# SORA · Dashboard Mutu Umpan PLTSa Putri Cempo

**SORA: Sistem Observasi, Rekomendasi, dan Analisis Sampah Berbasis Computer Vision untuk Identifikasi Komposisi, Prediksi Kadar Air, dan Estimasi Nilai Kalor serta Penentuan Jalur Pengolahan di PLTSa Putri Cempo, Surakarta.**

UNS Innovation Hackathon 2026, Sub-tema B. Pemilik masalah: DLH Kota Surakarta.

| Bagian | Tempat |
|---|---|
| Dashboard web (repo ini) | <https://sora-dashboard-hackathon-uns.streamlit.app/> |
| Aplikasi petugas di HP | <https://sora-mobile.vercel.app/> (repo `azunzios/sora-mobile`, Next.js) |

> **Status model.** Model segmentasi di aplikasi HP sudah dilatih dari data publik TACO dan ZeroWaste-f (6.003 frame, 1.512 kelompok; uji 2.769 frame): mIoU 0,41 dan galat proporsi 14,3 poin persen. Model ini belum dilatih dari foto TPS dan belum mengenali organik, tekstil, dan kayu, jadi di aplikasi tetap berlabel "Model versi uji". Pelatihan dengan foto TPS dijadwalkan 28 November–3 Desember 2026.

> **Data simulasi.** Belum ada data lapangan. Semua angka muatan di dashboard dibangkitkan oleh `demo/sora_data.py` untuk 12 TPS selama 30 hari. Rumus dan ambang rute sama dengan aplikasi HP dan lampiran laporan, jadi angkanya menunjukkan cara kerja sistem, bukan kondisi Putri Cempo yang sebenarnya. Data nyata dari HP bisa dimasukkan lewat **Laporan → Impor dari aplikasi HP**.

## Isi dashboard

Setiap halaman dirancang muat dalam satu layar laptop (1366×768 ke atas) tanpa menggulir. Di layar HP, halaman tersusun satu kolom dan bisa digulir. Periode (7, 14, 30 hari) dan jenis TPS di bagian atas berlaku untuk semua halaman.

| Halaman | Isi |
|---|---|
| Masuk | Akun demonstrasi `kepala.dlh`, `direksi.pltsa`, `analis` dengan kata sandi `sora2026` (hanya demo, bukan autentikasi sungguhan) |
| Ringkasan | Lima angka utama, peta asal muatan dan kadar air per TPS, temuan utama yang dihitung dari data, porsi tonase setiap rute |
| Peta TPS | Peta 12 TPS dan PLTSa dengan pilihan indikator (kadar air, porsi Rute R, LHV, organik, tonase), alur muatan, peringkat TPS, profil TPS terpilih |
| Muatan masuk | Tonase harian per rute dengan kadar air, curah hujan dengan kadar air, daftar muatan dengan saringan TPS, rute, dan pencarian |
| Komposisi | Komposisi berat keseluruhan dan per TPS, hubungan organik dengan kadar air, sebaran nilai kalor |
| Rute dan neraca | Tonase dan porsi setiap rute, tonase harian per rute, aturan rute berurutan beserta jumlah muatan per aturan, kebutuhan serbuk kayu, air yang perlu diuapkan, potensi listrik |
| Model dan validasi | Status model, rencana data tahap 1 (60 unit, 300 foto, 25 uji oven), pembagian data StratifiedGroupKFold, kriteria lulus dan rujukan |
| Laporan | Rekap per TPS menurut saringan, unduh Excel (rekap, rincian, keterangan), CSV, cetak atau PDF, impor CSV dari aplikasi HP |

Peta dasar memakai Esri World Light Gray (tanpa kunci API), dengan pilihan OpenStreetMap dan citra satelit. Bila ubin Esri gagal dimuat, peta otomatis beralih ke OpenStreetMap.

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
- Peta memakai ubin © Esri, © OpenStreetMap kontributor, dan citra satelit © Esri.
- Dataset publik untuk pralatih (TACO, ZeroWaste): cek lisensi masing-masing sebelum dipakai di luar riset.
