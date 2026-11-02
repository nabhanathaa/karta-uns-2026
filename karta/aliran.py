"""Pemrosesan aliran (video/kamera/konveyor): segmentasi tiap beberapa detik, lalu satu keputusan per jendela waktu.

Di konveyor, sampah terus bergerak. Satu keputusan rute dibuat untuk tiap jendela waktu (mis. 8 detik
= satu 'porsi' yang lewat), dari rata-rata proporsi fraksi semua frame di jendela itu.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .alur import BATAS_LEBAR_INTERVAL, rute_satu_muatan
from .kadar_air import ModelKadarAir, luas_ke_massa
from .konstanta import FRAKSI
from .optimasi import NAMA_RUTE
from .tampil import gambar_hasil
from .visi import HasilVisi, rata_rata_frame


class PemantauAliran:
    def __init__(self, model_air: ModelKadarAir, jendela_detik: float = 8.0, tps: str = "TPS-01",
                 hujan_24j: float = 0.0, hujan_72j: float = 0.0):
        self.model_air, self.jendela = model_air, jendela_detik
        self.tps, self.hujan = tps, (hujan_24j, hujan_72j)
        self.buf: list[HasilVisi] = []
        self.t0 = 0.0
        self.waktu: list[dict] = []
        self.keputusan: list[dict] = []
        self.terakhir: dict | None = None

    def tambah(self, t: float, hv: HasilVisi):
        self.waktu.append({"t": round(t, 2), **{f: hv.proporsi[f] for f in FRAKSI}, "keyakinan": hv.keyakinan})
        self.buf.append(hv)
        if t - self.t0 >= self.jendela:
            self._putuskan(t)

    def selesai(self, t: float):
        if self.buf:
            self._putuskan(t)

    def _putuskan(self, t: float):
        prop, sd = rata_rata_frame(self.buf)
        baris = pd.DataFrame([{**{f"luas_{f}": prop[f] for f in FRAKSI}, "hujan_24j": self.hujan[0], "hujan_72j": self.hujan[1]}])
        p = self.model_air.predict(baris).iloc[0]
        m = luas_ke_massa(baris[[f"luas_{f}" for f in FRAKSI]]).iloc[0]
        rute, alasan = rute_satu_muatan(p.w_hat, p.w_atas, m["massa_plastik"], m["massa_organik_basah"])
        lebar = float(p.w_atas - p.w_bawah)
        keyakinan = float(np.mean([h.keyakinan for h in self.buf]))
        self.terakhir = {
            "t_awal": round(self.t0, 1), "t_akhir": round(t, 1), "n_frame": len(self.buf),
            **{f"luas_{f}": round(prop[f], 4) for f in FRAKSI},
            "sd_antarframe_maks": round(max(sd.values()), 4),
            "kadar_air": round(float(p.w_hat), 3), "kadar_air_bawah": round(float(p.w_bawah), 3),
            "kadar_air_atas": round(float(p.w_atas), 3), "lhv_mj_kg": round(float(p.lhv_hat), 2),
            "rute": rute, "nama_rute": NAMA_RUTE[rute], "alasan": alasan,
            "perlu_cek_manual": bool(lebar > BATAS_LEBAR_INTERVAL),
        }
        self.keputusan.append(self.terakhir)
        self.buf, self.t0 = [], t

    def hud(self) -> list[str]:
        d = self.terakhir
        if d is None:
            return ["Mengumpulkan frame untuk keputusan pertama..."]
        baris = [f"Kadar air {d['kadar_air'] * 100:.0f}% (rentang {d['kadar_air_bawah'] * 100:.0f}-{d['kadar_air_atas'] * 100:.0f}%)  LHV {d['lhv_mj_kg']:.1f} MJ/kg",
                 f"RUTE {d['rute']}: {d['nama_rute']}"]
        if d["perlu_cek_manual"]:
            baris.append("PERLU CEK MANUAL (model ragu)")
        return baris

    def tabel(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        return pd.DataFrame(self.waktu), pd.DataFrame(self.keputusan)


def proses_video(path_in: str, path_out: str, model_visi, model_air: ModelKadarAir, *, tiap_detik: float = 1.0,
                 jendela_detik: float = 8.0, maks_detik: float | None = None, lebar_maks: int = 960,
                 tps: str = "TPS-01", hujan_24j: float = 0.0, hujan_72j: float = 0.0):
    """Baca video, segmentasi tiap `tiap_detik`, gambar hasil terakhir di setiap frame, tulis video keluaran.
    Mengembalikan (tabel_waktu, tabel_keputusan, path_out)."""
    import cv2
    cap = cv2.VideoCapture(path_in)
    if not cap.isOpened():
        raise RuntimeError(f"Tidak bisa membuka video: {path_in}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    mon = PemantauAliran(model_air, jendela_detik, tps, hujan_24j, hujan_72j)
    tulis, hv, t_proses, i, t = None, None, -1e9, 0, 0.0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = i / fps
        i += 1
        if maks_detik is not None and t > maks_detik:
            break
        if frame.shape[1] > lebar_maks:
            frame = cv2.resize(frame, (lebar_maks, int(frame.shape[0] * lebar_maks / frame.shape[1])))
        if t - t_proses >= tiap_detik:
            hv, t_proses = model_visi(frame), t
            mon.tambah(t, hv)
        if hv is None:
            continue
        out = gambar_hasil(frame, hv, hud=mon.hud() + [f"t = {t:5.1f} s"])
        if tulis is None:
            tulis = cv2.VideoWriter(path_out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (out.shape[1], out.shape[0]))
        tulis.write(out)
    cap.release()
    if tulis is not None:
        tulis.release()
    mon.selesai(t)
    return (*mon.tabel(), path_out)


def proses_deret_foto(frames: list[np.ndarray], jeda_detik: float, model_visi, model_air: ModelKadarAir, *,
                      jendela_detik: float = 8.0, tps: str = "TPS-01", hujan_24j: float = 0.0, hujan_72j: float = 0.0):
    """Untuk foto berurutan (mis. dari webcam tiap beberapa detik). Mengembalikan (gambar_hasil[], tabel_waktu, tabel_keputusan)."""
    mon = PemantauAliran(model_air, jendela_detik, tps, hujan_24j, hujan_72j)
    gambar = []
    for i, fr in enumerate(frames):
        hv = model_visi(fr)
        mon.tambah(i * jeda_detik, hv)
        gambar.append(gambar_hasil(fr, hv, hud=mon.hud() + [f"t = {i * jeda_detik:5.1f} s"]))
    mon.selesai(len(frames) * jeda_detik)
    return (gambar, *mon.tabel())
