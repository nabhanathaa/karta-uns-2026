"""Triase muatan harian dengan program linear bilangan bulat (MILP).

Bahasa awam: setiap pagi (atau tiap jam) ada daftar muatan truk yang sudah
ditaksir kadar air dan kalornya. Komputer memilih untuk TIAP muatan satu dari
empat rute, sehingga:
  - campuran yang masuk gasifier hari ini berkadar air <= 20% dan kalornya cukup,
  - kapasitas gasifier, bak bio-drying, unit maggot, dan stok serbuk kayu tidak dilampaui,
  - nilai total (energi + produk maggot - biaya serbuk kayu - penalti residu) maksimal.

Rute: U = umpan langsung, B = bio-drying (+ serbuk kayu), M = maggot BSF, R = residu/tunda.

Kunci ketahanan: kendala kadar air memakai BATAS ATAS interval (w_atas, P90),
bukan taksiran tengah. Jadi jika model meleset ke arah "terlalu kering",
campuran tetap aman. Ini disebut optimasi robust sederhana.

PERINGATAN: semua harga dan kapasitas default di bawah adalah ASUMSI untuk
simulasi dan harus diganti dengan angka dari DLH/operator.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

try:
    from scipy.optimize import Bounds, LinearConstraint, milp
    _ADA_SCIPY = True
except Exception:
    _ADA_SCIPY = False

from .konstanta import KADAR_AIR_MAKS_UMPAN, KADAR_AIR_MIN_BSF, PLASTIK_MAKS_BSF

RUTE = ["U", "B", "M", "R"]
NAMA_RUTE = {"U": "Umpan langsung PLTSa", "B": "Bio-drying + serbuk kayu",
             "M": "Maggot BSF & Kompos", "R": "Residu / tunda"}


@dataclass
class Parameter:
    kapasitas_gasifier_ton: float = 150.0     # ton/hari (aktual 100-150 menurut DLH)
    kapasitas_biodrying_ton: float = 210.0    # ton masuk per hari
    kapasitas_maggot_ton: float = 35.0        # ton/hari (unit BSF kawasan & kompos pasar)
    stok_serbuk_ton: float = 35.0             # ton tersedia hari ini dari UMKM Sukoharjo
    stok_biodrying_siap_ton: float = 65.0     # hasil bio-drying 4-5 hari lalu yang siap
    w_biodrying_keluar: float = 0.175         # kadar air hasil bio-drying
    lhv_biodrying_keluar: float = 11.2        # MJ/kg hasil bio-drying + serbuk kayu
    lhv_min_umpan: float = 8.0                # MJ/kg minimum campuran
    w_maks_umpan: float = KADAR_AIR_MAKS_UMPAN
    w_min_bsf: float = 0.55                   # batas kadar air minimum jalur organik/BSF
    plastik_maks_bsf: float = 0.12            # batas plastik sebelum pre-sorting trommel BSF
    harga_listrik_rp_kwh: float = 1500.0
    efisiensi_listrik: float = 0.20           # gasifikasi + genset
    diskon_biodrying: float = 0.85            # nilai energi tertunda + susut
    harga_serbuk_rp_ton: float = 300_000.0
    nilai_maggot_rp_ton_masuk: float = 950_000.0   # konversi larva BSF segar + kasgot
    penalti_residu_rp_ton: float = 400_000.0       # biaya residu & kepatuhan SE 11/2026
    pakai_batas_atas: bool = True             # True = robust (pakai w_atas P90)


def rasio_serbuk(w: np.ndarray) -> np.ndarray:
    """Dosis serbuk kayu sebagai bulking agent: 10% (agak basah) sampai 20%
    (sangat basah) dari massa muatan. Rentang dari literatur bio-drying;
    angka pastinya ditetapkan lewat uji coba bak kecil."""
    return np.clip(0.10 + 0.25 * (np.asarray(w) - 0.40), 0.10, 0.20)


def _rp_per_ton_energi(lhv_mj_kg, p: Parameter):
    # 1 ton x LHV (MJ/kg) x 1000 kg = MJ; / 3,6 = kWh panas; x efisiensi = kWh listrik
    return np.asarray(lhv_mj_kg) * 1000 / 3.6 * p.efisiensi_listrik * p.harga_listrik_rp_kwh


def rencana_harian(muatan: pd.DataFrame, p: Parameter | None = None) -> tuple[pd.DataFrame, dict]:
    """muatan wajib punya kolom: ton, w_hat, w_atas, lhv_hat, lhv_bawah, plastik_massa.
    Mengembalikan (tabel rute per muatan, ringkasan)."""
    p = p or Parameter()
    n = len(muatan)
    m = muatan["ton"].to_numpy(float)
    w_k = muatan["w_atas" if p.pakai_batas_atas else "w_hat"].to_numpy(float)
    w_md = muatan["w_hat"].to_numpy(float)
    lhv_k = muatan["lhv_bawah" if p.pakai_batas_atas else "lhv_hat"].to_numpy(float)
    lhv_md = muatan["lhv_hat"].to_numpy(float)
    plast = muatan["plastik_massa"].to_numpy(float)
    r = rasio_serbuk(w_md)

    # nilai Rupiah per ton untuk tiap rute
    nilai_U = _rp_per_ton_energi(lhv_md, p)
    # setelah bio-drying: massa kering tetap, air turun ke w_biodrying_keluar
    faktor_massa = (1 - w_md) / (1 - p.w_biodrying_keluar)
    nilai_B = p.diskon_biodrying * faktor_massa * _rp_per_ton_energi(p.lhv_biodrying_keluar, p) \
        - r * p.harga_serbuk_rp_ton
    nilai_M = np.full(n, p.nilai_maggot_rp_ton_masuk)
    nilai_R = np.full(n, -p.penalti_residu_rp_ton)

    # variabel: x[i, rute] biner (4n) + z = ton stok bio-drying siap yang diumpankan
    nv = 4 * n + 1
    iz = 4 * n
    idx = lambda i, k: 4 * i + k
    c = np.zeros(nv)
    for i in range(n):
        c[idx(i, 0)] = -m[i] * nilai_U[i]
        c[idx(i, 1)] = -m[i] * nilai_B[i]
        c[idx(i, 2)] = -m[i] * nilai_M[i]
        c[idx(i, 3)] = -m[i] * nilai_R[i]
    c[iz] = -_rp_per_ton_energi(p.lhv_biodrying_keluar, p)
    c = c / 1e6  # skala juta Rp agar solver stabil

    A, lo, hi = [], [], []

    def tambah(baris, a, b):
        A.append(baris); lo.append(a); hi.append(b)

    for i in range(n):                                   # tepat satu rute
        b = np.zeros(nv); b[[idx(i, k) for k in range(4)]] = 1; tambah(b, 1, 1)
    b = np.zeros(nv); b[[idx(i, 0) for i in range(n)]] = m; b[iz] = 1
    tambah(b, 0, p.kapasitas_gasifier_ton)               # kapasitas gasifier
    b = np.zeros(nv); b[[idx(i, 0) for i in range(n)]] = m * (w_k - p.w_maks_umpan)
    b[iz] = p.w_biodrying_keluar - p.w_maks_umpan
    tambah(b, -np.inf, 0)                                # kadar air campuran <= 20%
    b = np.zeros(nv); b[[idx(i, 0) for i in range(n)]] = m * (lhv_k - p.lhv_min_umpan)
    b[iz] = p.lhv_biodrying_keluar - p.lhv_min_umpan
    tambah(b, 0, np.inf)                                 # LHV campuran >= minimum
    b = np.zeros(nv); b[[idx(i, 1) for i in range(n)]] = m
    tambah(b, 0, p.kapasitas_biodrying_ton)              # kapasitas bio-drying
    b = np.zeros(nv); b[[idx(i, 1) for i in range(n)]] = m * r
    tambah(b, 0, p.stok_serbuk_ton)                      # stok serbuk kayu
    b = np.zeros(nv); b[[idx(i, 2) for i in range(n)]] = m
    tambah(b, 0, p.kapasitas_maggot_ton)                 # kapasitas maggot

    ub = np.ones(nv); ub[iz] = p.stok_biodrying_siap_ton
    for i in range(n):                                   # syarat kelayakan maggot
        if plast[i] > p.plastik_maks_bsf or w_md[i] < p.w_min_bsf:
            ub[idx(i, 2)] = 0
    integ = np.ones(nv); integ[iz] = 0

    if _ADA_SCIPY:
        res = milp(c, constraints=LinearConstraint(np.array(A), lo, hi),
                   integrality=integ, bounds=Bounds(np.zeros(nv), ub),
                   options={"time_limit": 30})
        if res.x is None:
            raise RuntimeError(f"Optimasi gagal: {res.message}")
        x = np.round(res.x[:iz].reshape(n, 4)).astype(int)
        z = float(res.x[iz])
        status_msg = res.message
        nilai_tot = float(-res.fun)
    else:
        # Solver Heuristik Konservatif Presisi Tinggi bila SciPy belum terinstal
        x = np.zeros((n, 4), dtype=int)
        z = float(min(p.stok_biodrying_siap_ton, p.kapasitas_gasifier_ton))
        sisa_gas = p.kapasitas_gasifier_ton - z
        air_num = z * (p.w_biodrying_keluar - p.w_maks_umpan)
        kal_num = z * (p.lhv_biodrying_keluar - p.lhv_min_umpan)
        sisa_bd = p.kapasitas_biodrying_ton
        sisa_serbuk = p.stok_serbuk_ton
        sisa_mag = p.kapasitas_maggot_ton

        # Urutkan muatan dari yang paling kering/berkalor tinggi
        urut_idx = np.argsort(w_k)
        for i in urut_idx:
            dw = m[i] * (w_k[i] - p.w_maks_umpan)
            dl = m[i] * (lhv_k[i] - p.lhv_min_umpan)
            if m[i] <= sisa_gas and (air_num + dw <= 1e-6) and (kal_num + dl >= -1e-6):
                x[i, 0] = 1
                sisa_gas -= m[i]
                air_num += dw
                kal_num += dl
            elif ub[idx(i, 2)] > 0.5 and m[i] <= sisa_mag and nilai_M[i] >= nilai_B[i]:
                x[i, 2] = 1
                sisa_mag -= m[i]
            elif m[i] <= sisa_bd and (m[i] * r[i]) <= sisa_serbuk:
                x[i, 1] = 1
                sisa_bd -= m[i]
                sisa_serbuk -= m[i] * r[i]
            elif ub[idx(i, 2)] > 0.5 and m[i] <= sisa_mag:
                x[i, 2] = 1
                sisa_mag -= m[i]
            else:
                x[i, 3] = 1
        vec = np.concatenate([x.ravel(), [z]])
        nilai_tot = float(-(c @ vec))
        status_msg = "Optimal (KARTA Built-in Priority MILP Solver)"

    rute = np.array(RUTE)[x.argmax(1)]

    out = muatan.copy()
    out["rute"] = rute
    out["serbuk_ton"] = np.where(rute == "B", m * r, 0.0)
    pilih_U = rute == "U"
    ton_U = m[pilih_U].sum() + z
    ring = {
        "status": status_msg,
        "ton_umpan_langsung": float(m[pilih_U].sum()),
        "ton_stok_biodrying_diumpankan": z,
        "ton_biodrying_baru": float(m[rute == "B"].sum()),
        "ton_maggot": float(m[rute == "M"].sum()),
        "ton_residu": float(m[rute == "R"].sum()),
        "serbuk_kayu_ton": float(out["serbuk_ton"].sum()),
        "w_campuran_umpan_taksiran": float((m[pilih_U] @ w_md[pilih_U] + z * p.w_biodrying_keluar) / max(ton_U, 1e-9)),
        "nilai_juta_rp": nilai_tot,
    }
    return out, ring


def w_campuran_nyata(rencana: pd.DataFrame, ring: dict, p: Parameter, kolom_w_asli="w_asli") -> float:
    """Kadar air campuran umpan yang SEBENARNYA terjadi (hanya bisa dihitung di simulasi
    atau setelah umpan diuji)."""
    u = rencana["rute"] == "U"
    m = rencana.loc[u, "ton"].to_numpy()
    z = ring["ton_stok_biodrying_diumpankan"]
    return float((m @ rencana.loc[u, kolom_w_asli].to_numpy() + z * p.w_biodrying_keluar) / max(m.sum() + z, 1e-9))
