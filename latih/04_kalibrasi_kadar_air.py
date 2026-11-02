"""Kalibrasi model kadar air dari lembar uji oven lapangan.

Lembar: data/uji_oven.csv (contoh kolom di data/uji_oven_TEMPLATE.csv)
  id_sampel, tanggal, tps, foto, berat_cawan_g, berat_basah_g, berat_kering_g,
  hujan_24j, hujan_72j
Kadar air (basis basah) = (berat_basah - berat_kering) / (berat_basah - berat_cawan),
dengan pengeringan oven mengikuti ASTM E790-15 (110 °C; untuk sampah basah ulangi sampai
berat konstan) dan pengambilan contoh/komposisi mengikuti SNI 19-3964-1994.

Skrip ini: (1) menjalankan model visi pada foto tiap sampel untuk mengisi luas_*,
(2) menghitung w_oven, (3) membandingkan fisika vs koreksi_linear dengan
leave-one-out, (4) menyimpan CSV siap pakai untuk aplikasi demo.

  python latih/04_kalibrasi_kadar_air.py --lembar data/uji_oven.csv --visi petak --model model/petak_v1
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from karta.kadar_air import ModelKadarAir  # noqa: E402
from karta.konstanta import FRAKSI  # noqa: E402
from karta.visi import muat_model  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lembar", required=True)
    ap.add_argument("--visi", default="petak")
    ap.add_argument("--model", default=None)
    ap.add_argument("--folder_foto", default="data/foto_sampel")
    ap.add_argument("--keluar", default="data/uji_oven_siap.csv")
    a = ap.parse_args()

    d = pd.read_csv(a.lembar)
    d["w_oven"] = (d.berat_basah_g - d.berat_kering_g) / (d.berat_basah_g - d.berat_cawan_g)
    visi = muat_model(a.visi, a.model)
    for i, r in d.iterrows():
        hv = visi(cv2.imread(str(Path(a.folder_foto) / r.foto)))
        for f in FRAKSI:
            d.loc[i, f"luas_{f}"] = hv.proporsi[f]

    y = d.w_oven.to_numpy()
    for met in ["fisika", "koreksi_linear"]:
        pred = np.array([ModelKadarAir(met).fit(d.drop(i), y[d.index != i]).predict(d.loc[[i]]).w_hat.iloc[0]
                         for i in d.index])
        print(f"{met:15s} MAE leave-one-out = {np.abs(pred - y).mean() * 100:.2f} poin persen (n={len(d)})")
    d.to_csv(a.keluar, index=False)
    print("tersimpan:", a.keluar)


if __name__ == "__main__":
    main()
