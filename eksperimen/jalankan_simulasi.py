"""Eksperimen SIMULASI KARTA (data sintetis, bukan data Putri Cempo).

Menjawab tiga pertanyaan desain sebelum turun ke lapangan:
  E1. Berapa uji oven yang dibutuhkan, dan model mana yang cocok untuk data sedikit?
  E2. Apakah kalibrasi aktif (memilih muatan paling tidak pasti) lebih hemat daripada acak?
  E3. Apakah memakai batas atas interval (robust) menjaga umpan tetap <= 20% kadar air?

Jalankan dari folder prototipe:  python eksperimen/jalankan_simulasi.py
Keluaran: eksperimen/hasil/*.png, hasil_simulasi.json, contoh_rencana_harian.csv
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

AKAR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AKAR))
from karta.kadar_air import (KOLOM_LUAS, ModelKadarAir, lhv_basah, lhv_kering_campuran,  # noqa: E402
                             luas_ke_massa, pilih_muatan_uji_oven)
from karta.optimasi import Parameter, rencana_harian, w_campuran_nyata  # noqa: E402
from karta.ramalan import uji_berurutan  # noqa: E402
from karta.simulasi import buat_muatan, mae_proporsi  # noqa: E402

SEED = 2026
KELUAR = AKAR / "eksperimen" / "hasil"
KELUAR.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"figure.dpi": 130, "font.size": 9})
CATATAN = "SIMULASI - data sintetis, bukan data lapangan"


def evaluasi(model, te):
    p = model.predict(te)
    y = te["w_asli"].to_numpy()
    return {"mae_pp": float(np.abs(p.w_hat - y).mean() * 100),
            "cakupan80": float(((y >= p.w_bawah) & (y <= p.w_atas)).mean()),
            "lebar_pp": float((p.w_atas - p.w_bawah).mean() * 100)}


def e1_kurva_belajar(df, ulang=20):
    te = df[df.hari >= 60]
    pool = df[df.hari < 60]
    baris = []
    for n in [15, 30, 60, 120, 240]:
        for r in range(ulang):
            tr = pool.sample(n, random_state=SEED + 1000 * n + r)
            for met in ["fisika", "koreksi_linear", "gbm"]:
                if met == "gbm" and n < 30:
                    continue
                ev = evaluasi(ModelKadarAir(met, seed=r).fit(tr, tr.w_oven), te)
                baris.append({"n_uji_oven": n, "metode": met, "ulang": r, **ev})
    hasil = pd.DataFrame(baris)
    ring = hasil.groupby(["n_uji_oven", "metode"])[["mae_pp", "cakupan80", "lebar_pp"]].agg(["mean", "std"]).round(3)

    fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
    warna = {"fisika": "#8a8a8a", "koreksi_linear": "#1f6f8b", "gbm": "#d1793b"}
    for met, g in hasil.groupby("metode"):
        s = g.groupby("n_uji_oven")
        ax[0].errorbar(s.mae_pp.mean().index, s.mae_pp.mean(), yerr=s.mae_pp.std(), marker="o",
                       capsize=3, label=met, color=warna[met])
        ax[1].plot(s.cakupan80.mean().index, s.cakupan80.mean(), marker="o", label=met, color=warna[met])
    ax[0].axhline(5, ls="--", c="k", lw=0.8); ax[0].text(16, 5.1, "target proposal 5 poin", fontsize=7)
    ax[0].set(xscale="log", xlabel="jumlah muatan diuji oven", ylabel="MAE kadar air (poin %)",
              title="E1. Galat taksiran vs jumlah uji oven")
    ax[1].axhline(0.8, ls="--", c="k", lw=0.8)
    ax[1].set(xscale="log", xlabel="jumlah muatan diuji oven", ylabel="cakupan interval 80%",
              title="Kejujuran interval (ideal 0,80)", ylim=(0.5, 1))
    for a in ax:
        a.set_xticks([15, 30, 60, 120, 240], ["15", "30", "60", "120", "240"]); a.minorticks_off()
    ax[0].legend(fontsize=7)
    fig.suptitle(CATATAN, fontsize=7, color="#b00")
    fig.tight_layout(); fig.savefig(KELUAR / "E1_kurva_belajar.png"); plt.close(fig)
    return hasil, ring


def e2_kalibrasi_aktif(df, ulang=20, n_awal=10, n_akhir=30, per_putaran=5):
    te = df[df.hari >= 60]
    pool_all = df[df.hari < 60]
    hasil = {"acak": [], "aktif": []}
    for r in range(ulang):
        pool = pool_all.sample(600, random_state=SEED + r)       # kandidat: muatan yang bisa diambil sampelnya
        awal = pool.sample(n_awal, random_state=SEED + 99 + r)
        acak = pd.concat([awal, pool.drop(awal.index).sample(n_akhir - n_awal, random_state=r)])
        hasil["acak"].append(evaluasi(ModelKadarAir().fit(acak, acak.w_oven), te)["mae_pp"])
        terpilih = awal
        while len(terpilih) < n_akhir:
            m = ModelKadarAir().fit(terpilih, terpilih.w_oven)
            baru = pilih_muatan_uji_oven(m, pool.drop(terpilih.index), k=per_putaran)
            terpilih = pd.concat([terpilih, pool.loc[baru]])
        hasil["aktif"].append(evaluasi(ModelKadarAir().fit(terpilih, terpilih.w_oven), te)["mae_pp"])
    a, b = np.array(hasil["acak"]), np.array(hasil["aktif"])
    return {"mae_acak_mean": float(a.mean()), "mae_acak_sd": float(a.std()),
            "mae_aktif_mean": float(b.mean()), "mae_aktif_sd": float(b.std()),
            "aktif_lebih_baik_pada": f"{int((b < a).sum())} dari {ulang} ulangan"}


VARIAN = {"titik": Parameter(pakai_batas_atas=False),
          "robust": Parameter(pakai_batas_atas=True),
          "robust_buffer": Parameter(pakai_batas_atas=True, w_maks_umpan=0.19)}


def e3_robust(df, n_hari_uji=30):
    latih = df[df.hari < 30].sample(30, random_state=SEED)      # 30 uji oven
    model = ModelKadarAir().fit(latih, latih.w_oven)
    baris, contoh = [], None
    for h in sorted(df.hari.unique())[-n_hari_uji:]:
        hari = df[df.hari == h].copy()
        hari = hari.join(model.predict(hari))
        hari["plastik_massa"] = luas_ke_massa(hari[KOLOM_LUAS])["massa_plastik"]
        for robust, P in VARIAN.items():
            rc, ring = rencana_harian(hari, P)
            baris.append({"hari": h, "robust": robust, "hujan_24j": hari.hujan_24j.iloc[0],
                          "w_nyata": w_campuran_nyata(rc, ring, P),
                          "ton_umpan": ring["ton_umpan_langsung"] + ring["ton_stok_biodrying_diumpankan"],
                          "ton_umpan_segar": ring["ton_umpan_langsung"],
                          "ton_maggot": ring["ton_maggot"], "serbuk_ton": ring["serbuk_kayu_ton"],
                          "nilai_juta_rp": ring["nilai_juta_rp"]})
            if robust == "robust_buffer" and contoh is None and ring["ton_umpan_langsung"] > 0:
                contoh = (rc, ring)
    hasil = pd.DataFrame(baris)
    ring = hasil.groupby("robust").agg(
        hari_melanggar_20pct=("w_nyata", lambda s: int((s > 0.20).sum())),
        w_nyata_maks=("w_nyata", "max"), ton_umpan_rata=("ton_umpan", "mean"),
        ton_umpan_segar_rata=("ton_umpan_segar", "mean"), ton_maggot_rata=("ton_maggot", "mean"),
        nilai_juta_rp_rata=("nilai_juta_rp", "mean")).round(3)

    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    warna = {"titik": "#d1793b", "robust": "#7a9cc6", "robust_buffer": "#1f4e6b"}
    label = {"titik": "taksiran tengah saja", "robust": "batas atas P90",
             "robust_buffer": "batas atas P90 + target 19%"}
    for robust, g in hasil.groupby("robust"):
        ax.plot(g.hari, g.w_nyata * 100, marker="o", ms=3, label=label[robust], color=warna[robust])
    ax.axhline(20, ls="--", c="k", lw=0.8)
    ax.set(xlabel="hari simulasi", ylabel="kadar air NYATA campuran umpan (%)",
           title="E3. Kadar air umpan yang benar-benar terjadi")
    ax.legend(fontsize=7)
    fig.suptitle(CATATAN, fontsize=7, color="#b00")
    fig.tight_layout(); fig.savefig(KELUAR / "E3_robust_vs_titik.png"); plt.close(fig)
    return hasil, ring, contoh


def e5_sensitivitas_visi(ulang=8):
    """Seberapa akurat model visi harus dibuat? Ubah galat proporsi fraksi dari kamera,
    ukur galat kadar air akhir (model dilatih dari 30 uji oven)."""
    baris = []
    for konsentrasi in [15, 30, 60, 120, 400, 5000]:
        d = buat_muatan(n_hari=60, truk_per_hari=60, galat_kamera=konsentrasi, seed=SEED)
        te = d[d.hari >= 40]
        for r in range(ulang):
            tr = d[d.hari < 40].sample(30, random_state=SEED + r)
            ev = evaluasi(ModelKadarAir(seed=r).fit(tr, tr.w_oven), te)
            baris.append({"mae_proporsi_pp": mae_proporsi(d), "konsentrasi": konsentrasi, **ev})
    h = pd.DataFrame(baris)
    return h.groupby("konsentrasi").agg(mae_proporsi_pp=("mae_proporsi_pp", "mean"), mae_air_pp=("mae_pp", "mean"),
                                        sd_mae_air=("mae_pp", "std"), cakupan80=("cakupan80", "mean")).round(2).reset_index()


def e6_ramalan(df):
    latih = df[df.hari < 30].sample(30, random_state=SEED)
    model = ModelKadarAir().fit(latih, latih.w_oven)
    p = model.predict(df)
    d = df.assign(w_hat=p.w_hat.to_numpy()).groupby("hari").agg(w_rata=("w_hat", "mean"), hujan=("hujan_24j", "first")).reset_index()
    return uji_berurutan(d)


def _energi_biodrying_gj(sub, w_keluar=0.18):
    """Energi (GJ) hasil bio-drying dari muatan terpilih, dihitung dengan kadar air ASLI."""
    lk = lhv_kering_campuran(sub[[f"luas_asli_{c[5:]}" for c in KOLOM_LUAS]].set_axis(KOLOM_LUAS, axis=1))
    massa_keluar = sub["ton"].to_numpy() * (1 - sub["w_asli"].to_numpy()) / (1 - w_keluar)
    return float((massa_keluar * lhv_basah(lk, w_keluar)).sum())  # ton x MJ/kg = GJ


def e4_vs_cara_sekarang(df, n_hari_uji=30):
    """Cara sekarang (asumsi): bak bio-drying diisi muatan sesuai urutan datang
    sampai penuh. KARTA: bak diisi muatan pilihan optimasi. Bandingkan energi
    hasil pengeringan (dihitung dengan kadar air ASLI) dan serbuk kayu."""
    latih = df[df.hari < 30].sample(30, random_state=SEED)
    model = ModelKadarAir().fit(latih, latih.w_oven)
    P = VARIAN["robust_buffer"]
    baris = []
    for h in sorted(df.hari.unique())[-n_hari_uji:]:
        hari = df[df.hari == h].copy()
        hari = hari.join(model.predict(hari))
        hari["plastik_massa"] = luas_ke_massa(hari[KOLOM_LUAS])["massa_plastik"]
        rc, ring = rencana_harian(hari, P)
        fifo = hari[hari["ton"].cumsum() <= P.kapasitas_biodrying_ton]
        baris.append({"hari": h,
                      "gj_karta": _energi_biodrying_gj(rc[rc.rute == "B"]),
                      "gj_urutan_datang": _energi_biodrying_gj(fifo),
                      "ton_bd_karta": rc.loc[rc.rute == "B", "ton"].sum(),
                      "ton_bd_urutan_datang": fifo["ton"].sum()})
    h = pd.DataFrame(baris)
    return {"gj_per_hari_karta": round(h.gj_karta.mean(), 1),
            "gj_per_hari_urutan_datang": round(h.gj_urutan_datang.mean(), 1),
            "kenaikan_persen": round(100 * (h.gj_karta.sum() / h.gj_urutan_datang.sum() - 1), 1),
            "hari_karta_lebih_tinggi": f"{int((h.gj_karta > h.gj_urutan_datang).sum())} dari {len(h)}",
            "ton_bd_rata_karta": round(h.ton_bd_karta.mean(), 1),
            "ton_bd_rata_urutan_datang": round(h.ton_bd_urutan_datang.mean(), 1)}


def main():
    t0 = time.time()
    df = buat_muatan(n_hari=90, truk_per_hari=60, seed=SEED)
    info = {"catatan": CATATAN, "n_muatan": len(df),
            "mae_proporsi_kamera_pp": round(mae_proporsi(df), 2),
            "kadar_air_asli_rata": round(float(df.w_asli.mean()), 3)}
    print("data:", info)

    h1, r1 = e1_kurva_belajar(df)
    print("\nE1 kurva belajar\n", r1)
    r2 = e2_kalibrasi_aktif(df)
    print("\nE2 kalibrasi aktif\n", r2)
    h3, r3, contoh = e3_robust(df)
    print("\nE3 robust vs titik\n", r3)

    r5 = e5_sensitivitas_visi()
    print("\nE5 sensitivitas terhadap galat model visi\n", r5)
    r6 = e6_ramalan(df)
    print("\nE6 ramalan kadar air hari berikutnya\n", r6)
    r4 = e4_vs_cara_sekarang(df)
    print("\nE4 KARTA vs urutan datang\n", r4)

    rc, ring = contoh
    kol = ["id_muatan", "tps", "ton", "w_hat", "w_bawah", "w_atas", "lhv_hat", "plastik_massa", "rute", "serbuk_ton"]
    rc[kol].round(3).to_csv(KELUAR / "contoh_rencana_harian.csv", index=False)
    r1.columns = ["_".join(c) for c in r1.columns]
    json.dump({"info": info,
               "E1": r1.reset_index().to_dict(orient="records"),
               "E2": r2,
               "E3": r3.reset_index().to_dict(orient="records"),
               "E4": r4,
               "E5": r5.to_dict(orient="records"),
               "E6": r6,
               "contoh_ringkasan_hari": ring,
               "detik": round(time.time() - t0, 1)},
              open(KELUAR / "hasil_simulasi.json", "w"), indent=2, default=float)
    print(f"\nselesai {time.time() - t0:.0f} detik -> {KELUAR}")


if __name__ == "__main__":
    main()
