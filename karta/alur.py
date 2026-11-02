"""Alur satu muatan: foto -> proporsi fraksi -> kadar air & LHV (+interval) -> rute.

Untuk satu muatan yang lewat (demo konveyor), rute ditentukan dengan aturan
sederhana yang konsisten dengan optimasi harian (optimasi.py). Di lapangan,
rute akhir datang dari rencana_harian() yang melihat SEMUA muatan hari itu.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from .kadar_air import ModelKadarAir, luas_ke_massa
from .konstanta import FRAKSI, KADAR_AIR_MAKS_UMPAN, KADAR_AIR_MIN_BSF, PLASTIK_MAKS_BSF
from .optimasi import NAMA_RUTE, rasio_serbuk


BATAS_LEBAR_INTERVAL = 0.25   # lebar interval 80% (fraksi) di atas ini dianggap tidak yakin


def rute_satu_muatan(w_hat, w_atas, plastik_massa, organik_massa, inert_massa: float = 0.0) -> tuple[str, str]:
    if w_atas <= KADAR_AIR_MAKS_UMPAN and inert_massa < 0.22:
        return "U", "Batas atas P90 kadar air <= 20%, aman diumpankan langsung ke reaktor gasifikasi"
    if w_hat >= 0.55 and plastik_massa <= 0.12 and organik_massa >= 0.50:
        return "M", "Kadar air tinggi (>=55%), dominan organik, plastik <= 12%: optimal untuk unit Maggot BSF & Kompos"
    if w_hat < 0.65 and inert_massa < 0.30:
        return "B", f"Kadar air menengah; arahkan ke Bio-drying + bulking agent serbuk kayu {rasio_serbuk(w_hat) * 100:.1f}% massa"
    return "R", "Tercampur fraksi inert/residu tinggi atau sangat basah: tunda/sortir & kirim peringatan SE 11/2026 ke TPS asal"


def proses_muatan(bgr, model_visi, model_air: ModelKadarAir, tps: str,
                  hujan_24j: float, hujan_72j: float, ton: float | None = None,
                  kepadatan_t_m3: float | None = None) -> dict:
    hv = model_visi(bgr)
    data_baris = {**{f"luas_{f}": hv.proporsi[f] for f in FRAKSI},
                  "hujan_24j": hujan_24j, "hujan_72j": hujan_72j}
    if kepadatan_t_m3 is not None:
        data_baris["kepadatan_t_m3"] = kepadatan_t_m3
    baris = pd.DataFrame([data_baris])
    p = model_air.predict(baris).iloc[0]
    massa = luas_ke_massa(baris[[f"luas_{f}" for f in FRAKSI]]).iloc[0]
    lebar = float(p.w_atas - p.w_bawah)
    rute, alasan = rute_satu_muatan(p.w_hat, p.w_atas, massa["massa_plastik"],
                                    massa["massa_organik_basah"], massa["massa_inert"])
    dosis_serbuk_pct = float(rasio_serbuk(p.w_hat) * 100.0) if rute == "B" else 0.0
    return {
        "waktu": dt.datetime.now().isoformat(timespec="seconds"), "tps": tps, "ton": ton,
        "backend_visi": hv.backend, "keyakinan_visi": round(hv.keyakinan, 3),
        **{f"luas_{f}": round(float(hv.proporsi[f]), 4) for f in FRAKSI},
        **{f"massa_{f}": round(float(massa[f"massa_{f}"]), 4) for f in FRAKSI},
        "kadar_air": round(float(p.w_hat), 3), "kadar_air_bawah": round(float(p.w_bawah), 3),
        "kadar_air_atas": round(float(p.w_atas), 3),
        "lhv_mj_kg": round(float(p.lhv_hat), 2),
        "lhv_bawah": round(float(p.lhv_bawah), 2),
        "lhv_atas": round(float(p.lhv_atas), 2),
        "rute": rute, "nama_rute": NAMA_RUTE[rute],
        "dosis_serbuk_pct": round(dosis_serbuk_pct, 1),
        "alasan": alasan, "lebar_interval": round(lebar, 3),
        # interval terlalu lebar = model tidak yakin: minta operator memeriksa / ambil sampel uji oven
        "perlu_cek_manual": bool(lebar > BATAS_LEBAR_INTERVAL or (hv.keyakinan and hv.keyakinan < 0.5)),
        "_hasil_visi": hv,
    }


def catat(hasil: dict, path_csv: str | Path = "log_muatan.csv"):
    """Simpan satu baris per muatan (jejak data per TPS untuk peta sumber DLH)."""
    path_csv = Path(path_csv)
    data = {k: v for k, v in hasil.items() if not k.startswith("_")}
    baru = not path_csv.exists()
    with path_csv.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(data))
        if baru:
            w.writeheader()
        w.writerow(data)


def ringkasan_per_tps(path_csv: str | Path = "log_muatan.csv") -> pd.DataFrame:
    df = pd.read_csv(path_csv)
    return (df.groupby("tps")
              .agg(muatan=("rute", "size"), kadar_air_rata=("kadar_air", "mean"),
                   organik_rata=("luas_organik_basah", "mean"),
                   plastik_rata=("luas_plastik", "mean"),
                   persen_residu=("rute", lambda s: float(np.mean(s == "R"))))
              .sort_values("kadar_air_rata", ascending=False).round(3))
