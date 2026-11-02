"""Potong foto muatan menjadi petak untuk pelabelan cepat.

Cara pakai:
  python latih/01_potong_petak.py --foto data/foto --keluar data/petak --ukuran 128

Hasil: data/petak/_belum_label/<idfoto>__y<baris>_x<kolom>.jpg
Pelabelan: buat folder data/petak/<nama_kelas>/ (organik_basah, plastik, kertas_kardus,
tekstil, kayu_ranting, inert, latar, campur) lalu PINDAHKAN tiap petak ke folder
kelasnya (drag-and-drop di File Explorer). Petak yang berisi beberapa jenis
seimbang taruh di "campur" (tidak dipakai untuk latih, tetapi dihitung untuk
melaporkan seberapa sering kasus ambigu).

Jika punya masker segmentasi (PNG, nilai piksel = indeks KELAS_VISI), pakai
--masker data/masker: petak diberi label otomatis bila >= 60% pikselnya satu kelas.

Ukuran petak dipilih sebanding dengan ukuran benda: dengan kamera 2-3 m di atas
tipping floor dan foto 1280x720, petak 128 px kira-kira 25-35 cm di lapangan.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from karta.konstanta import KELAS_VISI  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--foto", required=True)
    ap.add_argument("--keluar", required=True)
    ap.add_argument("--ukuran", type=int, default=128)
    ap.add_argument("--masker", default=None)
    ap.add_argument("--ambang", type=float, default=0.6)
    a = ap.parse_args()
    keluar = Path(a.keluar)
    n = 0
    for p in sorted(Path(a.foto).glob("*")):
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        img = cv2.imread(str(p))
        msk = cv2.imread(str(Path(a.masker) / (p.stem + ".png")), cv2.IMREAD_GRAYSCALE) if a.masker else None
        H, W = img.shape[:2]
        s = a.ukuran
        for y in range(H // s):
            for x in range(W // s):
                tile = img[y * s:(y + 1) * s, x * s:(x + 1) * s]
                kelas = "_belum_label"
                if msk is not None:
                    hit = np.bincount(msk[y * s:(y + 1) * s, x * s:(x + 1) * s].ravel(),
                                      minlength=len(KELAS_VISI))
                    k = int(hit.argmax())
                    kelas = KELAS_VISI[k] if hit[k] / hit.sum() >= a.ambang else "campur"
                d = keluar / kelas
                d.mkdir(parents=True, exist_ok=True)
                # nama file memuat id foto -> dipakai untuk membagi data latih/validasi PER FOTO
                cv2.imwrite(str(d / f"{p.stem}__y{y:02d}_x{x:02d}.jpg"), tile)
                n += 1
    print(f"{n} petak ditulis ke {keluar}")


if __name__ == "__main__":
    main()
