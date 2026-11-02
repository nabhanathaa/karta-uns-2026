"""Latih pengklasifikasi petak (backend "petak") dengan transfer learning.

Disarankan dijalankan di Colab (GPU), tetapi EfficientNet-B0 pada beberapa ribu
petak juga selesai dalam puluhan menit di CPU.

  pip install torch torchvision timm scikit-learn
  python latih/02_latih_petak.py --data data/petak --keluar model/petak_v1 --epoch 15

Hal penting:
- Validasi dibagi PER FOTO (GroupKFold), bukan per petak. Petak dari foto yang
  sama sangat mirip; jika tercampur di latih dan validasi, akurasi akan tampak
  tinggi palsu (kebocoran data / data leakage).
- Metrik yang dilaporkan ada dua: akurasi petak dan MAE proporsi per foto.
  Yang kedua lebih penting untuk KARTA karena masuk ke model kadar air.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
import timm
import torch
import torch.nn as nn
from PIL import Image
from sklearn.model_selection import GroupKFold
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms as T

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from karta.konstanta import FRAKSI, KELAS_VISI  # noqa: E402

MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)


class DataPetak(Dataset):
    def __init__(self, item, tf):
        self.item, self.tf = item, tf

    def __len__(self):
        return len(self.item)

    def __getitem__(self, i):
        p, y = self.item[i]
        return self.tf(Image.open(p).convert("RGB")), y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--keluar", required=True)
    ap.add_argument("--backbone", default="efficientnet_b0")
    ap.add_argument("--input", type=int, default=160)
    ap.add_argument("--epoch", type=int, default=15)
    ap.add_argument("--bs", type=int, default=64)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    kelas = [k for k in KELAS_VISI if (Path(a.data) / k).is_dir()]
    item, grup = [], []
    for ki, k in enumerate(kelas):
        for p in sorted((Path(a.data) / k).glob("*.jpg")):
            item.append((str(p), ki)); grup.append(p.stem.split("__")[0])
    print(f"{len(item)} petak, {len(set(grup))} foto, kelas: {kelas}")
    tr_idx, va_idx = next(GroupKFold(5).split(item, groups=grup))

    tf_latih = T.Compose([
        T.RandomResizedCrop(a.input, scale=(0.6, 1.0)), T.RandomHorizontalFlip(), T.RandomVerticalFlip(),
        T.ColorJitter(0.3, 0.3, 0.2, 0.03),       # cahaya pagi/sore/mendung
        T.RandomApply([T.GaussianBlur(5)], p=0.2),  # debu/goyang
        T.ToTensor(), T.Normalize(MEAN, STD)])
    tf_val = T.Compose([T.Resize((a.input, a.input)), T.ToTensor(), T.Normalize(MEAN, STD)])
    dl_tr = DataLoader(DataPetak([item[i] for i in tr_idx], tf_latih), a.bs, shuffle=True, num_workers=2)
    dl_va = DataLoader(DataPetak([item[i] for i in va_idx], tf_val), a.bs, num_workers=2)

    model = timm.create_model(a.backbone, pretrained=True, num_classes=len(kelas)).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.05)
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, 3e-4, total_steps=a.epoch * len(dl_tr))
    lossf = nn.CrossEntropyLoss(label_smoothing=0.1)
    terbaik = -1
    for ep in range(a.epoch):
        model.train()
        for x, y in dl_tr:
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad(); lossf(model(x), y).backward(); opt.step(); sch.step()
        model.eval(); pred = []
        with torch.no_grad():
            for x, _ in dl_va:
                pred.append(model(x.to(dev)).argmax(1).cpu())
        pred = torch.cat(pred).numpy()
        y_va = np.array([item[i][1] for i in va_idx])
        akurasi = float((pred == y_va).mean())
        mae = mae_proporsi_per_foto(pred, y_va, [grup[i] for i in va_idx], kelas)
        print(f"epoch {ep + 1}: akurasi petak {akurasi:.3f} | MAE proporsi per foto {mae:.2f} poin")
        if akurasi > terbaik:
            terbaik = akurasi
            simpan(model, kelas, a, dev, {"akurasi_petak_val": akurasi, "mae_proporsi_val_pp": mae, "epoch": ep + 1})
    print("selesai, akurasi validasi terbaik", round(terbaik, 3))


def mae_proporsi_per_foto(pred, y, grup, kelas):
    fr = [i for i, k in enumerate(kelas) if k in FRAKSI]
    err = []
    for g in set(grup):
        m = np.array(grup) == g
        ph = np.bincount(pred[m], minlength=len(kelas))[fr].astype(float)
        yh = np.bincount(y[m], minlength=len(kelas))[fr].astype(float)
        if yh.sum() == 0:
            continue
        err.append(np.abs(ph / max(ph.sum(), 1) - yh / yh.sum()).mean() * 100)
    return float(np.mean(err))


def simpan(model, kelas, a, dev, metrik):
    out = Path(a.keluar); out.mkdir(parents=True, exist_ok=True)
    model.eval()
    contoh = torch.zeros(1, 3, a.input, a.input, device=dev)
    torch.jit.trace(model, contoh).save(str(out / "model.pt"))
    (out / "meta.json").write_text(json.dumps({
        "kelas": kelas, "ukuran_petak": 128, "ukuran_input": a.input, "mean": MEAN, "std": STD,
        "backbone": a.backbone, "seed": a.seed, "metrik": metrik,
        "versi": {"torch": torch.__version__, "timm": timm.__version__}}, indent=2))


if __name__ == "__main__":
    main()
