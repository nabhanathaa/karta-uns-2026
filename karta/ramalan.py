"""Peramalan kadar air rata-rata muatan hari berikutnya (untuk menyiapkan serbuk kayu dan bak).

Model sengaja sederhana (regresi ridge pada fitur lag + prakiraan hujan) karena deret harian
yang tersedia pendek (puluhan hari). Pembanding wajib: persistensi ("besok sama dengan hari ini")
dan rata-rata 7 hari. Model hanya layak dipakai jika mengalahkan keduanya pada validasi
berurutan (expanding window), bukan acak.

Interval: kuantil galat satu-langkah dari validasi berurutan (split conformal sederhana).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .kadar_air import _Ridge


def fitur(harian: pd.DataFrame) -> pd.DataFrame:
    """harian: kolom hari, w_rata (kadar air rata-rata terukur/ditaksir), hujan (mm per hari).
    Baris t dipakai meramal w_rata pada t+1 dengan hujan(t+1) = PRAKIRAAN hujan besok."""
    d = harian.sort_values("hari").reset_index(drop=True)
    X = pd.DataFrame({"w_lag0": d.w_rata, "w_lag1": d.w_rata.shift(1), "w_ma7": d.w_rata.rolling(7, min_periods=3).mean(),
                      "log_hujan_besok": np.log1p(d.hujan.shift(-1)), "log_hujan_ini": np.log1p(d.hujan)})
    X["hari"] = d.hari
    X["target"] = d.w_rata.shift(-1)
    return X.dropna().reset_index(drop=True)


def uji_berurutan(harian: pd.DataFrame, awal: int = 20, alpha: float = 0.2) -> dict:
    """Ramal satu hari ke depan dengan jendela membesar; bandingkan dengan dua pembanding."""
    F = fitur(harian)
    kol = ["w_lag0", "w_lag1", "w_ma7", "log_hujan_besok", "log_hujan_ini"]
    y, pred, pers, ma7, lo, hi = [], [], [], [], [], []
    res_hist: list[float] = []
    for t in range(awal, len(F)):
        m = _Ridge(1.0).fit(F.loc[:t - 1, kol], F.loc[:t - 1, "target"])
        p = float(m.predict(F.loc[[t], kol])[0])
        q = np.quantile(res_hist, 1 - alpha) if len(res_hist) >= 5 else np.nan
        pred.append(p); y.append(F.target[t]); pers.append(F.w_lag0[t]); ma7.append(F.w_ma7[t])
        lo.append(p - q); hi.append(p + q)
        res_hist.append(abs(F.target[t] - p))
    y, pred, pers, ma7 = map(np.array, (y, pred, pers, ma7))
    lo, hi = np.array(lo), np.array(hi)
    ok = ~np.isnan(lo)
    return {"n_hari_uji": int(len(y)),
            "mae_model_pp": float(np.abs(y - pred).mean() * 100),
            "mae_persistensi_pp": float(np.abs(y - pers).mean() * 100),
            "mae_rata7_pp": float(np.abs(y - ma7).mean() * 100),
            "cakupan80": float(((y >= lo) & (y <= hi))[ok].mean()) if ok.any() else None}
