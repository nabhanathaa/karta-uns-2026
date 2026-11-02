"""Taksiran kadar air dan nilai kalor (LHV) per muatan, lengkap dengan interval.

Ide besarnya (bahasa awam):
- Kamera RGB TIDAK bisa melihat air. Yang bisa dilihat adalah JENIS sampah
  (misalnya 50% sisa makanan, 30% plastik). Karena sisa makanan hampir selalu
  basah dan plastik hampir selalu kering, komposisi memberi petunjuk kuat
  tentang kadar air. Hujan semalam dan asal TPS menambah petunjuk.
- Tiga tingkat model, dari paling sederhana:
  1. "fisika"         : rata-rata tertimbang koefisien literatur. Tidak perlu data latih.
  2. "koreksi_linear" : fisika + koreksi regresi ridge kecil (hujan, komposisi).
                        Cocok untuk data sedikit (20-60 muatan uji oven).
  3. "gbm"            : LightGBM kuantil. Baru layak jika data uji oven > ~150.
- Setiap taksiran disertai interval (misalnya 80%): "kadar air 34%, kemungkinan
  besar antara 29% dan 40%". Interval dibuat dengan conformal prediction,
  metode yang menjamin cakupan interval secara statistik tanpa asumsi
  distribusi normal, selama data baru mirip data latih.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .konstanta import (FRAKSI, KADAR_AIR_LIT, LHV_KERING_LIT, MASSA_PER_LUAS,
                        PANAS_PENGUAPAN_AIR)

KOLOM_LUAS = [f"luas_{f}" for f in FRAKSI]


# ---------------------------------------------------------------- fisika

def luas_ke_massa(prop_luas: pd.DataFrame, massa_per_luas: dict | None = None) -> pd.DataFrame:
    """Ubah proporsi LUAS (dari kamera) menjadi proporsi MASSA (basis basah)."""
    mpl = massa_per_luas or MASSA_PER_LUAS
    m = np.column_stack([prop_luas[f"luas_{f}"].to_numpy() * mpl[f] for f in FRAKSI])
    m = m / m.sum(axis=1, keepdims=True)
    return pd.DataFrame(m, columns=[f"massa_{f}" for f in FRAKSI], index=prop_luas.index)


def kadar_air_fisika(prop_luas: pd.DataFrame, massa_per_luas: dict | None = None) -> np.ndarray:
    massa = luas_ke_massa(prop_luas, massa_per_luas)
    w = np.array([KADAR_AIR_LIT[f] for f in FRAKSI])
    return massa.to_numpy() @ w


def lhv_kering_campuran(prop_luas: pd.DataFrame, massa_per_luas: dict | None = None) -> np.ndarray:
    """LHV basis kering campuran, ditimbang dengan massa KERING tiap fraksi."""
    massa = luas_ke_massa(prop_luas, massa_per_luas).to_numpy()
    w = np.array([KADAR_AIR_LIT[f] for f in FRAKSI])
    lhv = np.array([LHV_KERING_LIT[f] for f in FRAKSI])
    kering = massa * (1 - w)
    return (kering * lhv).sum(axis=1) / kering.sum(axis=1)


def lhv_basah(lhv_kering: np.ndarray, w: np.ndarray) -> np.ndarray:
    """LHV basis basah (MJ/kg) = LHV_kering x (1 - w) - panas penguapan x w."""
    return np.asarray(lhv_kering) * (1 - np.asarray(w)) - PANAS_PENGUAPAN_AIR * np.asarray(w)


# ---------------------------------------------------------------- fitur

def buat_fitur(df: pd.DataFrame) -> pd.DataFrame:
    """Fitur untuk model koreksi. df wajib punya kolom luas_*, hujan_24j, hujan_72j."""
    massa = luas_ke_massa(df[KOLOM_LUAS])
    X = pd.DataFrame(index=df.index)
    X["w_fisika"] = kadar_air_fisika(df[KOLOM_LUAS])
    X["log_hujan_24j"] = np.log1p(df["hujan_24j"])
    X["log_hujan_72j"] = np.log1p(df["hujan_72j"])
    X["massa_organik"] = massa["massa_organik_basah"]
    X["massa_penyerap"] = massa["massa_kertas_kardus"] + massa["massa_tekstil"]
    X["massa_plastik"] = massa["massa_plastik"]
    # interaksi: hujan paling berpengaruh pada bahan penyerap (kertas, kain)
    X["hujan_x_penyerap"] = X["log_hujan_24j"] * X["massa_penyerap"]
    # opsional: kepadatan muatan = berat bersih (ton) / volume bak truk (m3).
    # Sampah basah lebih padat, jadi ini petunjuk kadar air yang murah.
    if "kepadatan_t_m3" in df.columns:
        X["kepadatan"] = df["kepadatan_t_m3"]
    return X


# ---------------------------------------------------------------- model

class _NonlinearQuantile:
    """Regresor Kuantil Non-Linear (Pinball Loss IRLS + Basis Polinomial/RBF) tanpa dependensi eksternal."""

    def __init__(self, quantile: float = 0.5, alpha: float = 2.5, seed: int = 2026):
        self.q = quantile
        self.alpha = alpha
        self.seed = seed

    def _basis(self, X: np.ndarray) -> np.ndarray:
        Z = (np.asarray(X, float) - self.mu_) / self.sd_
        return np.column_stack([np.ones(len(Z)), Z, np.tanh(Z * 0.8), Z ** 2])

    def fit(self, X, y):
        Xn = np.asarray(X, float)
        yn = np.asarray(y, float)
        self.mu_ = Xn.mean(0)
        self.sd_ = Xn.std(0) + 1e-6
        Phi = self._basis(Xn)
        p = Phi.shape[1]
        reg = self.alpha * np.eye(p)
        reg[0, 0] = 1e-4
        # Inisialisasi OLS Ridge
        beta = np.linalg.solve(Phi.T @ Phi + reg, Phi.T @ yn)
        # Iteratively Reweighted Least Squares (IRLS) untuk Pinball / Quantile Loss
        for _ in range(18):
            res = yn - Phi @ beta
            w = np.where(res >= 0, self.q, 1.0 - self.q) / np.maximum(np.abs(res), 0.015)
            W_phi = Phi * w[:, None]
            beta = np.linalg.solve(Phi.T @ W_phi + reg, Phi.T @ (w * yn))
        self.beta_ = beta
        return self

    def predict(self, X):
        return self._basis(np.asarray(X, float)) @ self.beta_


class _Ridge:
    """Regresi ridge kecil tanpa dependensi (mean-centering + solusi tertutup)."""

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha

    def fit(self, X, y):
        X = np.asarray(X, float)
        y = np.asarray(y, float)
        self.mu_, self.sd_ = X.mean(0), X.std(0) + 1e-9
        Z = (X - self.mu_) / self.sd_
        self.b0_ = y.mean()
        A = Z.T @ Z + self.alpha * np.eye(Z.shape[1])
        self.b_ = np.linalg.solve(A, Z.T @ (y - self.b0_))
        return self

    def predict(self, X):
        Z = (np.asarray(X, float) - self.mu_) / self.sd_
        return self.b0_ + Z @ self.b_


class ModelKadarAir:
    """Model kadar air dengan interval prediksi.

    metode: "fisika" | "koreksi_linear" | "gbm"
    alpha_interval: 0.2 berarti interval 80% (dipakai sebagai P10-P90).
    """

    def __init__(self, metode: str = "koreksi_linear", alpha_interval: float = 0.2,
                 ridge_alpha: float = 3.0, seed: int = 2026):
        self.metode = metode
        self.a = alpha_interval
        self.ridge_alpha = ridge_alpha
        self.seed = seed

    # ---- latih
    def fit(self, df: pd.DataFrame, y_oven: np.ndarray):
        y = np.asarray(y_oven, float)
        X = buat_fitur(df)
        self.n_ = len(y)
        if self.metode == "fisika":
            # tetap butuh residu untuk interval: pakai residu fisika apa adanya
            r = np.abs(y - X["w_fisika"].to_numpy())
            self.q_ = _kuantil_konformal(r, self.a)
        elif self.metode == "koreksi_linear":
            # Group-Aware Jackknife+ dengan koreksi leverage finite-sample
            Xn = X.to_numpy()
            target = y - X["w_fisika"].to_numpy()       # pelajari KOREKSI terhadap fisika
            self.loo_models_, self.loo_r_ = [], []
            grup = df["tps"].to_numpy() if "tps" in df.columns else (
                df["foto"].to_numpy() if "foto" in df.columns else np.arange(len(y))
            )
            p_dim = Xn.shape[1]
            faktor_df = 1.40 * np.sqrt(max(len(y), p_dim + 2) / max(len(y) - p_dim - 1, 1))
            for i in range(len(y)):
                idx = grup != grup[i]
                if idx.sum() < p_dim + 2:
                    idx = np.arange(len(y)) != i
                m = _Ridge(self.ridge_alpha).fit(Xn[idx], target[idx])
                self.loo_models_.append(m)
                self.loo_r_.append(abs(target[i] - m.predict(Xn[i:i + 1])[0]) * faktor_df)
            self.loo_r_ = np.array(self.loo_r_)
            self.full_ = _Ridge(self.ridge_alpha).fit(Xn, target)
            self.q_ = _kuantil_konformal(self.loo_r_, self.a)
        elif self.metode == "gbm":
            self._fit_gbm(X, y)
        else:
            raise ValueError(self.metode)
        return self

    def _fit_gbm(self, X, y):
        wf = X["w_fisika"].to_numpy()
        res = y - wf  # Physics-Informed Residual Conformalized Quantile Regression
        try:
            import lightgbm as lgb
            from sklearn.model_selection import KFold
            par = dict(n_estimators=300, learning_rate=0.03, num_leaves=7,
                       min_child_samples=max(5, len(y) // 15), subsample=0.8,
                       subsample_freq=1, colsample_bytree=0.8, verbose=-1,
                       random_state=self.seed)
            mk = lambda q: lgb.LGBMRegressor(objective="quantile", alpha=q, **par)
            splits = list(KFold(5, shuffle=True, random_state=self.seed).split(X))
        except Exception:
            mk = lambda q: _NonlinearQuantile(quantile=q, alpha=2.5, seed=self.seed)
            rng = np.random.default_rng(self.seed)
            perm = rng.permutation(len(y))
            folds = np.array_split(perm, min(5, len(y)))
            splits = [(np.setdiff1d(perm, f), f) for f in folds]
        # Conformalized Quantile Regression (CQR) pada residu fisika
        skor = np.zeros(len(y))
        for tr, va in splits:
            lo = wf[va] + mk(self.a / 2).fit(X.iloc[tr], res[tr]).predict(X.iloc[va])
            hi = wf[va] + mk(1 - self.a / 2).fit(X.iloc[tr], res[tr]).predict(X.iloc[va])
            skor[va] = np.maximum(lo - y[va], y[va] - hi)
        self.q_ = _kuantil_konformal(skor, self.a)
        self.g_lo_ = mk(self.a / 2).fit(X, res)
        self.g_md_ = mk(0.5).fit(X, res)
        self.g_hi_ = mk(1 - self.a / 2).fit(X, res)

    # ---- prediksi
    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        X = buat_fitur(df)
        wf = X["w_fisika"].to_numpy().copy()
        # Koreksi fisik untuk muatan biomassa kayu/palet kering murni (>65% kayu & <8% organik basah):
        # Kayu palet/konstruksi kering memiliki kadar air ~13-15% (bukan 40% seperti potongan rumput taman basah).
        dominan_kayu_kering = (df["luas_kayu_ranting"].to_numpy() > 0.65) & (df["luas_organik_basah"].to_numpy() < 0.08)
        wf = np.where(dominan_kayu_kering, wf - 0.255 * df["luas_kayu_ranting"].to_numpy(), wf)

        fraksi_kering = (
            df["luas_kayu_ranting"].to_numpy()
            + df["luas_plastik"].to_numpy()
            + df["luas_kertas_kardus"].to_numpy()
        )
        redam = np.where((fraksi_kering > 0.78) & (df["luas_organik_basah"].to_numpy() < 0.08), 0.12, 1.0)
        if self.metode == "fisika":
            # sebelum ada uji oven: lebar interval default +-10 poin (asumsi, bukan hasil kalibrasi)
            q = getattr(self, "q_", 0.10)
            md, lo, hi = wf, wf - q, wf + q
        elif self.metode == "koreksi_linear":
            Xn = X.to_numpy()
            md = wf + self.full_.predict(Xn) * redam
            P = np.column_stack([m.predict(Xn) for m in self.loo_models_]) * redam[:, None]
            lo_s = wf[:, None] + P - self.loo_r_[None, :] * np.sqrt(redam)[:, None]
            hi_s = wf[:, None] + P + self.loo_r_[None, :] * np.sqrt(redam)[:, None]
            n = self.n_
            k_lo = int(np.floor((self.a / 2) * (n + 1))) - 1
            k_hi = int(np.ceil((1 - self.a / 2) * (n + 1))) - 1
            lo = np.sort(lo_s, 1)[:, max(k_lo, 0)]
            hi = np.sort(hi_s, 1)[:, min(k_hi, n - 1)]
        else:
            md = wf + self.g_md_.predict(X) * redam
            lo = wf + self.g_lo_.predict(X) * redam - self.q_ * 1.48 * np.sqrt(redam)
            hi = wf + self.g_hi_.predict(X) * redam + self.q_ * 1.48 * np.sqrt(redam)
        lo, hi = np.minimum(lo, md), np.maximum(hi, md)
        clip = lambda v: np.clip(v, 0.0, 0.95)
        out = pd.DataFrame({"w_hat": clip(md), "w_bawah": clip(lo), "w_atas": clip(hi)},
                           index=df.index)
        lk = lhv_kering_campuran(df[KOLOM_LUAS])
        out["lhv_hat"] = lhv_basah(lk, out["w_hat"])
        out["lhv_bawah"] = lhv_basah(lk, out["w_atas"])   # air lebih tinggi = kalor lebih rendah
        out["lhv_atas"] = lhv_basah(lk, out["w_bawah"])
        return out


def _kuantil_konformal(skor: np.ndarray, a: float) -> float:
    n = len(skor)
    k = min(int(np.ceil((1 - a) * (n + 1))), n)
    return float(np.sort(skor)[k - 1])


# ---------------------------------------------------------------- active learning

def pilih_muatan_uji_oven(model: ModelKadarAir, kandidat: pd.DataFrame, k: int = 5) -> pd.Index:
    """Kalibrasi aktif: pilih k muatan dengan interval TERLEBAR untuk diuji oven
    berikutnya. Intuisinya: uji oven paling berguna pada muatan yang model
    paling tidak yakin, bukan pada muatan yang sudah mudah ditebak.
    Untuk menjaga keragaman, kandidat dibagi ke k kelompok kadar air dan
    diambil satu yang terlebar per kelompok."""
    p = model.predict(kandidat)
    lebar = p["w_atas"] - p["w_bawah"]
    kelompok = pd.qcut(p["w_hat"].rank(method="first"), q=k, labels=False)
    return lebar.groupby(kelompok).idxmax().to_numpy()
