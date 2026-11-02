# KARTA prototipe v3

Kode prototipe untuk **KARTA (Kinetic Analytics for Refuse Triage & Allocation)**, gerbang cerdas mutu umpan PLTSa Putri Cempo, UNS Innovation Hackathon 2026, Sub-tema B.

> **Status 31 Oktober 2026.** Semua angka kinerja di folder `eksperimen/hasil/` berasal dari **SIMULASI** (data sintetis). Belum ada satu pun foto atau uji oven dari Putri Cempo. Jangan menulis angka simulasi sebagai kinerja lapangan di proposal.

## Mulai cepat tanpa foto/anotasi (demo zero-shot)

1. Colab: buka `notebooks/03_KARTA_Demo_Colab.ipynb`, unggah zip ini, jalankan sel dari atas. Bisa foto unggahan, URL gambar, kamera laptop, atau video.
2. Laptop: `pip install -r requirements.txt torch transformers` lalu `python demo/kamera_langsung.py`.
3. Mode `zero-shot` (CLIPSeg) **bukan model terlatih KARTA**; hanya untuk memeriksa alur dan bentuk keluaran. Ganti ke `segformer` setelah anotasi dan pelatihan.
4. Belum diuji dengan bobot CLIPSeg asli di lingkungan pengembang (unduhan Hugging Face diblokir); logika pemrosesan sudah diuji dengan segmenter tiruan. Jika ada galat saat memuat model di Colab, catat pesan galatnya.

## Alur sistem

```
QR TPS + jembatan timbang ─┐
                           ▼
foto muatan ─► [visi.py] proporsi luas tiap fraksi ─► [kadar_air.py] kadar air + LHV + interval 80%
                                                                  │
                     cuaca BMKG (hujan 24/72 jam) ────────────────┘
                                                                  ▼
                        [optimasi.py] rute tiap muatan: U umpan langsung / B bio-drying + serbuk kayu /
                                                         M maggot BSF / R residu-tunda
                                                                  ▼
                        [alur.py] log per muatan ─► ringkasan per TPS (peta sumber untuk DLH)
```

## Isi folder

| Berkas | Fungsi |
|---|---|
| `karta/konstanta.py` | Daftar 6 fraksi + koefisien literatur kadar air, LHV, massa per luas (asumsi, wajib diganti data lokal) |
| `karta/visi.py` | Foto → proporsi fraksi + peta ketidakpastian. Backend `segformer` (model utama), `petak` (baseline cepat), `yolo` (real-time tepi), `demo` (aturan warna, bukan AI); penggabungan banyak frame per muatan |
| `karta/zero_shot.py` | Segmentasi berbasis teks CLIPSeg tanpa pelatihan (demo awal) |
| `karta/tampil.py` | Menggambar masker, kotak berlabel, panel persen, peta keraguan |
| `karta/aliran.py` | Video/kamera/konveyor: segmentasi berkala, satu keputusan rute per jendela waktu |
| `notebooks/03_KARTA_Demo_Colab.ipynb` | Demo Colab: foto, URL, webcam, video |
| `demo/kamera_langsung.py` | Kamera laptop real-time dengan overlay |
| `karta/kadar_air.py` | Model fisika, koreksi linear (ridge + jackknife+), LightGBM kuantil + CQR; kalibrasi aktif |
| `karta/optimasi.py` | MILP harian (scipy/HiGHS) memilih rute tiap muatan dengan kendala kadar air ≤ 20%, LHV, kapasitas, stok serbuk kayu |
| `karta/ramalan.py` | Peramalan kadar air rata-rata hari berikutnya (ridge + pembanding persistensi) |
| `karta/alur.py` | Satu muatan: foto → hasil → rute; pencatatan CSV; ringkasan per TPS |
| `karta/perangkat.py` | Kamera, baca QR (OpenCV), kendali konveyor lewat serial |
| `karta/simulasi.py` | Generator muatan sintetis untuk menguji desain |
| `eksperimen/jalankan_simulasi.py` | Eksperimen E1–E4 (lihat di bawah), ±1 menit di CPU |
| `latih/01_potong_petak.py` | Potong foto jadi petak untuk dilabeli (drag-and-drop ke folder kelas) |
| `latih/02_latih_petak.py` | Latih pengklasifikasi petak (timm, transfer learning), validasi per foto |
| `latih/05_latih_segformer.py` | Fine-tune SegFormer (HF Transformers), validasi per muatan, melaporkan mIoU dan galat proporsi fraksi. **Belum dijalankan** |
| `latih/03_latih_yolo_seg.py` | Latih YOLO-seg dari anotasi poligon, ekspor ke ncnn/TensorRT |
| `latih/04_kalibrasi_kadar_air.py` | Kalibrasi model kadar air dari lembar uji oven |
| `demo/app_streamlit.py` | Layar operator untuk Hackathon Day |
| `demo/konveyor_arduino/konveyor_arduino.ino` | Firmware Arduino: motor konveyor, servo pengalih, sensor IR |
| `data/uji_oven_TEMPLATE.csv` | Contoh kolom lembar uji oven |

## Cara menjalankan

```bash
pip install -r requirements.txt            # inti: numpy pandas scipy scikit-learn lightgbm matplotlib opencv
python eksperimen/jalankan_simulasi.py     # hasil ke eksperimen/hasil/
pip install streamlit pyserial qrcode       # untuk demo
streamlit run demo/app_streamlit.py         # pilih "Unggah foto", model "demo"
```

Melatih model visi (Colab disarankan): `pip install torch torchvision timm` lalu `latih/01` → label petak → `latih/02`.

## Hasil simulasi (data sintetis, 90 hari × 60 truk)

| Eksperimen | Hasil | Arti untuk desain |
|---|---|---|
| E1, 30 uji oven | koreksi linear MAE 4,9 ± 0,2 poin; LightGBM 6,0 ± 0,5; fisika saja 7,4 | Dengan data sedikit, pakai **koreksi linear**, bukan gradient boosting. GBM baru menyamai pada ±240 uji oven |
| E1, interval 80% | cakupan 0,79–0,82 | Interval conformal jujur (ideal 0,80) |
| E2, kalibrasi aktif | MAE 4,87 vs acak 4,90; menang 9 dari 20 ulangan | **Tidak terbukti lebih baik.** Jangan dijual di proposal; uji lagi dengan data nyata |
| E3, robust | hari dengan campuran umpan > 20%: 13/30 (taksiran tengah), 7/30 (batas atas P90), 0/30 (P90 + target 19%) | Pakai batas atas interval + cadangan 1 poin |
| E5, galat model visi | proporsi fraksi meleset 6,0 / 4,5 / 3,2 / 2,2 / 1,2 poin → galat kadar air 6,4 / 5,7 / 4,9 / 4,1 / 3,8 poin | Agar kadar air ≤ 5 poin, model visi perlu galat proporsi ≲ 3 poin (rata-rata 6 fraksi) |
| E6, ramalan hari berikutnya | MAE 1,0 poin vs persistensi 2,6 dan rata-rata 7 hari 1,8 (67 hari uji, prakiraan hujan dianggap tepat) | Alur peramalan berfungsi; angka optimistis karena hujan dalam simulasi diketahui pasti |
| E4, vs urutan datang | energi hasil bio-drying +12,3% (29 dari 30 hari lebih tinggi) | Nilai utama KARTA: memilih muatan mana yang masuk bak bio-drying yang terbatas |

Semua angka bergantung pada asumsi dunia simulasi (`karta/simulasi.py`). Fungsinya memilih metode dan menunjukkan desain eksperimen, bukan membuktikan kinerja.

## Catatan lisensi

- Ultralytics YOLO: AGPL-3.0. Aman untuk riset dan hackathon; produk komersial tertutup perlu lisensi Enterprise atau model lain (mis. DeepLabV3-MobileNetV3 torchvision, BSD).
- Bobot SegFormer resmi NVIDIA berlisensi non-komersial. Cek sebelum dipakai di produk.
- Dataset publik (ZeroWaste, TACO): cek lisensi masing-masing sebelum dipakai untuk pralatih.
