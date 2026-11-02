"""Kamera laptop langsung: tampilkan segmentasi + keputusan secara real-time.

Jalankan di laptop (bukan Colab):
    pip install -r requirements.txt torch transformers
    python demo/kamera_langsung.py                       # webcam 0, mode zero-shot
    python demo/kamera_langsung.py --sumber video.mp4    # file video
    python demo/kamera_langsung.py --mode segformer --bobot hasil/segformer_karta

Tombol: q keluar | s simpan frame+CSV | + / - ubah ambang (zero-shot) | spasi jeda
Segmentasi dijalankan tiap --tiap detik (CLIPSeg lambat di CPU, 1-3 detik per proses); tampilan tetap mulus.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import cv2

from karta.aliran import PemantauAliran
from karta.kadar_air import ModelKadarAir
from karta.tampil import gambar_hasil
from karta.visi import muat_model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sumber", default="0", help="indeks kamera (0,1,...) atau path video")
    ap.add_argument("--mode", default="zero-shot", choices=["zero-shot", "segformer", "yolo", "petak", "demo"])
    ap.add_argument("--bobot", default=None)
    ap.add_argument("--tiap", type=float, default=2.0, help="detik antar segmentasi")
    ap.add_argument("--jendela", type=float, default=8.0, help="detik per keputusan rute")
    ap.add_argument("--lebar", type=int, default=960)
    ap.add_argument("--keluar", default="hasil_kamera")
    a = ap.parse_args()

    os.makedirs(a.keluar, exist_ok=True)
    sumber = int(a.sumber) if a.sumber.isdigit() else a.sumber
    cap = cv2.VideoCapture(sumber)
    if not cap.isOpened():
        sys.exit(f"Tidak bisa membuka sumber: {a.sumber}")
    model = muat_model(a.mode, a.bobot)
    mon = PemantauAliran(ModelKadarAir("fisika"), a.jendela)
    hv, t_proses, t0, jeda, n = None, -1e9, time.time(), False, 0
    frame = None
    while True:
        if not jeda:
            ok, frame = cap.read()
            if not ok:
                break
            if frame.shape[1] > a.lebar:
                frame = cv2.resize(frame, (a.lebar, int(frame.shape[0] * a.lebar / frame.shape[1])))
        t = time.time() - t0
        if frame is not None and not jeda and t - t_proses >= a.tiap:
            hv, t_proses = model(frame), t
            mon.tambah(t, hv)
        if hv is not None:
            tampil = gambar_hasil(frame, hv, hud=mon.hud() + [f"t = {t:5.1f} s   [q keluar, s simpan]"])
        else:
            tampil = frame
        cv2.imshow("KARTA - segmentasi langsung", tampil)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        if k == ord(" "):
            jeda = not jeda
        if k in (ord("+"), ord("=")) and hasattr(model, "ambang"):
            model.ambang = min(0.9, model.ambang + 0.05); print("ambang", round(model.ambang, 2))
        if k == ord("-") and hasattr(model, "ambang"):
            model.ambang = max(0.05, model.ambang - 0.05); print("ambang", round(model.ambang, 2))
        if k == ord("s") and hv is not None:
            n += 1
            cv2.imwrite(os.path.join(a.keluar, f"frame_{n:03d}.jpg"), tampil)
            print("tersimpan", n)
    cap.release()
    cv2.destroyAllWindows()
    mon.selesai(time.time() - t0)
    tw, tk = mon.tabel()
    tw.to_csv(os.path.join(a.keluar, "komposisi_per_waktu.csv"), index=False)
    tk.to_csv(os.path.join(a.keluar, "keputusan_per_jendela.csv"), index=False)
    print(f"Selesai. Hasil di {a.keluar}/")


if __name__ == "__main__":
    main()
