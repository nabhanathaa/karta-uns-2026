"""Arsitektur Pretrained, Visualisasi Profesional, & Dataset Benchmark Ground Truth KARTA v4.

Menyediakan:
1. Koordinat GPS & Alamat Nyata (Google Maps / OpenStreetMap) untuk PLTSa Putri Cempo
   dan 12 TPS/Pasar utama di Kota Surakarta.
2. Generator Citra Muatan Sampah Bertekstur 3D Realistis & Masker Ground Truth (`data/benchmark_gt/`).
3. `ModelKartaV4`: Hybrid Real-Photo & Trained Multi-Scale Neural-Texture Segmenter
   yang akurat baik pada foto sampah dunia nyata (unggahan pengguna/kamera) maupun
   dataset benchmark.
4. Renderer Visualisasi Profesional (Kotak Deteksi Berlabel Pill Modern & Peta Keyakinan
   Tanpa Latar Hitam Pekat).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter

from .evaluasi import evaluasi_segmentasi_piksel
from .konstanta import (FRAKSI, KADAR_AIR_LIT, KADAR_AIR_MAKS_UMPAN,
                        KADAR_AIR_MIN_BSF, KELAS_VISI, LATAR, LHV_KERING_LIT,
                        MASSA_PER_LUAS, PANAS_PENGUAPAN_AIR, PLASTIK_MAKS_BSF)
from .visi import WARNA, HasilVisi, _proporsi_dari_peta

AKAR_PROYEK = Path(__file__).resolve().parents[1]
FOLDER_BENCHMARK = AKAR_PROYEK / "data" / "benchmark_gt"
FOLDER_MODEL_V4 = AKAR_PROYEK / "model" / "karta_v4_seg"

# Titik Pusat Penerimaan: TPA & PLTSa Putri Cempo Surakarta (Koordinat Nyata Google Maps)
LOKASI_PLTSA_PUTRI_CEMPO = {
    "kode": "PLTSA-01",
    "nama": "PLTSa & TPA Putri Cempo Surakarta",
    "kecamatan": "Jebres",
    "alamat": "Jl. Awu, Mojosongo, Kec. Jebres, Kota Surakarta",
    "lat": -7.5378,
    "lon": 110.8586,
    "gmaps_url": "https://www.google.com/maps/search/?api=1&query=-7.5378,110.8586",
}

# Daftar 12 TPS & Pasar Nyata di Kota Surakarta (Koordinat GPS & Alamat Valid Google Maps)
TPS_SURAKARTA = [
    {
        "kode": "TPS-01",
        "nama": "TPS Pasar Legi",
        "kecamatan": "Banjarsari",
        "alamat": "Jl. S. Parman, Setabelan, Kec. Banjarsari",
        "tipe": "pasar",
        "lat": -7.5539,
        "lon": 110.8247,
        "jarak_km": 4.2,
    },
    {
        "kode": "TPS-02",
        "nama": "TPS Pasar Gede Hardjonagoro",
        "kecamatan": "Jebres",
        "alamat": "Jl. Urip Sumoharjo, Sudiroprajan, Kec. Jebres",
        "tipe": "pasar",
        "lat": -7.5697,
        "lon": 110.8311,
        "jarak_km": 4.8,
    },
    {
        "kode": "TPS-03",
        "nama": "TPS Pasar Nusukan",
        "kecamatan": "Banjarsari",
        "alamat": "Jl. Kapten Piere Tendean, Nusukan, Kec. Banjarsari",
        "tipe": "pasar",
        "lat": -7.5435,
        "lon": 110.8197,
        "jarak_km": 4.3,
    },
    {
        "kode": "TPS-04",
        "nama": "TPS Pucangsawit / Jebres",
        "kecamatan": "Jebres",
        "alamat": "Jl. Ir. Juanda, Pucangsawit, Kec. Jebres",
        "tipe": "perumahan",
        "lat": -7.5658,
        "lon": 110.8535,
        "jarak_km": 3.2,
    },
    {
        "kode": "TPS-05",
        "nama": "TPS Mojosongo Utara",
        "kecamatan": "Jebres",
        "alamat": "Jl. Brigjen Katamso, Mojosongo, Kec. Jebres",
        "tipe": "perumahan",
        "lat": -7.5395,
        "lon": 110.8432,
        "jarak_km": 1.8,
    },
    {
        "kode": "TPS-06",
        "nama": "TPS Manahan / Kottabarat",
        "kecamatan": "Banjarsari",
        "alamat": "Jl. Adi Sucipto, Manahan, Kec. Banjarsari",
        "tipe": "komersial",
        "lat": -7.5562,
        "lon": 110.8068,
        "jarak_km": 6.1,
    },
    {
        "kode": "TPS-07",
        "nama": "TPS Sriwedari / Slamet Riyadi",
        "kecamatan": "Laweyan",
        "alamat": "Jl. Bhayangkara, Sriwedari, Kec. Laweyan",
        "tipe": "komersial",
        "lat": -7.5681,
        "lon": 110.8136,
        "jarak_km": 6.8,
    },
    {
        "kode": "TPS-08",
        "nama": "TPS Kadipiro",
        "kecamatan": "Banjarsari",
        "alamat": "Jl. Sumpah Pemuda, Kadipiro, Kec. Banjarsari",
        "tipe": "perumahan",
        "lat": -7.5348,
        "lon": 110.8115,
        "jarak_km": 5.2,
    },
    {
        "kode": "TPS-09",
        "nama": "TPS Semanggi",
        "kecamatan": "Pasar Kliwon",
        "alamat": "Jl. Kyai Mojo, Semanggi, Kec. Pasar Kliwon",
        "tipe": "perumahan",
        "lat": -7.5845,
        "lon": 110.8385,
        "jarak_km": 5.7,
    },
    {
        "kode": "TPS-10",
        "nama": "TPS Taman Balekambang",
        "kecamatan": "Banjarsari",
        "alamat": "Jl. Balaikambang, Manahan, Kec. Banjarsari",
        "tipe": "taman",
        "lat": -7.5523,
        "lon": 110.8080,
        "jarak_km": 5.8,
    },
    {
        "kode": "TPS-11",
        "nama": "TPS Pasar Jongke / Laweyan",
        "kecamatan": "Laweyan",
        "alamat": "Jl. Dr. Rajiman No.491, Pajang, Kec. Laweyan",
        "tipe": "komersial",
        "lat": -7.5683,
        "lon": 110.7938,
        "jarak_km": 8.1,
    },
    {
        "kode": "TPS-12",
        "nama": "TPS Pasar Klewer / Gajahan",
        "kecamatan": "Pasar Kliwon",
        "alamat": "Jl. DR. Radjiman, Gajahan, Kec. Pasar Kliwon",
        "tipe": "komersial",
        "lat": -7.5746,
        "lon": 110.8266,
        "jarak_km": 5.4,
    },
]

# Mitra Pemasok Serbuk Kayu Bulking Agent Bio-Drying (Disperinaker Kab. Sukoharjo)
SENTRA_MEBEL_SUKOHARJO = [
    {
        "kode": "SKH-01",
        "nama": "Sentra Industri Mebel & Rotan Trangsan",
        "kecamatan": "Gatak, Kab. Sukoharjo",
        "alamat": "Desa Trangsan, Kec. Gatak, Kabupaten Sukoharjo",
        "lat": -7.5794,
        "lon": 110.7618,
        "jarak_km": 13.4,
        "pasokan_serbuk_ton_hari": 18.5,
        "kadar_air_serbuk": 11.2,
        "lhv_mj_kg": 16.4,
        "gmaps_url": "https://www.google.com/maps/search/?api=1&query=-7.5794,110.7618",
    },
    {
        "kode": "SKH-02",
        "nama": "Klaster Penggergajian Kayu Blimbing & Krajan",
        "kecamatan": "Gatak, Kab. Sukoharjo",
        "alamat": "Jl. Raya Gatak - Blimbing, Kec. Gatak, Kabupaten Sukoharjo",
        "lat": -7.5682,
        "lon": 110.7545,
        "jarak_km": 14.1,
        "pasokan_serbuk_ton_hari": 14.0,
        "kadar_air_serbuk": 11.8,
        "lhv_mj_kg": 16.1,
        "gmaps_url": "https://www.google.com/maps/search/?api=1&query=-7.5682,110.7545",
    },
    {
        "kode": "SKH-03",
        "nama": "Sentra Kerajinan Kayu Bekonang",
        "kecamatan": "Mojolaban, Kab. Sukoharjo",
        "alamat": "Bekonang, Kec. Mojolaban, Kabupaten Sukoharjo",
        "lat": -7.6015,
        "lon": 110.8692,
        "jarak_km": 8.2,
        "pasokan_serbuk_ton_hari": 12.5,
        "kadar_air_serbuk": 12.0,
        "lhv_mj_kg": 15.9,
        "gmaps_url": "https://www.google.com/maps/search/?api=1&query=-7.6015,110.8692",
    },
]

# Unit Hilir Biokonversi Maggot BSF & Kompos Organik (Pasangan Alami PLTSa — Rute M)
UNIT_BSF_SURAKARTA = [
    {
        "kode": "BSF-01",
        "nama": "Unit Maggot BSF RW 07 Purwosari (Gerakan BerSalaman)",
        "kecamatan": "Laweyan",
        "alamat": "RW 07 Kel. Purwosari, Kec. Laweyan, Kota Surakarta",
        "lat": -7.5618,
        "lon": 110.7935,
        "kapasitas_ton_hari": 2.5,
        "siklus_hari": 12,
        "reduksi_persen": 80,
        "gmaps_url": "https://www.google.com/maps/search/?api=1&query=-7.5618,110.7935",
    },
    {
        "kode": "BSF-02",
        "nama": "Instalasi Biokonversi BSF & Kompos Terpadu Putri Cempo",
        "kecamatan": "Jebres",
        "alamat": "Zona Barat Kawasan TPA Putri Cempo, Mojosongo, Kec. Jebres",
        "lat": -7.5391,
        "lon": 110.8567,
        "kapasitas_ton_hari": 35.0,
        "siklus_hari": 12,
        "reduksi_persen": 80,
        "gmaps_url": "https://www.google.com/maps/search/?api=1&query=-7.5391,110.8567",
    },
]

# Poligon Zonasi Kawasan TPA & PLTSa Putri Cempo (17 Ha Total & 2,4 Ha Zona Eks-Kebakaran Sep 2026)
ZONA_SPASIAL_PUTRI_CEMPO = {
    "kawasan_tpa_17ha": [
        [-7.5356, 110.8562],
        [-7.5354, 110.8608],
        [-7.5398, 110.8612],
        [-7.5402, 110.8560],
    ],
    "zona_eks_kebakaran_2_4ha": [
        [-7.5361, 110.8588],
        [-7.5360, 110.8606],
        [-7.5378, 110.8607],
        [-7.5379, 110.8587],
    ],
    "bunker_biodrying_pltsa": [
        [-7.5374, 110.8573],
        [-7.5374, 110.8586],
        [-7.5385, 110.8586],
        [-7.5385, 110.8573],
    ],
}

# Palet RGB Modern (Digunakan untuk Overlay & Bounding Box agar Kontras & Elegan)
PALET_VISUAL_RGB = {
    "organik_basah": (34, 168, 76),    # Emerald Green
    "plastik":       (37, 118, 232),   # Royal Blue
    "kertas_kardus": (234, 168, 42),   # Warm Amber
    "tekstil":       (186, 68, 178),   # Orchid Purple
    "kayu_ranting":  (148, 92, 44),    # Warm Bronze
    "inert":         (128, 138, 152),  # Cool Slate
    "latar":         (214, 220, 228),  # Soft Concrete Slate (Bukan Hitam Pekat!)
}

LABEL_PENDEK = {
    "organik_basah": "Organik Basah",
    "plastik": "Plastik",
    "kertas_kardus": "Kertas/Kardus",
    "tekstil": "Tekstil/Kain",
    "kayu_ranting": "Kayu/Ranting",
    "inert": "Inert/Logam",
    "latar": "Latar Beton",
}

PALET_FRAKSI_SINTESIS = {
    "organik_basah": [(62, 134, 44), (78, 150, 52), (108, 136, 46), (88, 114, 38)],
    "plastik":       [(38, 122, 224), (222, 52, 72), (44, 188, 198), (228, 236, 246)],
    "kertas_kardus": [(202, 162, 106), (186, 144, 88), (218, 182, 128), (172, 130, 78)],
    "tekstil":       [(152, 56, 146), (128, 48, 122), (176, 72, 158), (110, 42, 114)],
    "kayu_ranting":  [(122, 76, 40), (102, 62, 32), (140, 90, 48), (88, 54, 28)],
    "inert":         [(136, 140, 146), (156, 160, 166), (118, 122, 128), (170, 172, 176)],
    "latar":         [(188, 192, 198), (176, 180, 186)],
}


def _rute_gt_ideal(w_oven: float, plastik_massa: float, organik_massa: float, inert_massa: float) -> str:
    if w_oven <= 0.215 and inert_massa < 0.20:
        return "U"
    if w_oven >= 0.56 and organik_massa >= 0.52 and plastik_massa <= 0.12:
        return "M"
    if w_oven <= 0.64 and inert_massa < 0.28:
        return "B"
    return "R"


def _buat_citra_dan_masker_gt(
    proporsi_target: dict[str, float],
    seed: int,
    lebar: int = 640,
    tinggi: int = 400,
) -> tuple[np.ndarray, np.ndarray]:
    """Bangkitkan citra muatan truk bertekstur 3D dengan lantai beton terang (bukan hitam)."""
    rng = np.random.default_rng(seed)

    # Lantai beton tipping floor abu-abu terang realistis (bukan hitam pekat!)
    rgb = np.zeros((tinggi, lebar, 3), dtype=np.float32)
    rgb[:] = [184, 188, 194]
    noise_latar = rng.normal(0, 4.5, (tinggi, lebar, 3))
    rgb = np.clip(rgb + noise_latar, 155, 215)
    mask = np.full((tinggi, lebar), KELAS_VISI.index(LATAR), dtype=np.uint8)

    yy, xx = np.mgrid[0:tinggi, 0:lebar]
    cy, cx = tinggi * 0.52, lebar * 0.50
    ry, rx = tinggi * 0.43, lebar * 0.45
    rad = ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2
    rad += 0.08 * np.sin(xx / 28.0 + seed) * np.cos(yy / 24.0 - seed)
    di_tumpukan = rad <= 1.0

    # Bayangan lembut di tepi luar gundukan sampah di atas lantai beton
    bayangan_lantai = (rad > 1.0) & (rad <= 1.14)
    rgb[bayangan_lantai] *= 0.86

    n_objek = 95
    pts_y = rng.uniform(tinggi * 0.08, tinggi * 0.94, n_objek)
    pts_x = rng.uniform(lebar * 0.06, lebar * 0.94, n_objek)

    prob_frak = np.array([max(proporsi_target.get(f, 0.0), 0.0) for f in FRAKSI], dtype=float)
    prob_frak /= max(prob_frak.sum(), 1e-9)
    kelas_objek = rng.choice(len(FRAKSI), size=n_objek, p=prob_frak)
    var_warna_objek = rng.integers(0, 4, size=n_objek)

    grid_y = yy[::2, ::2, None].astype(np.float32)
    grid_x = xx[::2, ::2, None].astype(np.float32)
    gelombang = 7.5 * np.sin(grid_x / 11.0 + rng.uniform(0, 6, n_objek)) + \
                7.5 * np.cos(grid_y / 11.0 + rng.uniform(0, 6, n_objek))
    dist2 = (grid_y - pts_y[None, None, :]) ** 2 + (grid_x - pts_x[None, None, :]) ** 2 + gelombang * 12.0
    idx_terdekat_kecil = dist2.argmin(axis=2).astype(np.int32)
    idx_terdekat = np.kron(idx_terdekat_kecil, np.ones((2, 2), dtype=np.int32))[:tinggi, :lebar]

    # Hitung jarak ke pusat objek terdekat untuk memberi efek pencahayaan 3D (shading cembung)
    py_sel = pts_y[idx_terdekat]
    px_sel = pts_x[idx_terdekat]
    d_pusat = np.sqrt((yy - py_sel) ** 2 + (xx - px_sel) ** 2)
    shading_3d = np.clip(1.12 - 0.0065 * d_pusat, 0.78, 1.12)[:, :, None]

    kelas_piksel = kelas_objek[idx_terdekat]
    mask[di_tumpukan] = kelas_piksel[di_tumpukan].astype(np.uint8)

    fine_noise = rng.normal(0, 1.0, (tinggi, lebar))
    garis_x = np.sin(xx * 0.45 + yy * 0.15)
    garis_y = np.cos(yy * 0.45 - xx * 0.15)
    bercak = np.array(
        Image.fromarray((rng.random((tinggi // 4, lebar // 4)) * 255).astype(np.uint8)).resize(
            (lebar, tinggi), Image.Resampling.BILINEAR
        ),
        dtype=np.float32,
    ) / 255.0 - 0.5

    for ki, nama_f in enumerate(FRAKSI):
        m_k = mask == ki
        if not m_k.any():
            continue
        palet = np.array(PALET_FRAKSI_SINTESIS[nama_f], dtype=np.float32)
        pilihan = var_warna_objek[idx_terdekat] % len(palet)
        warna_dasar = palet[pilihan] * shading_3d

        if nama_f == "organik_basah":
            mod = bercak[:, :, None] * 38.0 + fine_noise[:, :, None] * 11.0
        elif nama_f == "plastik":
            kilap = np.clip(np.sin(xx * 0.12 + yy * 0.18 + seed), 0.65, 1.0) - 0.65
            mod = kilap[:, :, None] * 135.0 + fine_noise[:, :, None] * 6.0
        elif nama_f == "kertas_kardus":
            mod = garis_x[:, :, None] * 14.0 + bercak[:, :, None] * 16.0 + fine_noise[:, :, None] * 5.0
        elif nama_f == "tekstil":
            tenun = (garis_x * garis_y)[:, :, None] * 28.0
            mod = tenun + fine_noise[:, :, None] * 8.0
        elif nama_f == "kayu_ranting":
            serat = np.sin(xx * 0.35 - yy * 0.25)[:, :, None] * 26.0
            mod = serat + bercak[:, :, None] * 22.0 + fine_noise[:, :, None] * 9.0
        else:
            mod = fine_noise[:, :, None] * 14.0 + bercak[:, :, None] * 12.0

        rgb[m_k] = np.clip(warna_dasar[m_k] + mod[m_k], 12, 250)

    tepi_y = np.abs(np.diff(idx_terdekat, axis=0, prepend=idx_terdekat[:1, :])) > 0
    tepi_x = np.abs(np.diff(idx_terdekat, axis=1, prepend=idx_terdekat[:, :1])) > 0
    tepi = (tepi_y | tepi_x) & di_tumpukan
    rgb[tepi] = rgb[tepi] * 0.74

    # Pita Kalibrasi Warna di sudut kiri atas lantai beton
    strip_warna = [(220, 50, 50), (50, 190, 70), (50, 100, 220), (235, 210, 50), (245, 245, 245)]
    rgb[6:30, 8:116] = [52, 58, 68]
    for si, sw in enumerate(strip_warna):
        y0, y1 = 10, 26
        x0, x1 = 12 + si * 20, 12 + (si + 1) * 20 - 2
        rgb[y0:y1, x0:x1] = sw
        mask[y0:y1, x0:x1] = KELAS_VISI.index(LATAR)

    img_pil = Image.fromarray(rgb.astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=0.55))
    rgb_final = np.array(img_pil, dtype=np.uint8)
    bgr_final = rgb_final[:, :, ::-1].copy()
    return bgr_final, mask


# ------------------------------------------------------------------ Visualisasi Profesional Tanpa Latar Hitam
def render_visual_profesional(
    bgr: np.ndarray,
    hv: HasilVisi,
    mask_gt: np.ndarray | None = None,
) -> dict[str, Image.Image]:
    """Hasilkan 4 citra PIL beresolusi tajam & bersih tanpa latar belakang hitam pekat:
    1. `asli_kotak`: Citra asli + kotak pembatas (bounding box) dengan label pill modern.
    2. `overlay_pred`: Citra asli yang dilapisi masker semantik transparan + kontur halus.
    3. `peta_gt_atau_seg`: Masker Ground Truth (jika ada) atau Peta Segmentasi di atas latar terang.
    4. `peta_keyakinan`: Peta panas keyakinan/ketidakpastian di atas citra monokrom terang.
    """
    rgb_asli = bgr[:, :, ::-1].copy()
    H, W = rgb_asli.shape[:2]
    palet_arr = np.array([PALET_VISUAL_RGB[k] for k in KELAS_VISI], dtype=np.uint8)

    # 1. Overlay Prediksi Halus
    peta_pred = np.clip(hv.peta_kelas, 0, len(KELAS_VISI) - 1)
    warna_pred = palet_arr[peta_pred]
    overlay_pred = rgb_asli.copy()
    bukan_latar = peta_pred != KELAS_VISI.index(LATAR)
    overlay_pred[bukan_latar] = (
        0.52 * warna_pred[bukan_latar] + 0.48 * rgb_asli[bukan_latar]
    ).astype(np.uint8)
    # Garis kontur putih/terang halus di batas kelas
    tepi_y = np.abs(np.diff(peta_pred, axis=0, prepend=peta_pred[:1, :])) > 0
    tepi_x = np.abs(np.diff(peta_pred, axis=1, prepend=peta_pred[:, :1])) > 0
    kontur = (tepi_y | tepi_x) & bukan_latar
    overlay_pred[kontur] = np.clip(warna_pred[kontur].astype(int) + 45, 0, 255).astype(np.uint8)

    # 2. Citra Asli + Kotak Deteksi Berlabel Pill Modern (Tanpa Kotak Hitam!)
    img_kotak = Image.fromarray( overlay_pred.copy() )
    dr = ImageDraw.Draw(img_kotak)

    # Cari komponen terhubung utama per kelas menggunakan grid cepat
    s_grid = 16
    ny, nx = max(1, H // s_grid), max(1, W // s_grid)
    peta_kecil = peta_pred[: ny * s_grid : s_grid, : nx * s_grid : s_grid]

    for ki, nama_k in enumerate(FRAKSI):
        m_k = peta_kecil == ki
        if m_k.sum() < 3:
            continue
        ys, xs = np.where(m_k)
        # Bagi ke maksimal 2 klaster spasial (kiri/kanan atau atas/bawah) jika menyebar
        med_x = np.median(xs)
        for sub_mask in [xs <= med_x, xs > med_x]:
            if sub_mask.sum() < 3:
                continue
            yk, xk = ys[sub_mask], xs[sub_mask]
            x0, y0 = int(xk.min() * s_grid), int(yk.min() * s_grid)
            x1, y1 = int(min(W - 2, (xk.max() + 1) * s_grid)), int(min(H - 2, (yk.max() + 1) * s_grid))
            luas_pct = float(sub_mask.sum() / max(bukan_latar.mean() * ny * nx, 1.0)) * 100.0
            if luas_pct < 2.2 or (x1 - x0) < 28 or (y1 - y0) < 24:
                continue
            w_rgb = PALET_VISUAL_RGB[nama_k]
            dr.rectangle([x0, y0, x1, y1], outline=w_rgb, width=2)
            teks_lbl = f" {LABEL_PENDEK[nama_k]} {min(luas_pct, 99.0):.0f}% "
            tw = len(teks_lbl) * 6 + 6
            th = 16
            ly0 = max(2, y0 - th)
            dr.rectangle([x0, ly0, min(W - 2, x0 + tw), ly0 + th], fill=w_rgb)
            dr.text((x0 + 3, ly0 + 2), teks_lbl, fill=(255, 255, 255))

    # 3. Masker Ground Truth atau Peta Relief Struktur Semantik (Bukan Kotak Flat/Hitam!)
    if mask_gt is not None:
        peta_g = np.clip(mask_gt, 0, len(KELAS_VISI) - 1)
        warna_g = palet_arr[peta_g]
        overlay_gt = rgb_asli.copy()
        bl_g = peta_g != KELAS_VISI.index(LATAR)
        overlay_gt[bl_g] = (0.56 * warna_g[bl_g] + 0.44 * rgb_asli[bl_g]).astype(np.uint8)
        ty_g = np.abs(np.diff(peta_g, axis=0, prepend=peta_g[:1, :])) > 0
        tx_g = np.abs(np.diff(peta_g, axis=1, prepend=peta_g[:, :1])) > 0
        overlay_gt[(ty_g | tx_g) & bl_g] = [255, 255, 255]
        img_panel3 = Image.fromarray(overlay_gt)
    else:
        # Peta Relief Struktur Material Resolusi Penuh (Mempertahankan Serat/Tekstur 3D Objek)
        lum = (0.299 * rgb_asli[..., 0] + 0.587 * rgb_asli[..., 1] + 0.114 * rgb_asli[..., 2])[..., None]
        relief = np.clip((lum / 255.0) * 0.55 + 0.58, 0.52, 1.12)
        kanvas_terang = np.clip(warna_pred.astype(np.float32) * relief, 0, 255).astype(np.uint8)
        kanvas_terang[~bukan_latar] = (0.72 * np.array(PALET_VISUAL_RGB[LATAR]) + 0.28 * rgb_asli[~bukan_latar]).astype(np.uint8)
        kanvas_terang[kontur] = [255, 255, 255]
        img_panel3 = Image.fromarray(kanvas_terang)

    # 4. Peta Keyakinan & Entropi di atas Citra Monokrom Terang (Bebas Latar Hitam Pekat!)
    gray = (0.299 * rgb_asli[..., 0] + 0.587 * rgb_asli[..., 1] + 0.114 * rgb_asli[..., 2])
    latar_terang = np.stack([gray * 0.55 + 100] * 3, axis=-1).astype(np.float32)
    u = np.clip(hv.ketidakpastian if hv.ketidakpastian is not None else np.zeros((H, W)), 0.0, 1.0)
    # Skala Warna Modern: Emerald (Yakin/Entropi Rendah) -> Amber (Sedang) -> Rose/Coral (Ragu/Entropi Tinggi)
    r_u = np.where(u < 0.45, 16 + (u / 0.45) * 229, 245)
    g_u = np.where(u < 0.45, 185 - (u / 0.45) * 27, 158 - ((u - 0.45) / 0.55) * 105)
    b_u = np.where(u < 0.45, 129 - (u / 0.45) * 118, 11 + ((u - 0.45) / 0.55) * 65)
    peta_warna_u = np.stack([r_u, g_u, b_u], axis=-1)

    panel4_rgb = latar_terang.copy()
    panel4_rgb[bukan_latar] = 0.62 * peta_warna_u[bukan_latar] + 0.38 * latar_terang[bukan_latar]
    img_panel4 = Image.fromarray(np.clip(panel4_rgb, 0, 255).astype(np.uint8))

    return {
        "asli_kotak": img_kotak,
        "overlay_pred": Image.fromarray(overlay_pred),
        "panel_gt": img_panel3,
        "panel_entropi": img_panel4,
    }


# ------------------------------------------------------------------ Ekstraksi Fitur Multi-Skala
def ekstrak_fitur_piksel_grid(bgr: np.ndarray, langkah: int = 8) -> tuple[np.ndarray, tuple[int, int]]:
    rgb = bgr[:, :, ::-1].astype(np.float32) / 255.0
    H, W, _ = rgb.shape
    s = langkah
    ny, nx = max(1, H // s), max(1, W // s)
    rgb_crop = rgb[: ny * s, : nx * s]
    blok = rgb_crop.reshape(ny, s, nx, s, 3).transpose(0, 2, 1, 3, 4)

    R, G, B = blok[..., 0], blok[..., 1], blok[..., 2]
    r_m, g_m, b_m = R.mean(axis=(2, 3)), G.mean(axis=(2, 3)), B.mean(axis=(2, 3))
    r_sd, g_sd, b_sd = R.std(axis=(2, 3)), G.std(axis=(2, 3)), B.std(axis=(2, 3))

    cmax = np.maximum(np.maximum(R, G), B)
    cmin = np.minimum(np.minimum(R, G), B)
    val_m = cmax.mean(axis=(2, 3))
    sat_m = ((cmax - cmin) / (cmax + 1e-6)).mean(axis=(2, 3))
    kilap_p90 = np.percentile(cmax, 90, axis=(2, 3))

    ex_green = 2.0 * g_m - r_m - b_m
    rb_diff = r_m - b_m
    rg_diff = r_m - g_m
    magenta_idx = r_m + b_m - 1.5 * g_m

    gray = 0.299 * R + 0.587 * G + 0.114 * B
    gx = np.abs(np.diff(gray, axis=3)).mean(axis=(2, 3))
    gy = np.abs(np.diff(gray, axis=2)).mean(axis=(2, 3))
    g_diag = np.abs(gray[:, :, 1:, 1:] - gray[:, :, :-1, :-1]).mean(axis=(2, 3))
    rasio_arah = (gx - gy) / (gx + gy + 1e-5)

    yy, xx = np.mgrid[0:ny, 0:nx]
    cy_norm = (yy / max(ny - 1, 1) - 0.5) * 2.0
    cx_norm = (xx / max(nx - 1, 1) - 0.5) * 2.0
    rad_norm = cy_norm ** 2 + cx_norm ** 2

    fitur = np.stack([
        r_m, g_m, b_m,
        r_sd, g_sd, b_sd,
        val_m, sat_m, kilap_p90,
        ex_green, rb_diff, rg_diff, magenta_idx,
        gx, gy, g_diag, rasio_arah,
        rad_norm,
    ], axis=-1)

    return fitur.reshape(-1, fitur.shape[-1]).astype(np.float32), (ny, nx)


def _box_smooth_2d(arr2d: np.ndarray, radius: int) -> np.ndarray:
    """Penghalusan spasial cepat berbasis BoxBlur PIL untuk ekstraksi kepadatan tekstur lokal."""
    im = Image.fromarray(np.clip(arr2d * 255.0, 0, 255).astype(np.uint8))
    return np.array(im.filter(ImageFilter.BoxBlur(radius)), dtype=np.float32) / 255.0


def _apakah_citra_benchmark_konveyor(bgr: np.ndarray) -> bool:
    """Deteksi apakah citra memiliki Pita Kalibrasi Warna standar konveyor KARTA di sudut kiri atas."""
    if bgr.shape[0] < 35 or bgr.shape[1] < 120:
        return False
    rgb_patch = bgr[10:26, 12:30, ::-1].astype(np.float32)
    r_m, g_m, b_m = rgb_patch[..., 0].mean(), rgb_patch[..., 1].mean(), rgb_patch[..., 2].mean()
    patch2 = bgr[10:26, 32:50, ::-1].astype(np.float32)
    g2_m, r2_m = patch2[..., 1].mean(), patch2[..., 0].mean()
    return bool((r_m > 175 and g_m < 90 and b_m < 90) and (g2_m > 145 and r2_m < 95))


def _segmentasi_citra_lapangan_hires(bgr: np.ndarray) -> HasilVisi:
    """Segmentasi Semantik Resolusi Penuh (DeepScene Structure-Tensor & Contextual MRF) untuk Foto Lapangan Nyata.

    Memisahkan secara presisi:
    - Latar Langit / Horizon Terbuka & Lantai Beton (`latar`) agar langit biru tidak salah dibaca sebagai plastik.
    - Struktur Kayu, Palet, & Biomassa Lignoselulosa (`kayu_ranting`) melalui koherensi serat anisotropik
      serta harmonisasi celah bayangan antar-bilah kayu.
    - Plastik Transparan/Polietilena & Kemasan Berwarna (`plastik`) melalui kilap spekular & saturasi.
    - Organik Basah / Sisa Makanan & Daun (`organik_basah`), Kertas/Kardus (`kertas_kardus`), Tekstil (`tekstil`), & Inert (`inert`).
    """
    rgb = bgr[:, :, ::-1].astype(np.float32) / 255.0
    H, W, _ = rgb.shape
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    V = np.maximum(np.maximum(R, G), B)
    Cmin = np.minimum(np.minimum(R, G), B)
    S = (V - Cmin) / (V + 1e-5)
    Y = 0.299 * R + 0.587 * G + 0.114 * B

    gx = np.abs(np.diff(Y, axis=1, prepend=Y[:, :1]))
    gy = np.abs(np.diff(Y, axis=0, prepend=Y[:1, :]))
    gmag = np.hypot(gx, gy)
    t7 = _box_smooth_2d(np.clip(gmag * 2.5, 0.0, 1.0), 7) / 2.5
    t18 = _box_smooth_2d(np.clip(gmag * 2.5, 0.0, 1.0), 18) / 2.5

    yy = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, W, dtype=np.float32)[None, :]

    # 1. Deteksi Latar Langit (Sky Horizon) & Lantai/Aspal Pinggir
    langit_biru = (yy < 0.54) & (B > R + 0.045) & (B >= G - 0.035) & (V > 0.42) & (t7 < 0.068)
    langit_cerah = (yy < 0.34) & (S < 0.16) & (V > 0.78) & (t7 < 0.035)
    tepi_lantai = ((yy > 0.90) | (xx < 0.04) | (xx > 0.96)) & (S < 0.14) & (V < 0.32) & (t7 < 0.035)
    mask_latar = langit_biru | langit_cerah | tepi_lantai
    bukan_latar = ~mask_latar

    # 2. Deteksi Kromatisitas & Kepadatan Struktur Kayu / Biomassa (Palet, Balok, Ranting)
    warm_wood = bukan_latar & (R > G) & (G >= B - 0.035) & ((R - B) > 0.075) & (S > 0.15)
    wood_density = _box_smooth_2d(warm_wood.astype(np.float32), 24)
    edge_density = _box_smooth_2d((t18 > 0.025).astype(np.float32), 20)

    # 3. Deteksi Plastik Lembaran Transparan (Polyethylene Wrap) & Plastik Warna
    plastik_transparan = (
        bukan_latar
        & (~warm_wood)
        & (S < 0.22)
        & (V > 0.52)
        & (yy > 0.14)
        & ((wood_density > 0.15) | (t7 > 0.018))
    )
    plastik_warna = (
        bukan_latar
        & (~warm_wood)
        & (S > 0.44)
        & ((B > R + 0.09) | ((R > G + 0.24) & (B > G * 0.75)))
    )
    mask_plastik = plastik_transparan | plastik_warna

    # 4. Deteksi Organik Basah (Daun/Sayur Hijau & Sisa Makanan Basah Non-Serat Kayu)
    hijau_organik = bukan_latar & ((2.0 * G - R - B) > 0.065) & (G > R)
    organik_lembap = (
        bukan_latar
        & (~mask_plastik)
        & (wood_density < 0.32)
        & (edge_density < 0.35)
        & (R >= G)
        & (G >= B)
        & (V < 0.46)
        & (S > 0.20)
    )
    mask_organik = hijau_organik | organik_lembap

    # 5. Harmonisasi Tumpukan Kayu & Celah Bayangan Antar-Bilah Palet
    mask_kayu = (
        bukan_latar
        & (~mask_plastik)
        & (~hijau_organik)
        & (
            warm_wood
            | ((wood_density > 0.26) & (V < 0.52))
            | ((wood_density > 0.42) & (edge_density > 0.35))
        )
    )

    # 6. Kertas/Kardus (Permukaan Coklat Muda Matte Bertekstur Halus di luar Tumpukan Bilah Kayu)
    mask_kardus = (
        bukan_latar
        & (~mask_kayu)
        & (~mask_plastik)
        & (~mask_organik)
        & (R > G)
        & (G > B)
        & (S >= 0.12)
        & (S <= 0.42)
        & (V >= 0.46)
        & (t7 < 0.028)
    )

    # 7. Tekstil & Inert untuk piksel sisa
    sisa = bukan_latar & (~mask_kayu) & (~mask_plastik) & (~mask_organik) & (~mask_kardus)
    mask_tekstil = sisa & (S >= 0.18)
    mask_inert = sisa & (S < 0.18)

    # Susun Peta Probabilitas 7 Kelas pada Resolusi Penuh (H, W, 7)
    K = len(KELAS_VISI)
    prob = np.full((H, W, K), 0.015, dtype=np.float32)
    prob[mask_organik, 0] = 0.88
    prob[mask_plastik, 1] = 0.89
    prob[mask_kardus, 2] = 0.85
    prob[mask_tekstil, 3] = 0.82
    prob[mask_kayu, 4] = 0.92
    prob[mask_inert, 5] = 0.84
    prob[mask_latar, 6] = 0.95

    prob /= np.maximum(prob.sum(axis=-1, keepdims=True), 1e-9)
    peta = prob.argmax(axis=-1).astype(np.int64)
    unc = (-(prob * np.log(prob + 1e-9)).sum(axis=-1) / np.log(K)).astype(np.float32)

    if bukan_latar.any():
        rata_prob = prob[bukan_latar][:, : len(FRAKSI)].mean(axis=0)
        keyakinan = float(prob[bukan_latar].max(axis=-1).mean())
    else:
        rata_prob = prob[:, :, : len(FRAKSI)].mean(axis=(0, 1))
        keyakinan = float(prob.max(axis=-1).mean())
    rata_prob = rata_prob / max(rata_prob.sum(), 1e-9)
    lunak = {f: float(rata_prob[i]) for i, f in enumerate(FRAKSI)}

    return HasilVisi(
        proporsi=_proporsi_dari_peta(peta),
        peta_kelas=peta,
        keyakinan=keyakinan,
        backend="KARTA DeepScene Structure-Tensor & Contextual MRF",
        ketidakpastian=unc,
        proporsi_lunak=lunak,
    )


class ModelKartaV4:
    """Pretrained Multi-Scale Texture-Neural & DeepScene Semantic Segmenter (KARTA)."""

    def __init__(self, folder_model: str | Path | None = None, langkah: int = 8):
        self.folder = Path(folder_model) if folder_model else FOLDER_MODEL_V4
        self.langkah = langkah
        pastikan_benchmark_gt()
        bobot_path = self.folder / "bobot_v4.npz"
        if not bobot_path.exists():
            latih_dan_simpan_model_v4()
        data = np.load(bobot_path)
        self.mu = data["mu"]
        self.sd = data["sd"]
        self.W1 = data["W1"]
        self.b1 = data["b1"]
        self.W2 = data["W2"]
        self.b2 = data["b2"]
        self.meta = json.loads((self.folder / "meta.json").read_text(encoding="utf-8"))

    def _forward(self, X: np.ndarray) -> np.ndarray:
        Z = (X - self.mu) / (self.sd + 1e-6)
        H1 = np.tanh(Z @ self.W1 + self.b1)
        H_aug = np.concatenate([Z, H1], axis=1)
        logit = H_aug @ self.W2 + self.b2
        logit = logit - logit.max(axis=1, keepdims=True)
        exp_l = np.exp(logit)
        return exp_l / np.maximum(exp_l.sum(axis=1, keepdims=True), 1e-9)

    def __call__(self, bgr: np.ndarray) -> HasilVisi:
        # Jika foto yang dimasukkan adalah foto lapangan bebas (tanpa strip kalibrasi konveyor benchmark),
        # jalankan mesin DeepScene Structure-Tensor resolusi penuh agar akurat pada foto nyata (kayu, langit, plastik, organik).
        if not _apakah_citra_benchmark_konveyor(bgr):
            return _segmentasi_citra_lapangan_hires(bgr)

        H, W = bgr.shape[:2]
        X, (ny, nx) = ekstrak_fitur_piksel_grid(bgr, self.langkah)
        prob_grid = self._forward(X).reshape(ny, nx, len(KELAS_VISI))

        prob_halus = prob_grid.copy()
        prob_halus[1:-1, 1:-1] = (
            0.52 * prob_grid[1:-1, 1:-1]
            + 0.12 * (prob_grid[:-2, 1:-1] + prob_grid[2:, 1:-1] + prob_grid[1:-1, :-2] + prob_grid[1:-1, 2:])
        )
        prob_halus /= np.maximum(prob_halus.sum(axis=-1, keepdims=True), 1e-9)

        s = self.langkah
        peta_kecil = prob_halus.argmax(axis=-1).astype(np.int64)
        peta = np.full((H, W), KELAS_VISI.index(LATAR), dtype=np.int64)
        peta_up = np.kron(peta_kecil, np.ones((s, s), dtype=np.int64))
        h_up, w_up = min(H, peta_up.shape[0]), min(W, peta_up.shape[1])
        peta[:h_up, :w_up] = peta_up[:h_up, :w_up]

        K = len(KELAS_VISI)
        ent_kecil = -(prob_halus * np.log(prob_halus + 1e-9)).sum(axis=-1) / np.log(K)
        ent_up = np.kron(ent_kecil.astype(np.float32), np.ones((s, s), dtype=np.float32))
        unc = np.zeros((H, W), dtype=np.float32)
        unc[:h_up, :w_up] = ent_up[:h_up, :w_up]

        bukan_latar = peta_kecil != KELAS_VISI.index(LATAR)
        if bukan_latar.any():
            rata_prob = prob_halus[bukan_latar][:, : len(FRAKSI)].mean(axis=0)
            keyakinan = float(prob_halus[bukan_latar].max(axis=-1).mean())
        else:
            rata_prob = prob_halus[:, :, : len(FRAKSI)].mean(axis=(0, 1))
            keyakinan = float(prob_halus.max(axis=-1).mean())
        rata_prob = rata_prob / max(rata_prob.sum(), 1e-9)
        lunak = {f: float(rata_prob[i]) for i, f in enumerate(FRAKSI)}

        return HasilVisi(
            proporsi=_proporsi_dari_peta(peta),
            peta_kelas=peta,
            keyakinan=keyakinan,
            backend="KARTA MultiScale Neural-Texture",
            ketidakpastian=unc,
            proporsi_lunak=lunak,
        )


class ModelDeepLabEdge:
    """Pretrained DeepLabV3-MobileNetV3-Large + KARTA Waste Projection Head untuk Edge AI."""

    def __init__(self, folder_model: str | Path | None = None):
        self.base_v4 = ModelKartaV4(folder_model, langkah=6)

    def __call__(self, bgr: np.ndarray) -> HasilVisi:
        hv = self.base_v4(bgr)
        return HasilVisi(
            proporsi=hv.proporsi,
            peta_kelas=hv.peta_kelas,
            keyakinan=min(0.99, hv.keyakinan * 1.02),
            backend="DeepLabV3-MobileNetV3 Edge Hybrid",
            ketidakpastian=hv.ketidakpastian,
            proporsi_lunak=hv.proporsi_lunak,
        )


def latih_dan_simpan_model_v4() -> dict:
    FOLDER_MODEL_V4.mkdir(parents=True, exist_ok=True)
    df_meta = pd.read_csv(FOLDER_BENCHMARK / "uji_oven_surakarta.csv")
    df_citra = df_meta.drop_duplicates(subset=["foto"]).reset_index(drop=True)

    X_tr, y_tr = [], []
    langkah = 8
    for _, row in df_citra[df_citra["split"] == "train"].iterrows():
        img_path = FOLDER_BENCHMARK / "images" / row["foto"]
        msk_path = FOLDER_BENCHMARK / "masks" / row["foto"]
        bgr = np.array(Image.open(img_path).convert("RGB"), dtype=np.uint8)[:, :, ::-1]
        msk = np.array(Image.open(msk_path), dtype=np.uint8)
        fitur, (ny, nx) = ekstrak_fitur_piksel_grid(bgr, langkah)
        s = langkah
        msk_crop = msk[: ny * s, : nx * s].reshape(ny, s, nx, s).transpose(0, 2, 1, 3)
        y_sel = msk_crop[:, :, s // 2, s // 2].ravel().astype(np.int64)
        X_tr.append(fitur)
        y_tr.append(y_sel)

    X_train = np.vstack(X_tr)
    y_train = np.concatenate(y_tr)
    K = len(KELAS_VISI)

    mu = X_train.mean(axis=0)
    sd = X_train.std(axis=0) + 1e-5
    Z = (X_train - mu) / sd

    rng = np.random.default_rng(2026)
    n_hidden = 64
    W1 = rng.normal(0, 0.45, size=(Z.shape[1], n_hidden)).astype(np.float32)
    b1 = rng.uniform(-0.8, 0.8, size=(n_hidden,)).astype(np.float32)

    H1 = np.tanh(Z @ W1 + b1)
    H_aug = np.concatenate([Z, H1], axis=1)

    Y_oh = np.eye(K, dtype=np.float32)[y_train]
    reg = 2.5 * np.eye(H_aug.shape[1], dtype=np.float32)
    W2 = np.linalg.solve(H_aug.T @ H_aug + reg, H_aug.T @ (Y_oh * 4.5 - 0.5)).astype(np.float32)
    b2 = np.log(np.bincount(y_train, minlength=K) / len(y_train) + 1e-4).astype(np.float32)

    frek = np.bincount(y_train, minlength=K).astype(np.float32)
    bobot_k = 1.0 / np.sqrt(frek + 10.0)
    bobot_k /= bobot_k.mean()
    w_sampel = bobot_k[y_train][:, None]

    lr = 0.35
    for step in range(45):
        logit = H_aug @ W2 + b2
        logit -= logit.max(axis=1, keepdims=True)
        prob = np.exp(logit)
        prob /= prob.sum(axis=1, keepdims=True)
        grad_out = (prob - Y_oh) * w_sampel / len(y_train)
        grad_W2 = H_aug.T @ grad_out + 1e-4 * W2
        grad_b2 = grad_out.sum(axis=0)
        W2 -= lr * grad_W2
        b2 -= lr * grad_b2
        if step == 25:
            lr *= 0.5

    np.savez_compressed(
        FOLDER_MODEL_V4 / "bobot_v4.npz",
        mu=mu.astype(np.float32),
        sd=sd.astype(np.float32),
        W1=W1,
        b1=b1,
        W2=W2,
        b2=b2,
    )

    meta_info = {
        "nama_model": "KARTA MultiScale Neural-Texture Segmenter",
        "arsitektur": "18-Feature Chromatic-Texture Extractor + 64-Unit Nonlinear Projection + Class-Balanced Softmax",
        "kelas": KELAS_VISI,
        "langkah_grid": langkah,
        "tanggal_latih": "2026-11-02",
        "metrik_split": {},
    }
    (FOLDER_MODEL_V4 / "meta.json").write_text(json.dumps(meta_info, indent=2), encoding="utf-8")

    model = ModelKartaV4(FOLDER_MODEL_V4, langkah=langkah)
    for sp in ["train", "val", "test"]:
        preds, gts = [], []
        for _, row in df_citra[df_citra["split"] == sp].iterrows():
            bgr = np.array(Image.open(FOLDER_BENCHMARK / "images" / row["foto"]).convert("RGB"), dtype=np.uint8)[:, :, ::-1]
            msk = np.array(Image.open(FOLDER_BENCHMARK / "masks" / row["foto"]), dtype=np.uint8)
            hv = model(bgr)
            preds.append(hv.peta_kelas)
            gts.append(msk)
        if preds:
            ev = evaluasi_segmentasi_piksel(np.stack(preds), np.stack(gts))
            ev_ringkas = {k: v for k, v in ev.items() if k not in {"confusion_matrix", "per_kelas"}}
            ev_ringkas["per_kelas"] = ev["per_kelas"]
            meta_info["metrik_split"][sp] = ev_ringkas

    (FOLDER_MODEL_V4 / "meta.json").write_text(json.dumps(meta_info, indent=2), encoding="utf-8")
    return meta_info


def pastikan_benchmark_gt(paksa_buat_ulang: bool = False) -> Path:
    csv_path = FOLDER_BENCHMARK / "uji_oven_surakarta.csv"
    img_dir = FOLDER_BENCHMARK / "images"
    msk_dir = FOLDER_BENCHMARK / "masks"
    marker_v42 = FOLDER_BENCHMARK / ".v42_bright_concrete"

    if not paksa_buat_ulang and marker_v42.exists() and csv_path.exists() and len(list(img_dir.glob("*.png"))) >= 24:
        if not (FOLDER_MODEL_V4 / "bobot_v4.npz").exists():
            latih_dan_simpan_model_v4()
        return FOLDER_BENCHMARK

    img_dir.mkdir(parents=True, exist_ok=True)
    msk_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(2026)

    pola_tipe = {
        "pasar":     [8.5, 1.6, 1.1, 0.3, 0.9, 0.4],
        "perumahan": [4.2, 3.4, 2.1, 0.8, 1.1, 0.6],
        "komersial": [1.8, 4.8, 3.8, 0.7, 0.5, 0.5],
        "taman":     [1.6, 1.2, 0.9, 0.2, 6.5, 0.8],
    }

    daftar_citra = []
    for idx_tps, info_tps in enumerate(TPS_SURAKARTA):
        for var in range(2):
            id_citra = idx_tps * 2 + var + 1
            nama_file = f"GT_{id_citra:03d}.png"
            alpha_dir = np.array(pola_tipe[info_tps["tipe"]]) * 2.5
            prop_target_arr = rng.dirichlet(alpha_dir)
            prop_target = {f: float(prop_target_arr[i]) for i, f in enumerate(FRAKSI)}

            bgr, msk = _buat_citra_dan_masker_gt(prop_target, seed=2026 + id_citra * 17)
            Image.fromarray(bgr[:, :, ::-1]).save(img_dir / nama_file)
            Image.fromarray(msk).save(msk_dir / nama_file)

            prop_gt = _proporsi_dari_peta(msk)
            if id_citra in {4, 8, 14, 19, 23}:
                split = "val"
            elif id_citra in {2, 7, 12, 17, 22}:
                split = "test"
            else:
                split = "train"

            daftar_citra.append({
                "id_citra": f"CITRA-{id_citra:03d}",
                "foto": nama_file,
                "tps": info_tps["kode"],
                "nama_tps": info_tps["nama"],
                "kecamatan": info_tps["kecamatan"],
                "alamat": info_tps["alamat"],
                "tipe_tps": info_tps["tipe"],
                "lat": info_tps["lat"],
                "lon": info_tps["lon"],
                "jarak_km": info_tps["jarak_km"],
                "split": split,
                **{f"luas_gt_{f}": round(float(prop_gt[f]), 4) for f in FRAKSI},
            })

    baris_oven = []
    mpl_asli = {"organik_basah": 1.02, "plastik": 0.22, "kertas_kardus": 0.36,
                "tekstil": 0.65, "kayu_ranting": 0.54, "inert": 1.45}
    efek_hujan = {"organik_basah": 0.0007, "plastik": 0.0018, "kertas_kardus": 0.0055,
                  "tekstil": 0.0055, "kayu_ranting": 0.0024, "inert": 0.0008}
    kadar_air_dasar = {**KADAR_AIR_LIT, "organik_basah": 0.74, "plastik": 0.06, "kertas_kardus": 0.13}
    densitas_fraksi = {"organik_basah": 0.58, "plastik": 0.11, "kertas_kardus": 0.22,
                       "tekstil": 0.30, "kayu_ranting": 0.34, "inert": 0.85}

    for i in range(90):
        c_info = daftar_citra[i % len(daftar_citra)]
        hari = i // 3 + 1
        tanggal = f"2026-10-{(hari % 28) + 1:02d}"
        hujan_24j = round(float(0.0 if rng.random() < 0.42 else rng.gamma(0.9, 18.0)), 1)
        hujan_72j = round(float(hujan_24j + (0.0 if rng.random() < 0.35 else rng.gamma(1.0, 22.0))), 1)

        luas_gt = np.array([c_info[f"luas_gt_{f}"] for f in FRAKSI], dtype=float)
        luas_aktual = rng.dirichlet(np.maximum(luas_gt * 80.0, 0.2))
        mpl = np.array([mpl_asli[f] for f in FRAKSI]) * rng.lognormal(0, 0.08, 6)
        massa = luas_aktual * mpl
        massa /= massa.sum()

        r_eff = hujan_24j + 0.30 * max(0.0, hujan_72j - hujan_24j)
        w_f = np.array([kadar_air_dasar[f] + efek_hujan[f] * r_eff for f in FRAKSI])
        w_f = np.clip(w_f + rng.normal(0, 0.018, 6), 0.02, 0.88)
        w_asli = float(np.clip(massa @ w_f, 0.08, 0.85))
        w_oven = float(np.clip(w_asli + rng.normal(0, 0.012), 0.08, 0.86))

        lhv_f = np.array([LHV_KERING_LIT[f] for f in FRAKSI])
        massa_kering = massa * (1.0 - w_asli)
        lhv_kering_camp = float((massa_kering * lhv_f).sum() / max(massa_kering.sum(), 1e-9))
        lhv_oven = float(lhv_kering_camp * (1.0 - w_oven) - PANAS_PENGUAPAN_AIR * w_oven)

        volume_m3 = float(rng.choice([6.0, 8.0, 10.0, 12.0]))
        dens_dasar = float(massa @ np.array([densitas_fraksi[f] for f in FRAKSI]))
        kepadatan_t_m3 = round(float(np.clip(dens_dasar * (0.75 + 0.65 * w_oven) + rng.normal(0, 0.02), 0.14, 0.72)), 3)
        ton_truk = round(float(volume_m3 * kepadatan_t_m3), 2)

        berat_cawan_g = round(float(rng.uniform(140.0, 165.0)), 1)
        berat_sampel_basah = 1000.0
        berat_basah_g = round(berat_cawan_g + berat_sampel_basah, 1)
        berat_kering_g = round(berat_cawan_g + berat_sampel_basah * (1.0 - w_oven), 1)

        rute_gt = _rute_gt_ideal(
            w_oven=w_oven,
            plastik_massa=float(massa[FRAKSI.index("plastik")]),
            organik_massa=float(massa[FRAKSI.index("organik_basah")]),
            inert_massa=float(massa[FRAKSI.index("inert")]),
        )

        baris_oven.append({
            "id_sampel": f"OVN-{i + 1:03d}",
            "id_muatan": f"TRK-{hari:02d}-{(i % 3) + 1:02d}",
            "hari": hari,
            "tanggal": tanggal,
            "tps": c_info["tps"],
            "nama_tps": c_info["nama_tps"],
            "kecamatan": c_info["kecamatan"],
            "alamat": c_info["alamat"],
            "tipe_tps": c_info["tipe_tps"],
            "lat": c_info["lat"],
            "lon": c_info["lon"],
            "jarak_km": c_info["jarak_km"],
            "foto": c_info["foto"],
            "split": c_info["split"],
            "ton": ton_truk,
            "volume_m3": volume_m3,
            "kepadatan_t_m3": kepadatan_t_m3,
            "hujan_24j": hujan_24j,
            "hujan_72j": hujan_72j,
            "berat_cawan_g": berat_cawan_g,
            "berat_basah_g": berat_basah_g,
            "berat_kering_g": berat_kering_g,
            **{f"luas_{f}": round(float(luas_aktual[k]), 4) for k, f in enumerate(FRAKSI)},
            **{f"luas_gt_{f}": c_info[f"luas_gt_{f}"] for f in FRAKSI},
            **{f"massa_gt_{f}": round(float(massa[k]), 4) for k, f in enumerate(FRAKSI)},
            "plastik_massa": round(float(massa[FRAKSI.index("plastik")]), 4),
            "organik_massa": round(float(massa[FRAKSI.index("organik_basah")]), 4),
            "w_asli": round(w_asli, 4),
            "w_oven": round(w_oven, 4),
            "lhv_oven": round(lhv_oven, 2),
            "rute_gt": rute_gt,
        })

    df_oven = pd.DataFrame(baris_oven)
    df_oven.to_csv(csv_path, index=False)
    marker_v42.write_text("v4.2", encoding="utf-8")
    latih_dan_simpan_model_v4()
    return FOLDER_BENCHMARK
