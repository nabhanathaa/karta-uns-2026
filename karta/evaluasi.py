"""Modul Evaluasi Ilmiah End-to-End KARTA (Visi Komputer, Regresi Kadar Air, & Triase).

Menyediakan metrik standar akademik dan industri untuk:
1. Segmentasi Semantik & Estimasi Proporsi Fraksi (Computer Vision):
   - Confusion Matrix (KxK)
   - IoU (Intersection over Union / Jaccard Index) per kelas & mIoU
   - Precision, Recall, F1-Score (Dice Coefficient) per kelas, Macro-F1, & Weighted-F1
   - Pixel Accuracy & Balanced Class Accuracy
   - Cohen's Kappa (κ) untuk kesepakatan piksel terkoreksi peluang acak
   - MAE & RMSE Proporsi Luas Fraksi (poin persen) & Cosine Similarity komposisi

2. Estimasi Kadar Air & Nilai Kalor LHV (Regresi & Kalibrasi Konformal):
   - MAE (Mean Absolute Error) & RMSE (Root Mean Squared Error) dalam poin persen
   - R² (Coefficient of Determination) & Korelasi Pearson (r)
   - PICP (Prediction Interval Coverage Probability) untuk Conformal Prediction
   - MPIW (Mean Prediction Interval Width) & Winkler Interval Score

3. Keputusan Triase & Optimasi Operasional PLTSa:
   - Akurasi Triase, Macro-F1 Triase, & Cohen's Kappa (κ) Triase terhadap Rute Ground Truth
   - Reactor Moisture Violation Rate (% hari/batch melanggar batas kadar air > 20%)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .konstanta import FRAKSI, KELAS_VISI, LATAR


def evaluasi_segmentasi_piksel(
    peta_pred: np.ndarray,
    peta_gt: np.ndarray,
    abaikan_indeks: int = 255,
) -> dict:
    """Hitung metrik evaluasi segmentasi semantik lengkap antara peta prediksi dan ground truth.

    Args:
        peta_pred: Array 2D/3D (H, W) atau (N, H, W) berisi indeks kelas prediksi (0..6).
        peta_gt: Array 2D/3D (H, W) atau (N, H, W) berisi indeks kelas ground truth (0..6).
        abaikan_indeks: Nilai piksel yang diabaikan (default 255).

    Returns:
        Dictionary berisi mIoU, Macro-F1, Weighted-F1, Cohen's Kappa, Pixel Accuracy,
        metrik per kelas, confusion matrix, dan galat proporsi fraksi.
    """
    pred = np.asarray(peta_pred, dtype=np.int64).ravel()
    gt = np.asarray(peta_gt, dtype=np.int64).ravel()
    valid = (gt != abaikan_indeks) & (gt >= 0) & (gt < len(KELAS_VISI))
    pred = np.clip(pred[valid], 0, len(KELAS_VISI) - 1)
    gt = gt[valid]

    K = len(KELAS_VISI)
    if len(gt) == 0:
        return {}

    # Confusion Matrix K x K (baris = Ground Truth, kolom = Prediksi)
    conf = np.bincount(gt * K + pred, minlength=K * K).reshape(K, K)

    tp = np.diag(conf).astype(float)
    fp = conf.sum(axis=0).astype(float) - tp
    fn = conf.sum(axis=1).astype(float) - tp
    support = conf.sum(axis=1).astype(float)
    total = float(conf.sum())

    # Kelas yang hadir di Ground Truth atau Prediksi
    hadir = (support + fp) > 0

    iou = np.where(hadir, tp / np.maximum(tp + fp + fn, 1e-9), np.nan)
    precision = np.where(tp + fp > 0, tp / np.maximum(tp + fp, 1e-9), 0.0)
    recall = np.where(support > 0, tp / np.maximum(support, 1e-9), 0.0)
    f1 = np.where(precision + recall > 0, 2 * precision * recall / np.maximum(precision + recall, 1e-9), 0.0)

    # Rata-rata pada kelas yang muncul di Ground Truth
    mask_gt = support > 0
    miou = float(np.nanmean(iou[mask_gt])) if mask_gt.any() else 0.0
    macro_f1 = float(np.mean(f1[mask_gt])) if mask_gt.any() else 0.0
    macro_prec = float(np.mean(precision[mask_gt])) if mask_gt.any() else 0.0
    macro_rec = float(np.mean(recall[mask_gt])) if mask_gt.any() else 0.0
    weighted_f1 = float(np.sum(f1 * support) / max(total, 1e-9))
    pixel_acc = float(tp.sum() / max(total, 1e-9))

    # Cohen's Kappa (κ) = (p_o - p_e) / (1 - p_e)
    p_o = pixel_acc
    p_e = float(np.sum(conf.sum(axis=1) * conf.sum(axis=0)) / max(total * total, 1e-9))
    kappa = float((p_o - p_e) / max(1.0 - p_e, 1e-9)) if p_e < 1.0 else 1.0

    # Proporsi Fraksi (tanpa latar)
    idx_fraksi = [KELAS_VISI.index(f) for f in FRAKSI]
    hit_pred = np.array([ (pred == i).sum() for i in idx_fraksi ], dtype=float)
    hit_gt = np.array([ (gt == i).sum() for i in idx_fraksi ], dtype=float)
    prop_pred = hit_pred / max(hit_pred.sum(), 1e-9)
    prop_gt = hit_gt / max(hit_gt.sum(), 1e-9)

    mae_prop_pp = float(np.abs(prop_pred - prop_gt).mean() * 100.0)
    rmse_prop_pp = float(np.sqrt(np.mean((prop_pred - prop_gt) ** 2)) * 100.0)
    cos_sim = float(np.dot(prop_pred, prop_gt) / max(np.linalg.norm(prop_pred) * np.linalg.norm(prop_gt), 1e-9))

    per_kelas = []
    for i, nama in enumerate(KELAS_VISI):
        per_kelas.append({
            "kelas": nama,
            "iou": round(float(iou[i]) if not np.isnan(iou[i]) else 0.0, 4),
            "precision": round(float(precision[i]), 4),
            "recall": round(float(recall[i]), 4),
            "f1_score": round(float(f1[i]), 4),
            "proporsi_gt_pct": round(float(prop_gt[i] * 100) if i < len(FRAKSI) else 0.0, 2),
            "proporsi_pred_pct": round(float(prop_pred[i] * 100) if i < len(FRAKSI) else 0.0, 2),
            "selisih_prop_pp": round(float((prop_pred[i] - prop_gt[i]) * 100) if i < len(FRAKSI) else 0.0, 2),
            "piksel_gt": int(support[i]),
        })

    return {
        "mIoU": round(miou, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "macro_precision": round(macro_prec, 4),
        "macro_recall": round(macro_rec, 4),
        "cohen_kappa": round(kappa, 4),
        "pixel_accuracy": round(pixel_acc, 4),
        "mae_proporsi_pp": round(mae_prop_pp, 2),
        "rmse_proporsi_pp": round(rmse_prop_pp, 2),
        "cosine_similarity_proporsi": round(cos_sim, 4),
        "per_kelas": per_kelas,
        "confusion_matrix": conf,
        "nama_kelas": KELAS_VISI,
    }


def evaluasi_regresi_kadar_air(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_bawah: np.ndarray | None = None,
    y_atas: np.ndarray | None = None,
    alpha: float = 0.20,
    target_mae_pp: float = 5.0,
) -> dict:
    """Evaluasi taksiran kadar air (atau LHV) beserta interval prediksi konformal.

    Menghitung MAE, RMSE, R², Korelasi Pearson, proporsi sampel yang memenuhi target
    galat <= 5 poin persen, PICP (Prediction Interval Coverage Probability),
    MPIW (Mean Prediction Interval Width), dan Winkler Score.
    """
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    err = yp - yt
    abs_err = np.abs(err)

    mae_pp = float(abs_err.mean() * 100.0)
    rmse_pp = float(np.sqrt(np.mean(err ** 2)) * 100.0)
    median_ae_pp = float(np.median(abs_err) * 100.0)
    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((yt - yt.mean()) ** 2))
    r2 = float(1.0 - ss_res / max(ss_tot, 1e-12))
    corr = float(np.corrcoef(yt, yp)[0, 1]) if len(yt) > 1 else 1.0
    lolos_target_pct = float((abs_err * 100.0 <= target_mae_pp).mean() * 100.0)

    hasil = {
        "n_sampel": int(len(yt)),
        "mae_pp": round(mae_pp, 2),
        "rmse_pp": round(rmse_pp, 2),
        "median_ae_pp": round(median_ae_pp, 2),
        "r2_score": round(r2, 4),
        "pearson_r": round(corr, 4),
        "within_5pp_pct": round(lolos_target_pct, 1),
    }

    if y_bawah is not None and y_atas is not None:
        lo = np.asarray(y_bawah, dtype=float)
        hi = np.asarray(y_atas, dtype=float)
        tercakup = (yt >= lo) & (yt <= hi)
        picp = float(tercakup.mean())
        lebar = hi - lo
        mpiw_pp = float(lebar.mean() * 100.0)

        # Winkler Score untuk interval prediksi (semakin kecil semakin baik)
        penalti_bawah = np.where(yt < lo, (2.0 / alpha) * (lo - yt), 0.0)
        penalti_atas = np.where(yt > hi, (2.0 / alpha) * (yt - hi), 0.0)
        winkler = float((lebar + penalti_bawah + penalti_atas).mean() * 100.0)

        hasil.update({
            "picp_coverage": round(picp, 4),
            "target_coverage": round(1.0 - alpha, 2),
            "mpiw_lebar_pp": round(mpiw_pp, 2),
            "winkler_score_pp": round(winkler, 2),
        })

    return hasil


def evaluasi_keputusan_triase(
    rute_pred: list[str] | np.ndarray,
    rute_gt: list[str] | np.ndarray,
    label_rute: list[str] | None = None,
) -> dict:
    """Evaluasi ketepatan keputusan triase muatan (U, B, M, R) terhadap rute Ground Truth."""
    label = label_rute or ["U", "B", "M", "R"]
    K = len(label)
    p_idx = np.array([label.index(r) if r in label else K - 1 for r in rute_pred], dtype=np.int64)
    g_idx = np.array([label.index(r) if r in label else K - 1 for r in rute_gt], dtype=np.int64)

    conf = np.bincount(g_idx * K + p_idx, minlength=K * K).reshape(K, K)
    total = float(conf.sum())
    tp = np.diag(conf).astype(float)
    fp = conf.sum(axis=0).astype(float) - tp
    fn = conf.sum(axis=1).astype(float) - tp
    support = conf.sum(axis=1).astype(float)

    prec = np.where(tp + fp > 0, tp / np.maximum(tp + fp, 1e-9), 0.0)
    rec = np.where(support > 0, tp / np.maximum(support, 1e-9), 0.0)
    f1 = np.where(prec + rec > 0, 2 * prec * rec / np.maximum(prec + rec, 1e-9), 0.0)

    mask = support > 0
    acc = float(tp.sum() / max(total, 1e-9))
    macro_f1 = float(np.mean(f1[mask])) if mask.any() else 0.0
    weighted_f1 = float(np.sum(f1 * support) / max(total, 1e-9))

    p_o = acc
    p_e = float(np.sum(conf.sum(axis=1) * conf.sum(axis=0)) / max(total * total, 1e-9))
    kappa = float((p_o - p_e) / max(1.0 - p_e, 1e-9)) if p_e < 1.0 else 1.0

    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "cohen_kappa": round(kappa, 4),
        "confusion_matrix": conf,
        "label_rute": label,
    }

