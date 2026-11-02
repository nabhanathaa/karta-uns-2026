"""Segmentasi TANPA pelatihan (zero-shot) untuk demo awal, sebelum ada foto dan anotasi.

Model: CLIPSeg (Lüddecke dan Ecker, 2022, arXiv 2112.10003; Hugging Face CIDAS/clipseg-rd64-refined,
Apache-2.0). Ia menerima TEKS ("plastic bag", "food waste", ...) lalu memberi peta probabilitas per
piksel. Tidak ada label sampah yang dipakai untuk melatihnya.

PENTING (jujur):
- Ini BUKAN model terlatih KARTA. Kualitasnya hanya cukup untuk memeriksa alur (foto/kamera/video ->
  segmentasi -> proporsi -> kadar air -> rute) dan melihat bentuk keluaran. Untuk sampah basah campur,
  kelas organik/plastik/kertas sering tertukar, dan batas objek kasar (peta CLIPSeg beresolusi 352x352
  per petak).
- Ambang (`ambang`) dan teks prompt perlu disesuaikan dengan foto Anda; tidak ada nilai yang sudah diuji.
- Setelah 100-300 foto dianotasi, ganti dengan SegFormer hasil fine-tune (latih/05_latih_segformer.py).
  Dengan antarmuka yang sama, cukup ubah MODE di notebook.
"""
from __future__ import annotations

import numpy as np

from .konstanta import FRAKSI, KELAS_VISI, LATAR
from .visi import HasilVisi, _proporsi_dari_peta

PROMPT_ZS = {
    "organik_basah": ["food waste", "rotten vegetables and fruit scraps", "wet organic garbage"],
    "plastik": ["plastic bag", "plastic bottle", "plastic packaging and styrofoam"],
    "kertas_kardus": ["cardboard box", "paper waste"],
    "tekstil": ["old clothes", "fabric and textile waste"],
    "kayu_ranting": ["wood and tree branches", "dry leaves and twigs"],
    "inert": ["metal can", "glass bottle", "stones and soil"],
    LATAR: ["concrete floor", "wall", "empty ground"],
}


class ModelZeroShot:
    nama_model = "CIDAS/clipseg-rd64-refined"

    def __init__(self, device: str | None = None, grid: int = 2, ambang: float = 0.25,
                 lebar_maks: int = 1280, prompt: dict | None = None, muat: bool = True):
        self.grid, self.ambang, self.lebar_maks = grid, ambang, lebar_maks
        self.prompt = prompt or PROMPT_ZS
        self.teks, self.idx_kelas = [], []
        for k in KELAS_VISI:
            ids = list(range(len(self.teks), len(self.teks) + len(self.prompt[k])))
            self.teks += self.prompt[k]
            self.idx_kelas.append(ids)
        if muat:
            self._muat(device)

    def _muat(self, device):
        import torch
        from transformers import CLIPSegForImageSegmentation, CLIPSegProcessor
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.proc = CLIPSegProcessor.from_pretrained(self.nama_model)
        self.model = CLIPSegForImageSegmentation.from_pretrained(self.nama_model).to(self.device).eval()

    def _logit_tiles(self, tiles: list[np.ndarray]) -> np.ndarray:
        """Satu-satunya bagian yang menyentuh model. Masukan: daftar petak RGB uint8.
        Keluaran: logit (T, jumlah_prompt, 352, 352)."""
        import torch
        from PIL import Image
        P, hasil = len(self.teks), []
        for t in tiles:
            im = Image.fromarray(t)
            inp = self.proc(text=self.teks, images=[im] * P, padding="max_length", return_tensors="pt").to(self.device)
            with torch.no_grad():
                lg = self.model(**inp).logits
            if lg.ndim == 2:
                lg = lg[None]
            hasil.append(lg.float().cpu().numpy())
        return np.stack(hasil)

    def __call__(self, bgr: np.ndarray) -> HasilVisi:
        import cv2
        H0, W0 = bgr.shape[:2]
        s = min(1.0, self.lebar_maks / W0)
        kecil = cv2.resize(bgr, (int(W0 * s), int(H0 * s))) if s < 1 else bgr
        H, W = kecil.shape[:2]
        rgb = cv2.cvtColor(kecil, cv2.COLOR_BGR2RGB)
        g = self.grid
        ys, xs = np.linspace(0, H, g + 1).astype(int), np.linspace(0, W, g + 1).astype(int)
        kotak = [(ys[i], ys[i + 1], xs[j], xs[j + 1]) for i in range(g) for j in range(g)]
        L = self._logit_tiles([rgb[y0:y1, x0:x1] for y0, y1, x0, x1 in kotak])

        K = len(KELAS_VISI)
        prob = np.zeros((K, H, W), np.float32)
        for ti, (y0, y1, x0, x1) in enumerate(kotak):
            p = np.stack([cv2.resize(l, (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR) for l in L[ti]])
            p = 1 / (1 + np.exp(-p))
            for ki, ids in enumerate(self.idx_kelas):
                prob[ki, y0:y1, x0:x1] = p[ids].mean(0)

        lat = KELAS_VISI.index(LATAR)
        peta = prob.argmax(0)
        kuat = prob.max(0)
        peta[(peta != lat) & (kuat < self.ambang)] = lat
        q = prob / np.maximum(prob.sum(0, keepdims=True), 1e-6)
        ent = (-(q * np.log(q + 1e-9)).sum(0) / np.log(K)).astype(np.float32)
        lunak = q.mean((1, 2))[: len(FRAKSI)]
        lunak = lunak / max(lunak.sum(), 1e-9)

        if s < 1:
            peta = cv2.resize(peta.astype(np.uint8), (W0, H0), interpolation=cv2.INTER_NEAREST)
            ent = cv2.resize(ent, (W0, H0), interpolation=cv2.INTER_LINEAR)
        peta = peta.astype(np.int64)
        return HasilVisi(_proporsi_dari_peta(peta), peta, float(kuat.mean()), "zero-shot CLIPSeg (BUKAN model terlatih KARTA)",
                         ent, {f: float(lunak[i]) for i, f in enumerate(FRAKSI)})
