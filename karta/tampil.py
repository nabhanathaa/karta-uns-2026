"""Menggambar hasil segmentasi: masker berwarna, kotak per area, label, panel persen, dan HUD keputusan."""
from __future__ import annotations

import numpy as np

from .konstanta import FRAKSI, KELAS_VISI, LATAR
from .visi import WARNA, HasilVisi

NAMA_PENDEK = {"organik_basah": "organik", "plastik": "plastik", "kertas_kardus": "kertas/kardus",
               "tekstil": "tekstil", "kayu_ranting": "kayu/ranting", "inert": "inert", LATAR: "latar"}


def kotak_segmentasi(peta: np.ndarray, min_luas: float = 0.004, kernel: int = 9) -> list[dict]:
    """Kotak pembatas untuk tiap area terhubung per kelas (kecuali latar). min_luas = porsi luas gambar."""
    import cv2
    H, W = peta.shape
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel, kernel))
    hasil = []
    for ki, nama in enumerate(KELAS_VISI):
        if nama == LATAR:
            continue
        m = cv2.morphologyEx((peta == ki).astype(np.uint8), cv2.MORPH_OPEN, k)
        n, _, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        for i in range(1, n):
            x, y, w, h, a = st[i]
            if a >= min_luas * H * W:
                hasil.append({"kelas": nama, "x": int(x), "y": int(y), "w": int(w), "h": int(h), "luas": float(a / (H * W))})
    return hasil


def _teks(img, s, org, skala=0.5, warna=(255, 255, 255), tebal=1, latar=True):
    import cv2
    (tw, th), _ = cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, skala, tebal)
    x, y = org
    if latar:
        cv2.rectangle(img, (x - 2, y - th - 3), (x + tw + 2, y + 3), (0, 0, 0), -1)
    cv2.putText(img, s, (x, y), cv2.FONT_HERSHEY_SIMPLEX, skala, warna, tebal, cv2.LINE_AA)


def gambar_hasil(bgr: np.ndarray, hv: HasilVisi, kotak: bool = True, panel: bool = True,
                 hud: list[str] | None = None, alpha: float = 0.45) -> np.ndarray:
    """Gambar asal + masker + kotak berlabel + panel persen di kanan + teks HUD di kiri atas."""
    import cv2
    out = hv.overlay(bgr, alpha)
    if kotak:
        for b in kotak_segmentasi(hv.peta_kelas):
            w = WARNA[b["kelas"]]
            cv2.rectangle(out, (b["x"], b["y"]), (b["x"] + b["w"], b["y"] + b["h"]), w, 2)
            _teks(out, f"{NAMA_PENDEK[b['kelas']]} {b['luas'] * 100:.0f}%", (b["x"] + 3, b["y"] + 15), 0.45, (255, 255, 255))
    for i, s in enumerate(hud or []):
        _teks(out, s, (8, 22 + 22 * i), 0.55, (0, 255, 255))
    if not panel:
        return out
    H, W = out.shape[:2]
    lebar = 270
    kanvas = np.full((H, W + lebar, 3), 24, np.uint8)
    kanvas[:, :W] = out
    _teks(kanvas, "Komposisi luas", (W + 12, 24), 0.55, (255, 255, 255), 1, False)
    for i, f in enumerate(FRAKSI):
        v = hv.proporsi[f]
        y = 54 + i * 34
        cv2.rectangle(kanvas, (W + 12, y), (W + 12 + int(v * (lebar - 90)), y + 14), WARNA[f], -1)
        _teks(kanvas, f"{NAMA_PENDEK[f]} {v * 100:.0f}%", (W + 12, y + 30), 0.45, (230, 230, 230), 1, False)
    _teks(kanvas, hv.backend[:34], (W + 12, H - 10), 0.38, (150, 150, 150), 1, False)
    return kanvas


def bandingkan(bgr: np.ndarray, hv: HasilVisi, hud: list[str] | None = None) -> np.ndarray:
    """Tiga panel berdampingan: asli | segmentasi + kotak | peta keraguan model (entropi)."""
    import cv2
    a = bgr.copy()
    b = gambar_hasil(bgr, hv, panel=False, hud=hud)
    c = hv.overlay_ketidakpastian(bgr) if hv.ketidakpastian is not None else np.zeros_like(bgr)
    for img, s in ((a, "asli"), (b, "segmentasi"), (c, "keraguan model (terang = ragu)")):
        _teks(img, s, (8, bgr.shape[0] - 10), 0.55)
    return cv2.hconcat([a, b, c])
