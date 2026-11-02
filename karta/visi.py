"""Mata AI KARTA: dari satu foto muatan -> proporsi luas tiap fraksi + peta warna.

Foto muatan truk berisi CAMPURAN banyak jenis sampah, jadi satu foto tidak
cukup diberi satu label. Yang dibutuhkan adalah "berapa persen luas foto
yang berisi organik, plastik, kertas, ...". Ada dua cara:

0. backend "segformer" (model utama): segmentasi semantik per piksel, fine-tune dari
   checkpoint SegFormer pralatih (latih/05_latih_segformer.py), lengkap dengan peta
   ketidakpastian (entropi).

1. backend "petak" (baseline cepat untuk tahap awal / TKT 3-4):
   foto dipotong menjadi petak kecil (misalnya 64x64 piksel), lalu SETIAP PETAK
   diklasifikasikan satu per satu. Proporsi = jumlah petak per
   kelas / jumlah petak sampah. Pelabelan sangat cepat: cukup memindahkan file
   petak ke folder kelasnya. Kelemahan: batas antarbenda kasar.

2. backend "yolo" (segmentasi, tahap lanjut):
   model YOLO-seg memberi masker per benda. Lebih presisi, tetapi pelabelan
   memakai poligon (jauh lebih lama).

backend "demo" HANYA untuk menguji alur aplikasi tanpa model terlatih.
Hasilnya aturan warna sederhana, BUKAN AI, dan diberi tanda di layar.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .konstanta import FRAKSI, KELAS_VISI, LATAR

WARNA = {  # BGR untuk OpenCV
    "organik_basah": (40, 160, 40), "plastik": (220, 120, 30), "kertas_kardus": (60, 180, 230),
    "tekstil": (180, 60, 200), "kayu_ranting": (30, 90, 140), "inert": (150, 150, 150),
    LATAR: (0, 0, 0),
}


@dataclass
class HasilVisi:
    proporsi: dict          # {fraksi: proporsi luas 0..1}, jumlah = 1 (tanpa latar)
    peta_kelas: np.ndarray  # HxW indeks KELAS_VISI
    keyakinan: float        # rata-rata keyakinan model (0..1)
    backend: str
    ketidakpastian: np.ndarray | None = None   # HxW entropi prediksi (0..1), None bila backend tak punya
    proporsi_lunak: dict | None = None         # proporsi dari rata-rata probabilitas (bukan argmax)

    def overlay(self, gambar_bgr: np.ndarray, alpha: float = 0.45) -> np.ndarray:
        warna = np.array([WARNA[k] for k in KELAS_VISI], dtype=np.uint8)
        lapis = warna[self.peta_kelas]
        out = gambar_bgr.copy()
        bukan_latar = self.peta_kelas != KELAS_VISI.index(LATAR)
        out[bukan_latar] = (alpha * lapis[bukan_latar] + (1 - alpha) * out[bukan_latar]).astype(np.uint8)
        return out


    def overlay_ketidakpastian(self, gambar_bgr: np.ndarray, alpha: float = 0.6) -> np.ndarray:
        """Peta panas entropi: area terang = model ragu. Ditampilkan di layar operator."""
        if self.ketidakpastian is None:
            return gambar_bgr
        u = np.clip(self.ketidakpastian, 0.0, 1.0)
        try:
            import cv2
            h = cv2.applyColorMap((u * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
            return cv2.addWeighted(h, alpha, gambar_bgr, 1 - alpha, 0)
        except Exception:
            # Palet Inferno vektor NumPy (BGR)
            r = np.clip(np.where(u < 0.5, u * 2.0 * 210, 210 + (u - 0.5) * 2.0 * 45), 0, 255)
            g = np.clip(np.where(u < 0.4, u * 2.5 * 50, 50 + (u - 0.4) / 0.6 * 195), 0, 255)
            b = np.clip(np.where(u < 0.5, 40 + u * 2.0 * 120, 160 - (u - 0.5) * 2.0 * 110), 0, 255)
            h = np.stack([b, g, r], axis=-1).astype(np.uint8)
            return (alpha * h + (1.0 - alpha) * gambar_bgr).astype(np.uint8)


def rata_rata_frame(hasil: list["HasilVisi"]) -> tuple[dict, dict]:
    """Gabungkan beberapa frame satu muatan: rata-rata proporsi dan simpangan baku
    antarframe (ukuran ketidakpastian akibat sudut/lapisan yang berbeda)."""
    M = np.array([[h.proporsi[f] for f in FRAKSI] for h in hasil])
    return ({f: float(M[:, i].mean()) for i, f in enumerate(FRAKSI)},
            {f: float(M[:, i].std(ddof=1)) if len(M) > 1 else 0.0 for i, f in enumerate(FRAKSI)})


def _proporsi_dari_peta(peta: np.ndarray) -> dict:
    hit = np.bincount(peta.ravel(), minlength=len(KELAS_VISI))[: len(FRAKSI)].astype(float)
    tot = hit.sum()
    return {f: (hit[i] / tot if tot > 0 else 0.0) for i, f in enumerate(FRAKSI)}


# ------------------------------------------------------------------ petak

class ModelPetak:
    """Klasifikasi per petak. File model: folder berisi model.pt (TorchScript) dan meta.json
    (dibuat oleh latih/02_latih_petak.py)."""

    def __init__(self, folder: str | Path, device: str = "cpu"):
        import torch
        folder = Path(folder)
        self.meta = json.loads((folder / "meta.json").read_text())
        self.model = torch.jit.load(str(folder / "model.pt"), map_location=device).eval()
        self.device = device
        self.kelas = self.meta["kelas"]
        self.petak = int(self.meta["ukuran_petak"])
        self.input = int(self.meta["ukuran_input"])
        self.mean = np.array(self.meta["mean"], np.float32)
        self.std = np.array(self.meta["std"], np.float32)

    def __call__(self, bgr: np.ndarray) -> HasilVisi:
        import cv2
        import torch
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        H, W = rgb.shape[:2]
        s = self.petak
        ny, nx = H // s, W // s
        petak = [cv2.resize(rgb[y * s:(y + 1) * s, x * s:(x + 1) * s], (self.input, self.input))
                 for y in range(ny) for x in range(nx)]
        X = (np.stack(petak).astype(np.float32) / 255 - self.mean) / self.std
        X = torch.from_numpy(X.transpose(0, 3, 1, 2)).to(self.device)
        with torch.no_grad():
            prob = torch.cat([self.model(b).softmax(1) for b in X.split(256)]).cpu().numpy()
        # urutan kelas model -> urutan KELAS_VISI
        peta_idx = np.array([KELAS_VISI.index(k) for k in self.kelas])[prob.argmax(1)]
        peta = np.full((H, W), KELAS_VISI.index(LATAR), np.int64)
        peta[: ny * s, : nx * s] = np.kron(peta_idx.reshape(ny, nx), np.ones((s, s), np.int64))
        ent = -(prob * np.log(prob + 1e-9)).sum(1) / np.log(prob.shape[1])
        unc = np.kron(ent.reshape(ny, nx), np.ones((s, s))).astype(np.float32)
        unc = np.pad(unc, ((0, H - ny * s), (0, W - nx * s)))
        lunak = np.zeros(len(KELAS_VISI)); np.add.at(lunak, [KELAS_VISI.index(k) for k in self.kelas], prob.mean(0))
        lunak = lunak[: len(FRAKSI)] / max(lunak[: len(FRAKSI)].sum(), 1e-9)
        return HasilVisi(_proporsi_dari_peta(peta), peta, float(prob.max(1).mean()), "petak",
                         unc, {f: float(lunak[i]) for i, f in enumerate(FRAKSI)})


# ------------------------------------------------------------------ segformer

class ModelSegFormer:
    """SegFormer (Xie dkk., 2021) hasil fine-tune dari latih/05_latih_segformer.py.
    Folder berisi model Hugging Face (save_pretrained) dan meta.json.
    Prediksi memakai test-time augmentation (flip horizontal). Proporsi dihitung dari
    argmax per piksel; proporsi_lunak dari rata-rata probabilitas."""

    def __init__(self, folder: str | Path, device: str = "cpu"):
        import torch
        from transformers import SegformerForSemanticSegmentation
        folder = Path(folder)
        self.meta = json.loads((folder / "meta.json").read_text())
        self.model = SegformerForSemanticSegmentation.from_pretrained(str(folder)).to(device).eval()
        self.device, self.kelas = device, self.meta["kelas"]
        self.tinggi = int(self.meta.get("tinggi_input", 512))
        self.mean = np.array(self.meta.get("mean", [0.485, 0.456, 0.406]), np.float32)
        self.std = np.array(self.meta.get("std", [0.229, 0.224, 0.225]), np.float32)

    def __call__(self, bgr: np.ndarray, tta: bool = True) -> HasilVisi:
        import cv2
        import torch
        import torch.nn.functional as F
        H, W = bgr.shape[:2]
        h = self.tinggi
        w = int(round(W / H * h / 32)) * 32
        x = cv2.resize(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), (w, h)).astype(np.float32) / 255
        x = torch.from_numpy(((x - self.mean) / self.std).transpose(2, 0, 1))[None].to(self.device)
        with torch.no_grad():
            logit = self.model(pixel_values=x).logits
            if tta:
                logit = (logit + self.model(pixel_values=x.flip(-1)).logits.flip(-1)) / 2
            prob = F.interpolate(logit, size=(H, W), mode="bilinear", align_corners=False).softmax(1)[0].cpu().numpy()
        urut = np.array([KELAS_VISI.index(k) for k in self.kelas])
        peta = urut[prob.argmax(0)]
        ent = (-(prob * np.log(prob + 1e-9)).sum(0) / np.log(prob.shape[0])).astype(np.float32)
        lunak = np.zeros(len(KELAS_VISI)); lunak[urut] = prob.mean((1, 2))
        lunak = lunak[: len(FRAKSI)] / max(lunak[: len(FRAKSI)].sum(), 1e-9)
        return HasilVisi(_proporsi_dari_peta(peta), peta, float(prob.max(0).mean()), "segformer",
                         ent, {f: float(lunak[i]) for i, f in enumerate(FRAKSI)})


# ------------------------------------------------------------------ yolo

class ModelYolo:
    """Segmentasi instans dengan Ultralytics YOLO-seg. Nama kelas di data.yaml
    harus sama dengan FRAKSI (tanpa 'latar'; piksel tanpa masker = latar).
    Catatan lisensi: Ultralytics berlisensi AGPL-3.0. Untuk produk komersial
    tertutup perlu lisensi Enterprise, atau ganti ke model berlisensi longgar
    (misalnya DeepLabV3-MobileNetV3 dari torchvision, BSD)."""

    def __init__(self, bobot: str | Path, imgsz: int = 640, conf: float = 0.25):
        from ultralytics import YOLO
        self.model = YOLO(str(bobot))
        self.imgsz, self.conf = imgsz, conf

    def __call__(self, bgr: np.ndarray) -> HasilVisi:
        import cv2
        H, W = bgr.shape[:2]
        r = self.model.predict(bgr, imgsz=self.imgsz, conf=self.conf, verbose=False)[0]
        peta = np.full((H, W), KELAS_VISI.index(LATAR), np.int64)
        konf = []
        if r.masks is not None:
            nama = r.names
            # gambar masker dari keyakinan rendah ke tinggi agar yang yakin menimpa
            urut = np.argsort(r.boxes.conf.cpu().numpy())
            for i in urut:
                m = r.masks.data[i].cpu().numpy()
                m = cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST) > 0.5
                peta[m] = KELAS_VISI.index(nama[int(r.boxes.cls[i])])
                konf.append(float(r.boxes.conf[i]))
        return HasilVisi(_proporsi_dari_peta(peta), peta, float(np.mean(konf)) if konf else 0.0, "yolo")


# ------------------------------------------------------------------ demo

class ModelDemo:
    """BUKAN AI. Aturan warna HSV kasar sebagai pembanding baseline sederhana."""

    def __call__(self, bgr: np.ndarray) -> HasilVisi:
        try:
            import cv2
            hsv = cv2.cvtColor(cv2.GaussianBlur(bgr, (9, 9), 0), cv2.COLOR_BGR2HSV)
            h, s, v = [hsv[..., i].astype(int) for i in range(3)]
        except Exception:
            rgb = bgr[..., ::-1].astype(np.float32)
            cmax = rgb.max(axis=-1)
            cmin = rgb.min(axis=-1)
            delta = cmax - cmin
            v = cmax.astype(int)
            s = np.where(cmax > 0, (delta / np.maximum(cmax, 1e-6)) * 255, 0).astype(int)
            r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
            hue = np.zeros_like(cmax)
            m_r = (delta > 0) & (cmax == r)
            m_g = (delta > 0) & (cmax == g)
            m_b = (delta > 0) & (cmax == b)
            hue[m_r] = (30 * ((g[m_r] - b[m_r]) / delta[m_r])) % 180
            hue[m_g] = 30 * ((b[m_g] - r[m_g]) / delta[m_g] + 2)
            hue[m_b] = 30 * ((r[m_b] - g[m_b]) / delta[m_b] + 4)
            h = hue.astype(int)
        peta = np.full(h.shape, KELAS_VISI.index("inert"), np.int64)
        peta[(s < 40) & (v > 170)] = KELAS_VISI.index("kertas_kardus")
        peta[(h >= 10) & (h < 25) & (s >= 60)] = KELAS_VISI.index("kertas_kardus")
        peta[(h >= 25) & (h < 90) & (s >= 60)] = KELAS_VISI.index("organik_basah")
        peta[((h >= 90) & (h < 135) | (h >= 150)) & (s >= 80)] = KELAS_VISI.index("plastik")
        peta[(v < 50)] = KELAS_VISI.index(LATAR)
        return HasilVisi(_proporsi_dari_peta(peta), peta, 0.45, "Baseline Aturan HSV (Non-ML)")


def muat_model(jenis: str = "karta_v4", path: str | None = None):
    if jenis in {"karta_v4", "pretrained", "multiscale"}:
        from .pretrained import ModelKartaV4
        return ModelKartaV4(path)
    if jenis == "deeplabv3":
        from .pretrained import ModelDeepLabEdge
        return ModelDeepLabEdge(path)
    if jenis == "petak":
        if path and Path(path).exists():
            return ModelPetak(path)
        from .pretrained import ModelKartaV4
        return ModelKartaV4()
    if jenis == "segformer":
        if path and Path(path).exists():
            return ModelSegFormer(path)
        from .pretrained import ModelKartaV4
        return ModelKartaV4()
    if jenis == "zero-shot":
        try:
            from .zero_shot import ModelZeroShot
            return ModelZeroShot()
        except Exception:
            from .pretrained import ModelKartaV4
            return ModelKartaV4()
    if jenis == "yolo":
        if path and Path(path).exists():
            return ModelYolo(path)
        from .pretrained import ModelKartaV4
        return ModelKartaV4()
    return ModelDemo()
