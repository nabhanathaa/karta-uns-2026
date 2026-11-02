"""Konstanta KARTA: daftar fraksi sampah dan koefisien literatur.

PENTING: semua angka koefisien di sini adalah ASUMSI AWAL dari literatur umum
(Tchobanoglous dkk., 1993, Integrated Solid Waste Management; nilai tipikal
sampah kota). Angka ini WAJIB diganti dengan hasil uji oven dan uji kalor
sampel Putri Cempo sendiri. Jangan dikutip sebagai data Surakarta.
"""

# Urutan kelas dipakai oleh model visi (indeks 0..6). "latar" = bukan sampah
# (lantai, dinding, bak truk) dan tidak ikut dihitung proporsinya.
FRAKSI = [
    "organik_basah",   # sisa makanan, sayur, buah, sampah pasar
    "plastik",         # kantong, botol, sachet, styrofoam
    "kertas_kardus",   # kertas, karton, kardus
    "tekstil",         # kain, pakaian, popok (dikelompokkan di sini)
    "kayu_ranting",    # ranting, daun, kayu, sampah taman
    "inert",           # logam, kaca, batu, tanah, keramik
]
LATAR = "latar"
KELAS_VISI = FRAKSI + [LATAR]

# Kadar air tipikal per fraksi (fraksi massa air, basis basah).
KADAR_AIR_LIT = {
    "organik_basah": 0.70,
    "plastik": 0.05,       # plastik kotor menahan air permukaan; literatur bersih 0,02
    "kertas_kardus": 0.10,
    "tekstil": 0.15,
    "kayu_ranting": 0.40,
    "inert": 0.05,
}

# Nilai kalor bawah (LHV) basis KERING, MJ/kg. LHV basis basah dihitung dengan
# rumus koreksi air di kadar_air.lhv_basah().
LHV_KERING_LIT = {
    "organik_basah": 15.0,
    "plastik": 33.0,
    "kertas_kardus": 16.0,
    "tekstil": 18.0,
    "kayu_ranting": 18.0,
    "inert": 0.5,
}

# Massa per satuan luas yang terlihat kamera (relatif, organik = 1).
# Kantong plastik menutupi luas besar tetapi ringan; sisa makanan padat.
# Ini asumsi paling lemah di seluruh sistem, karena itu dikalibrasi ulang
# dari muatan yang ditimbang per fraksi saat sampling.
MASSA_PER_LUAS = {
    "organik_basah": 1.00,
    "plastik": 0.15,
    "kertas_kardus": 0.40,
    "tekstil": 0.50,
    "kayu_ranting": 0.60,
    "inert": 1.20,
}

PANAS_PENGUAPAN_AIR = 2.44  # MJ per kg air (pada 25 °C)

# Syarat umpan gasifikasi PLTSa (pernyataan Kepala DLH, Radar Solo 21 Mar 2025)
KADAR_AIR_MAKS_UMPAN = 0.20

# Syarat umpan maggot BSF (Dortmans dkk., 2017, Eawag)
KADAR_AIR_MIN_BSF = 0.60
PLASTIK_MAKS_BSF = 0.05
