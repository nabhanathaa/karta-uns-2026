"""Fine-tune SegFormer untuk segmentasi fraksi sampah (model utama KARTA).

Masukan (hasil anotasi CVAT + SAM 2, lihat dokumen teknis bagian dataset):
  data/seg/images/<id>.jpg         foto muatan
  data/seg/masks/<id>.png          masker indeks (0..6 = urutan KELAS_VISI di karta/konstanta.py,
                                   255 = abaikan/tidak jelas)
  data/seg/metadata.csv            kolom: file (tanpa ekstensi), muatan (id muatan truk)

Validasi dibagi PER MUATAN (GroupKFold): beberapa foto dari muatan yang sama sangat mirip,
sehingga jika tercampur antara latih dan validasi, skor tampak lebih tinggi dari kenyataan.

  pip install torch torchvision transformers scikit-learn pandas pillow
  python latih/05_latih_segformer.py --data data/seg --keluar model/segformer_b2_f0 --fold 0 --epoch 60

Titik awal bobot: --model nvidia/mit-b2 (encoder ImageNet-1k) atau checkpoint SegFormer
yang sudah di-fine-tune di ADE20K (mis. nvidia/segformer-b5-finetuned-ade-640-640).
Lisensi bobot NVIDIA tercatat "other" di Hugging Face; periksa sebelum komersialisasi.

STATUS: skrip ini belum dijalankan di mesin penulis (tidak ada GPU/PyTorch di lingkungan
penyusunan). Uji dulu dengan --epoch 1 pada 20 foto sebelum pelatihan penuh.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from PIL import Image
from sklearn.model_selection import GroupKFold
from torch.utils.data import DataLoader, Dataset
from torchvision import tv_tensors
from torchvision.transforms import v2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from karta.konstanta import FRAKSI, KELAS_VISI  # noqa: E402

MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)
NK = len(KELAS_VISI)
LATAR = KELAS_VISI.index("latar")


class DataSeg(Dataset):
    def __init__(self, root, files, size, latih):
        self.root, self.files = Path(root), files
        h, w = size, int(size * 16 / 9 / 32) * 32
        aug = [v2.RandomResizedCrop((h, w), scale=(0.35, 1.0), ratio=(1.3, 2.2)),
               v2.RandomHorizontalFlip(), v2.RandomVerticalFlip(),
               v2.ColorJitter(0.35, 0.35, 0.25, 0.04),           # cahaya pagi/sore/mendung
               v2.RandomApply([v2.GaussianBlur(5)], p=0.2),       # goyang/debu
               v2.RandomApply([v2.JPEG((40, 95))], p=0.3)] if latih else [v2.Resize((h, w))]
        self.tf = v2.Compose(aug)
        self.norm = v2.Compose([v2.ToDtype(torch.float32, scale=True), v2.Normalize(MEAN, STD)])

    def __len__(self):
        return len(self.files)

    def __getitem__(self, i):
        f = self.files[i]
        img = tv_tensors.Image(torch.from_numpy(np.array(Image.open(self.root / "images" / f"{f}.jpg").convert("RGB"))).permute(2, 0, 1))
        msk = tv_tensors.Mask(torch.from_numpy(np.array(Image.open(self.root / "masks" / f"{f}.png"))).long()[None])
        img, msk = self.tf(img, msk)
        return self.norm(img), msk[0].long()


def loss_fn(logit, y, bobot):
    logit = F.interpolate(logit, size=y.shape[-2:], mode="bilinear", align_corners=False)
    ce = F.cross_entropy(logit, y, weight=bobot, ignore_index=255, label_smoothing=0.05)
    valid = (y != 255)
    p = logit.softmax(1)
    oh = F.one_hot(y.clamp(max=NK - 1), NK).permute(0, 3, 1, 2).float()
    v = valid[:, None].float()
    inter = (p * oh * v).sum((0, 2, 3))
    dice = 1 - ((2 * inter + 1) / ((p * v).sum((0, 2, 3)) + (oh * v).sum((0, 2, 3)) + 1)).mean()
    return ce + dice


@torch.no_grad()
def evaluasi(model, dl, dev):
    model.eval()
    conf = np.zeros((NK, NK), np.int64)
    mae_frak = []
    for x, y in dl:
        lg = F.interpolate(model(pixel_values=x.to(dev)).logits, size=y.shape[-2:], mode="bilinear", align_corners=False)
        pr = lg.argmax(1).cpu().numpy()
        yy = y.numpy()
        for a, b in zip(pr, yy):
            m = b != 255
            conf += np.bincount(b[m] * NK + a[m], minlength=NK * NK).reshape(NK, NK)
            # galat proporsi fraksi (tanpa latar): ukuran terpenting untuk model kadar air
            pa = np.bincount(a[m & (b != LATAR)], minlength=NK)[: len(FRAKSI)].astype(float)
            pb = np.bincount(b[m & (b != LATAR)], minlength=NK)[: len(FRAKSI)].astype(float)
            if pb.sum() > 0 and pa.sum() > 0:
                mae_frak.append(np.abs(pa / pa.sum() - pb / pb.sum()).mean() * 100)
    iou = np.diag(conf) / np.maximum(conf.sum(0) + conf.sum(1) - np.diag(conf), 1)
    return {"mIoU": float(iou.mean()), "IoU_per_kelas": {k: float(v) for k, v in zip(KELAS_VISI, iou)},
            "MAE_proporsi_pp": float(np.mean(mae_frak))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--keluar", required=True)
    ap.add_argument("--model", default="nvidia/mit-b2")
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--epoch", type=int, default=60)
    ap.add_argument("--tinggi", type=int, default=512)
    ap.add_argument("--bs", type=int, default=8)
    ap.add_argument("--lr", type=float, default=6e-5)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    meta = pd.read_csv(Path(a.data) / "metadata.csv", dtype=str)
    tr, va = list(GroupKFold(5).split(meta, groups=meta["muatan"]))[a.fold]
    dl_tr = DataLoader(DataSeg(a.data, meta.file.iloc[tr].tolist(), a.tinggi, True), a.bs, shuffle=True, num_workers=2, drop_last=True)
    dl_va = DataLoader(DataSeg(a.data, meta.file.iloc[va].tolist(), a.tinggi, False), 2, num_workers=2)

    from transformers import SegformerForSemanticSegmentation
    model = SegformerForSemanticSegmentation.from_pretrained(
        a.model, num_labels=NK, id2label=dict(enumerate(KELAS_VISI)),
        label2id={k: i for i, k in enumerate(KELAS_VISI)}, ignore_mismatched_sizes=True).to(dev)

    # bobot kelas dari frekuensi piksel (akar terbalik, tidak terlalu ekstrem)
    frek = np.zeros(NK)
    for f in meta.file.iloc[tr]:
        frek += np.bincount(np.array(Image.open(Path(a.data) / "masks" / f"{f}.png")).ravel(), minlength=256)[:NK]
    bobot = torch.tensor((1 / np.sqrt(frek + 1)) / (1 / np.sqrt(frek + 1)).mean(), dtype=torch.float32, device=dev)

    opt = torch.optim.AdamW([{"params": model.segformer.parameters(), "lr": a.lr},
                             {"params": model.decode_head.parameters(), "lr": a.lr * 10}], weight_decay=0.01)
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, [a.lr, a.lr * 10], total_steps=a.epoch * len(dl_tr), pct_start=0.1)
    skala = torch.amp.GradScaler(enabled=dev == "cuda")
    terbaik = -1.0
    for ep in range(a.epoch):
        model.train()
        for x, y in dl_tr:
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad()
            with torch.autocast(dev, enabled=dev == "cuda"):
                loss = loss_fn(model(pixel_values=x).logits, y, bobot)
            skala.scale(loss).backward(); skala.step(opt); skala.update(); sch.step()
        r = evaluasi(model, dl_va, dev)
        print(f"epoch {ep + 1}/{a.epoch} loss {loss.item():.3f} | mIoU {r['mIoU']:.3f} | MAE proporsi {r['MAE_proporsi_pp']:.2f} poin")
        if r["mIoU"] > terbaik:
            terbaik = r["mIoU"]
            out = Path(a.keluar); out.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(out)
            (out / "meta.json").write_text(json.dumps({
                "kelas": KELAS_VISI, "tinggi_input": a.tinggi, "mean": MEAN, "std": STD,
                "model_awal": a.model, "fold": a.fold, "seed": a.seed, "epoch": ep + 1, "metrik_val": r,
                "versi": {"torch": torch.__version__}}, indent=2))
    print("selesai. mIoU validasi terbaik:", round(terbaik, 3))


if __name__ == "__main__":
    main()
