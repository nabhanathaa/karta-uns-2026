"""Skrip Evaluasi Ilmiah Lengkap KARTA v4 (End-to-End 4 Lapisan Metrik).

Menjalankan:
1. Evaluasi Segmentasi Piksel & Proporsi Fraksi (mIoU, Macro-F1, Weighted-F1, Cohen's Kappa κ, MAE Proporsi)
   pada split Train, Val, dan Test.
2. Evaluasi Regresi Kadar Air & Nilai Kalor LHV terhadap Uji Oven SNI 19-3964-1994
   (MAE, RMSE, R², Pearson r, PICP Conformal Coverage 80%, MPIW, Winkler Score).
3. Evaluasi Keputusan Triase & Optimasi Harian MILP (Akurasi Triase, Macro-F1 Triase,
   Cohen's Kappa Triase, Pelanggaran Kadar Air Reaktor >20%, dan Nilai Ekonomi Harian).

Jalankan:
    python eksperimen/evaluasi_lengkap_v4.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

AKAR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AKAR))

from karta.alur import rute_satu_muatan  # noqa: E402
from karta.evaluasi import (evaluasi_keputusan_triase,  # noqa: E402
                            evaluasi_regresi_kadar_air,
                            evaluasi_segmentasi_piksel)
from karta.kadar_air import ModelKadarAir  # noqa: E402
from karta.optimasi import Parameter, rencana_harian, w_campuran_nyata  # noqa: E402
from karta.pretrained import FOLDER_BENCHMARK, pastikan_benchmark_gt  # noqa: E402
from karta.visi import muat_model  # noqa: E402


def main():
    t0 = time.perf_counter()
    pastikan_benchmark_gt()
    df = pd.read_csv(FOLDER_BENCHMARK / "uji_oven_surakarta.csv")
    df_citra = df.drop_duplicates(subset=["foto"]).reset_index(drop=True)

    print("=" * 78)
    print("LAPORAN EVALUASI ILMIAH END-TO-END KARTA v4 (BENCHMARK GROUND TRUTH SURAKARTA)")
    print("=" * 78)

    # 1. Evaluasi Computer Vision
    hasil_visi = {}
    for kode_m in ["karta_v4", "deeplabv3", "demo"]:
        mod = muat_model(kode_m)
        t_m = time.perf_counter()
        preds, gts = [], []
        for _, r in df_citra[df_citra["split"] == "test"].iterrows():
            bgr = np.array(Image.open(FOLDER_BENCHMARK / "images" / r["foto"]).convert("RGB"), dtype=np.uint8)[:, :, ::-1]
            msk = np.array(Image.open(FOLDER_BENCHMARK / "masks" / r["foto"]), dtype=np.uint8)
            preds.append(mod(bgr).peta_kelas)
            gts.append(msk)
        ms_per_img = (time.perf_counter() - t_m) * 1000.0 / len(preds)
        ev = evaluasi_segmentasi_piksel(np.stack(preds), np.stack(gts))
        hasil_visi[kode_m] = {
            "mIoU": ev["mIoU"],
            "macro_f1": ev["macro_f1"],
            "weighted_f1": ev["weighted_f1"],
            "cohen_kappa": ev["cohen_kappa"],
            "pixel_accuracy": ev["pixel_accuracy"],
            "mae_proporsi_pp": ev["mae_proporsi_pp"],
            "rmse_proporsi_pp": ev["rmse_proporsi_pp"],
            "latency_ms": round(ms_per_img, 2),
        }

    print("\n[1] EVALUASI COMPUTER VISION PADA TEST SET (UNSEEN TRUCKS):")
    print(pd.DataFrame(hasil_visi).T.to_string())

    # 2. Evaluasi Regresi Kadar Air & Conformal Prediction
    df_tr = df[df["split"] == "train"].reset_index(drop=True)
    df_te = df[df["split"] == "test"].reset_index(drop=True)

    hasil_regresi = {}
    hasil_triase = {}
    for met in ["fisika", "koreksi_linear", "gbm"]:
        m_air = ModelKadarAir(met, alpha_interval=0.20).fit(df_tr, df_tr["w_oven"])
        pr = m_air.predict(df_te)
        hasil_regresi[met] = evaluasi_regresi_kadar_air(
            df_te["w_oven"].to_numpy(),
            pr["w_hat"].to_numpy(),
            pr["w_bawah"].to_numpy(),
            pr["w_atas"].to_numpy(),
            alpha=0.20,
        )
        rute_p = [
            rute_satu_muatan(
                float(pr.loc[i, "w_hat"]),
                float(pr.loc[i, "w_atas"]),
                float(df_te.loc[i, "plastik_massa"]),
                float(df_te.loc[i, "organik_massa"]),
                float(df_te.loc[i, "massa_gt_inert"]),
            )[0]
            for i in df_te.index
        ]
        ev_tr = evaluasi_keputusan_triase(rute_p, df_te["rute_gt"].tolist())
        hasil_triase[met] = {k: v for k, v in ev_tr.items() if k != "confusion_matrix"}

    print("\n[2] EVALUASI TAKSIRAN KADAR AIR & INTERVAL KONFORMAL 80% (TEST SET):")
    print(pd.DataFrame(hasil_regresi).T.to_string())

    print("\n[3] EVALUASI KEPUTUSAN TRIASE MUATAN (U / B / M / R):")
    print(pd.DataFrame(hasil_triase).T.to_string())

    # 4. Evaluasi Optimasi Harian MILP
    m_terbaik = ModelKadarAir("gbm", alpha_interval=0.20).fit(df_tr, df_tr["w_oven"])
    df_hari = df.iloc[:60].copy().reset_index(drop=True)
    pr_hari = m_terbaik.predict(df_hari)
    for k in ["w_hat", "w_bawah", "w_atas", "lhv_hat", "lhv_bawah", "lhv_atas"]:
        df_hari[k] = pr_hari[k].to_numpy()

    par = Parameter(pakai_batas_atas=True, w_maks_umpan=0.195)
    rc, ring = rencana_harian(df_hari, par)
    ring["w_campuran_aktual_oven"] = round(w_campuran_nyata(rc, ring, par, kolom_w_asli="w_oven"), 4)

    print("\n[4] RINGKASAN OPTIMASI MILP HARIAN (60 TRUK):")
    for k, v in ring.items():
        print(f"  - {k:32s}: {v}")

    out_path = AKAR / "eksperimen" / "hasil" / "evaluasi_v4_benchmark.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "visi_test": hasil_visi,
                "regresi_kadar_air_test": hasil_regresi,
                "triase_test": hasil_triase,
                "optimasi_harian": ring,
                "waktu_eksekusi_detik": round(time.perf_counter() - t0, 2),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nLaporan JSON tersimpan di: {out_path}")


if __name__ == "__main__":
    main()

