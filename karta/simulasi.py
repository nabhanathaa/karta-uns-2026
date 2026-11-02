"""Generator data SIMULASI untuk menguji alur KARTA sebelum ada data lapangan.

PERINGATAN: semua angka dari modul ini SINTETIS. Gunanya hanya untuk
(1) memastikan kode berjalan dari ujung ke ujung, (2) memilih metode yang
tepat untuk ukuran data yang realistis (misalnya 30 uji oven), dan
(3) menunjukkan desain eksperimen di proposal. Hasilnya TIDAK boleh ditulis
sebagai kinerja di Putri Cempo.

Dunia simulasi sengaja dibuat "lebih rumit" daripada asumsi model:
- massa per luas yang sebenarnya berbeda dari asumsi literatur,
- hujan membasahi kertas/kain jauh lebih kuat daripada plastik,
- tiap TPS punya kebiasaan sendiri (tertutup/terbuka),
- kamera salah menaksir proporsi luas (galat segmentasi),
- uji oven sendiri punya galat sampling.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .konstanta import FRAKSI, KADAR_AIR_LIT, MASSA_PER_LUAS

# Pola komposisi LUAS per tipe TPS (parameter Dirichlet, urutan = FRAKSI)
POLA_TPS = {
    "pasar":     [8.0, 2.0, 1.0, 0.3, 1.0, 0.4],
    "perumahan": [4.0, 3.5, 2.0, 0.8, 1.0, 0.6],
    "komersial": [2.0, 4.5, 3.5, 0.6, 0.4, 0.5],
    "taman":     [1.5, 1.5, 0.8, 0.3, 6.0, 0.8],
}

# "Kebenaran" dunia simulasi yang TIDAK diketahui model
_MASSA_PER_LUAS_ASLI = {"organik_basah": 1.0, "plastik": 0.25, "kertas_kardus": 0.35,
                        "tekstil": 0.7, "kayu_ranting": 0.5, "inert": 1.5}
_EFEK_HUJAN = {"organik_basah": 0.0006, "plastik": 0.0020, "kertas_kardus": 0.0060,
               "tekstil": 0.0060, "kayu_ranting": 0.0025, "inert": 0.0010}  # per mm
_KADAR_AIR_ASLI = {**KADAR_AIR_LIT, "organik_basah": 0.78, "plastik": 0.08, "kertas_kardus": 0.14}


def buat_tps(n_tps: int = 15, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tipe = rng.choice(list(POLA_TPS), size=n_tps, p=[0.2, 0.5, 0.2, 0.1])
    return pd.DataFrame({"tps": [f"TPS-{i + 1:02d}" for i in range(n_tps)],
                         "tipe": tipe,
                         "offset_air": rng.normal(0, 0.02, n_tps)})


def buat_hujan(n_hari: int, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    hujan = np.where(rng.random(n_hari) < 0.45, 0.0, rng.gamma(0.8, 22.0, n_hari))
    h72 = pd.Series(hujan).rolling(3, min_periods=1).sum().to_numpy()
    return pd.DataFrame({"hari": np.arange(n_hari), "hujan_24j": hujan, "hujan_72j": h72})


def buat_muatan(n_hari: int = 60, truk_per_hari: int = 60, n_tps: int = 15,
                galat_kamera: float = 60.0, seed: int = 2026) -> pd.DataFrame:
    """Satu baris = satu muatan truk. galat_kamera = konsentrasi Dirichlet galat
    segmentasi (makin besar makin akurat; 60 kira-kira MAE proporsi 3-5 poin)."""
    rng = np.random.default_rng(seed)
    tps = buat_tps(n_tps, seed)
    hujan = buat_hujan(n_hari, seed + 1)
    baris = []
    for h in range(n_hari):
        for t in range(truk_per_hari):
            j = rng.integers(n_tps)
            tipe = tps.tipe[j]
            luas = rng.dirichlet(np.array(POLA_TPS[tipe]) * 3)
            # massa sebenarnya (dengan variasi antarmuatan)
            mpl = np.array([_MASSA_PER_LUAS_ASLI[f] for f in FRAKSI]) * rng.lognormal(0, 0.15, 6)
            massa = luas * mpl
            massa /= massa.sum()
            r = hujan.hujan_24j[h] + 0.3 * (hujan.hujan_72j[h] - hujan.hujan_24j[h])
            w_frak = np.array([_KADAR_AIR_ASLI[f] + _EFEK_HUJAN[f] * r for f in FRAKSI])
            w_frak = np.clip(w_frak + rng.normal(0, 0.03, 6), 0.01, 0.9)
            w_asli = float(np.clip(massa @ w_frak + tps.offset_air[j], 0.02, 0.9))
            luas_kamera = rng.dirichlet(luas * galat_kamera + 0.05)
            baris.append({
                "id_muatan": f"H{h:03d}-T{t:02d}", "hari": h, "tps": tps.tps[j], "tipe_tps": tipe,
                "ton": float(np.clip(rng.normal(6.5, 1.5), 2, 10)),
                "hujan_24j": hujan.hujan_24j[h], "hujan_72j": hujan.hujan_72j[h],
                **{f"luas_{f}": v for f, v in zip(FRAKSI, luas_kamera)},
                **{f"luas_asli_{f}": v for f, v in zip(FRAKSI, luas)},
                "plastik_massa_asli": massa[FRAKSI.index("plastik")],
                "w_asli": w_asli,
                # hasil uji oven = kebenaran + galat pengambilan sub-sampel
                "w_oven": float(np.clip(w_asli + rng.normal(0, 0.015), 0.01, 0.95)),
            })
    return pd.DataFrame(baris)


def mae_proporsi(df: pd.DataFrame) -> float:
    """Rata-rata galat absolut proporsi luas kamera vs asli (poin persen)."""
    a = df[[f"luas_{f}" for f in FRAKSI]].to_numpy()
    b = df[[f"luas_asli_{f}" for f in FRAKSI]].to_numpy()
    return float(np.abs(a - b).mean() * 100)


__all__ = ["buat_muatan", "buat_tps", "buat_hujan", "mae_proporsi", "MASSA_PER_LUAS"]
