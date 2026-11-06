# SORA · Dashboard Mutu Umpan PLTSa Putri Cempo

**SORA: Sistem Observasi, Rekomendasi, dan Analisis Sampah Berbasis Computer Vision untuk Identifikasi Komposisi, Prediksi Kadar Air, dan Estimasi Nilai Kalor serta Penentuan Jalur Pengolahan di PLTSa Putri Cempo, Surakarta.**

UNS Innovation Hackathon 2026, Sub-tema B. Pemilik masalah: DLH Kota Surakarta.

| Bagian | Tempat |
|---|---|
| Dashboard web (repo ini) | <https://karta-uns-2026.streamlit.app/> |
| Aplikasi petugas di HP | repo `azunzios/karta-mobile` (Next.js, Vercel) |
| Proposal | `Proposal_SORA_UNS_Hackathon_2026.pdf` (dan `.docx`) |

> **Data simulasi.** Belum ada data lapangan. Semua angka di dashboard dibangkitkan oleh `demo/sora_data.py` untuk 12 TPS selama 30 hari. Rumus dan ambang rute sama dengan aplikasi HP dan lampiran laporan, jadi angkanya menunjukkan cara kerja sistem, bukan kondisi Putri Cempo yang sebenarnya. Data nyata dari HP bisa dimasukkan lewat **Pusat laporan → Impor CSV dari aplikasi HP**.

## Isi dashboard

| Halaman | Isi |
|---|---|
| Masuk | Akun demonstrasi `kepala.dlh`, `direksi.pltsa`, `analis` dengan kata sandi `sora2026` (hanya demo, bukan autentikasi sungguhan) |
| Beranda | Ringkasan hari terakhir, tonase per rute, TPS prioritas pembinaan, alur kerja SORA |
| Muatan masuk | Log setiap truk dengan filter TPS, jenis, rute, tanggal, dan pencarian; grafik tonase, kadar air, dan curah hujan |
| Peta TPS | Peta interaktif 12 TPS dan PLTSa, warna menurut indikator (kadar air, porsi Rute R, LHV, organik, tonase), alur muatan beranimasi, peringkat TPS |
| Komposisi sampah | Komposisi berat keseluruhan dan per TPS, hubungan organik dengan kadar air, sebaran nilai kalor |
| Rute dan neraca | Tonase per rute, aturan rute berurutan, kebutuhan serbuk kayu, air yang perlu diuapkan, potensi listrik |
| Model dan validasi | Status model, rencana data tahap 1 (60 unit, 300 foto, 25 uji oven), pembagian data StratifiedGroupKFold, kriteria lulus |
| Pusat laporan | Rekap per TPS menurut filter, unduh Excel (rekap, rincian, keterangan), CSV, cetak atau PDF, impor CSV dari HP |

## Rumus dan aturan yang dipakai

Sama persis dengan `lib/karta` di aplikasi HP dan Bab 3 lampiran laporan.

| Besaran | Rumus |
|---|---|
| Kadar air fisika | w = Σ yₖ · wₖ (wₖ: organik 0,70; plastik 0,05; kertas 0,10; tekstil 0,15; kayu 0,40; inert 0,05) |
| Nilai kalor bersih | LHV = (1 − w) · LHV_kering − 2,443 · w |
| Dosis serbuk kayu | d = (w − 0,50) / (0,50 − 0,12), dibatasi 10–20 % |
| Potensi listrik | kWh/ton = 1000 · LHV · 0,20 / 3,6 |

Aturan rute diperiksa berurutan, aturan pertama yang terpenuhi menjadi rekomendasi:

1. Inert ≥ 20 % → **R** (area residu)
2. Batas atas kadar air ≤ 20 % → **U** (umpan gasifikasi)
3. Kadar air ≥ 60 %, organik ≥ 60 %, plastik ≤ 5 % → **M** (maggot BSF dan kompos)
4. Kadar air < 65 % → **B** (bio-drying dengan serbuk kayu)
5. Selain itu → **R**

## Menjalankan

```bash
pip install streamlit numpy
python demo/sora_data.py                 # membuat ulang demo/web/data/sora_demo.json (opsional)
streamlit run demo/app_streamlit.py
```

Tanpa Streamlit, halaman yang sama bisa dibuka langsung:

```bash
cd demo/web && python -m http.server 8000   # buka http://localhost:8000
```

## Struktur

```
demo/
  app_streamlit.py     pembungkus Streamlit (entrypoint Streamlit Cloud)
  sora_data.py         pembangkit data simulasi
  web/
    index.html         kerangka halaman dan ikon
    css/sora.css       tema SORA (navy, emas sogan, motif kawung)
    js/app.js          logika halaman, grafik, peta, laporan, impor CSV
    data/              sora_demo.json
    vendor/            ECharts 5.5.1, Leaflet 1.9.4, SheetJS 0.18.5 (disimpan lokal, lisensi terlampir)
karta/, latih/, eksperimen/, notebooks/   kode riset tahap awal (nama paket lama), tidak dipakai dashboard
```

Pelatihan model segmentasi yang dipakai aplikasi HP ada di repo aplikasi, folder `training/` (notebook `SORA_Latih_DeepLabv3plus.ipynb`).

## Catatan

- Koordinat TPS di peta adalah perkiraan dan perlu dicek ulang bersama DLH.
- Peta memakai ubin © OpenStreetMap kontributor dan © CARTO.
- Dataset publik untuk pralatih (TACO, ZeroWaste): cek lisensi masing-masing sebelum dipakai di luar riset.
