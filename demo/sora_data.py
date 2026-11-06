"""Data demonstrasi untuk dashboard SORA.

Belum ada data lapangan, jadi dashboard memakai data SIMULASI yang dibangkitkan di sini.
Semua rumus dan ambang sama dengan aplikasi petugas (karta-mobile/lib/karta) dan
lampiran laporan Bab 3, supaya angka di HP, dashboard, dan dokumen konsisten:

- kadar air fisika   w = sum(y_k * w_k)                       (Pers. 3.9, Tchobanoglous dkk. 1993)
- LHV basah          LHV = (1 - w) * LHV_kering - 2,443 * w   (Pers. 3.17, ISO 18125 / ISO 21654)
- dosis serbuk kayu  d = (w - 0,50) / (0,50 - 0,12), dibatasi 10-20 %   (Pers. 3.19)
- rute               R bila inert >= 20 %; U bila batas atas w <= 20 %;
                     M bila w >= 60 %, organik >= 60 %, plastik <= 5 %; B bila w < 65 %; selain itu R

Skenario simulasi memakai rentang kadar air +/- 7 poin (asumsi setelah kalibrasi uji oven).
Koordinat TPS adalah perkiraan dan perlu dicek ulang bersama DLH.

Jalankan:  python demo/sora_data.py   -> menulis demo/web/data/sora_demo.json
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

FRAKSI = ["organik_basah", "plastik", "kertas_kardus", "tekstil", "kayu_ranting", "inert"]
W_FRAKSI = np.array([0.70, 0.05, 0.10, 0.15, 0.40, 0.05])
H_KERING = np.array([14.1, 31.7, 16.2, 18.0, 18.5, 0.5])
SERAP = np.array([1, 0, 1, 1, 0, 0], float)
KALOR_UAP_AIR = 2.443
SETENGAH_RENTANG = 0.07

PLTSA = {"kode": "PLTSA", "nama": "PLTSa Putri Cempo", "kecamatan": "Jebres",
         "alamat": "Mojosongo, Jebres, Kota Surakarta", "lat": -7.5378, "lon": 110.8586}

# Koordinat perkiraan; tipe mengikuti jenis TPS di aplikasi petugas.
TPS = [
    ("TPS-01", "TPS Pasar Legi", "Banjarsari", "pasar", -7.5539, 110.8247, 4.2),
    ("TPS-02", "TPS Pasar Gede", "Jebres", "pasar", -7.5697, 110.8311, 4.8),
    ("TPS-03", "TPS Pasar Nusukan", "Banjarsari", "pasar", -7.5435, 110.8197, 4.3),
    ("TPS-04", "TPS Pucangsawit", "Jebres", "permukiman", -7.5658, 110.8535, 3.2),
    ("TPS-05", "TPS Mojosongo", "Jebres", "permukiman", -7.5395, 110.8432, 1.8),
    ("TPS-06", "TPS Manahan", "Banjarsari", "ruang_publik", -7.5562, 110.8068, 6.1),
    ("TPS-07", "TPS Sriwedari", "Laweyan", "ruang_publik", -7.5681, 110.8136, 6.8),
    ("TPS-08", "TPS Kadipiro", "Banjarsari", "permukiman", -7.5348, 110.8115, 5.2),
    ("TPS-09", "TPS Semanggi", "Pasar Kliwon", "permukiman", -7.5845, 110.8385, 5.7),
    ("TPS-10", "TPS Balekambang", "Banjarsari", "ruang_publik", -7.5523, 110.8080, 5.8),
    ("TPS-11", "TPS Pasar Jongke", "Laweyan", "pasar", -7.5683, 110.7938, 8.1),
    ("TPS-12", "TPS Pasar Klewer", "Pasar Kliwon", "pasar", -7.5746, 110.8266, 5.4),
]

# Rerata komposisi MASSA per jenis TPS (urutan = FRAKSI) dan konsentrasi Dirichlet.
POLA = {
    "pasar": ([0.76, 0.06, 0.07, 0.02, 0.05, 0.04], 45),
    "permukiman": ([0.55, 0.17, 0.11, 0.06, 0.05, 0.06], 30),
    "ruang_publik": ([0.42, 0.14, 0.12, 0.03, 0.24, 0.05], 22),
}
TRIP = {"pasar": (3, 6), "permukiman": (2, 4), "ruang_publik": (1, 3)}


def rute(y: np.ndarray, w: float, w_atas: float) -> str:
    persen = y * 100
    if persen[5] >= 20:
        return "R"
    if w_atas <= 0.20:
        return "U"
    if w >= 0.60 and persen[0] >= 60 and persen[1] <= 5:
        return "M"
    if w < 0.65:
        return "B"
    return "R"


def lhv_basah(y: np.ndarray, w: float) -> float:
    kering = y * (1 - W_FRAKSI)
    lk = float((kering / kering.sum()) @ H_KERING) if kering.sum() > 0 else 0.0
    return (1 - w) * lk - KALOR_UAP_AIR * w


def bangkitkan(hari: int = 30, akhir: str = "2026-11-06", seed: int = 2026) -> dict:
    rng = np.random.default_rng(seed)
    t_akhir = datetime.fromisoformat(akhir)
    tanggal = [t_akhir - timedelta(days=hari - 1 - i) for i in range(hari)]
    # Hujan harian (mm): peluang hari hujan naik menuju musim hujan.
    hujan = []
    for i in range(hari):
        p = 0.35 + 0.35 * i / max(1, hari - 1)
        hujan.append(round(float(rng.gamma(1.6, 9.0)) if rng.random() < p else 0.0, 1))
    muatan = []
    nomor = 0
    for i, tgl in enumerate(tanggal):
        r24 = hujan[i]
        r72 = round(sum(hujan[max(0, i - 2): i + 1]), 1)
        for kode, nama, kec, tipe, *_ in TPS:
            rata, kons = POLA[tipe]
            for _ in range(int(rng.integers(TRIP[tipe][0], TRIP[tipe][1] + 1))):
                y = rng.dirichlet(np.array(rata) * kons)
                if rng.random() < 0.05:  # sesekali puing atau kaca dari TPS
                    y[5] += rng.uniform(0.18, 0.35)
                    y = y / y.sum()
                if tipe != "pasar" and r24 < 2 and rng.random() < 0.16:  # muatan kering kemasan
                    y = rng.dirichlet(np.array([0.05, 0.60, 0.25, 0.05, 0.01, 0.04]) * 40)
                w_fis = float(y @ W_FRAKSI)
                w = w_fis + 0.022 * math.log1p(r24) * float(y @ SERAP) + 0.010 * math.log1p(r72) \
                    + rng.normal(0, 0.025)
                w = float(np.clip(w, 0.06, 0.85))
                wb, wa = max(0.0, w - SETENGAH_RENTANG), min(1.0, w + SETENGAH_RENTANG)
                r = rute(y, w, wa)
                lhv = lhv_basah(y, w)
                dosis = min(0.20, max(0.10, (w - 0.50) / (0.50 - 0.12))) if r == "B" else 0.0
                jam = 5 + rng.uniform(0, 9.5)
                waktu = tgl.replace(hour=int(jam), minute=int((jam % 1) * 60))
                ton = round(float(rng.uniform(2.5, 7.5)), 2)
                nomor += 1
                muatan.append({
                    "id": f"SR-{waktu:%m%d}-{nomor:04d}", "t": waktu.strftime("%Y-%m-%dT%H:%M"),
                    "tps": kode, "pelat": f"AD {int(rng.integers(1000, 9999))} {'ABCDEFGHJKLMNPRSTUVWXYZ'[int(rng.integers(0, 23))]}{'ABCDEFGHJKLMNPRSTUVWXYZ'[int(rng.integers(0, 23))]}",
                    "ton": ton, "w": round(w * 100, 1), "wb": round(wb * 100, 1), "wa": round(wa * 100, 1),
                    "lhv": round(lhv, 2), "lhvb": round(lhv_basah(y, wa), 2), "lhva": round(lhv_basah(y, wb), 2),
                    **{k: round(float(v) * 100, 1) for k, v in zip(["org", "pla", "ker", "tek", "kay", "ine"], y)},
                    "r24": r24, "r72": r72, "rute": r, "dosis": round(dosis * 100, 1),
                    "kwh": round(max(0.0, 1000 * lhv * 0.2 / 3.6), 0),
                    "cek": bool(rng.random() < 0.04), "sumber": "simulasi",
                })
    muatan.sort(key=lambda m: m["t"])
    return {
        "meta": {"dibuat": datetime.now().strftime("%Y-%m-%d %H:%M"), "sumber": "simulasi",
                 "periode": [tanggal[0].strftime("%Y-%m-%d"), tanggal[-1].strftime("%Y-%m-%d")],
                 "setengah_rentang_poin": SETENGAH_RENTANG * 100, "seed": seed},
        "pltsa": PLTSA,
        "tps": [{"kode": k, "nama": n, "kecamatan": c, "tipe": t, "lat": la, "lon": lo, "jarak_km": j}
                for k, n, c, t, la, lo, j in TPS],
        "hujan": [{"tanggal": d.strftime("%Y-%m-%d"), "mm": h} for d, h in zip(tanggal, hujan)],
        "muatan": muatan,
    }


def tulis(jalur: Path | None = None) -> Path:
    jalur = jalur or Path(__file__).parent / "web" / "data" / "sora_demo.json"
    jalur.parent.mkdir(parents=True, exist_ok=True)
    jalur.write_text(json.dumps(bangkitkan(), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return jalur


if __name__ == "__main__":
    p = tulis()
    d = json.loads(p.read_text())
    from collections import Counter
    c = Counter(m["rute"] for m in d["muatan"])
    print(p, len(d["muatan"]), "muatan", dict(c), f"{p.stat().st_size/1024:.0f} KB")
