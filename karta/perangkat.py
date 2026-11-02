"""Perangkat keras demo: kamera, pemindai QR TPS, dan konveyor mini (Arduino + servo).

Protokol serial ke Arduino (115200 baud, satu baris per perintah):
  "JALAN <0-255>\n"  -> motor konveyor berputar dengan kecepatan PWM
  "STOP\n"           -> motor berhenti
  "RUTE U\n" / "RUTE B\n" / "RUTE M\n" / "RUTE R\n" -> servo pengalih ke posisi rute
Arduino membalas "OK ..." dan mengirim "BENDA\n" saat sensor IR melihat benda lewat.
"""
from __future__ import annotations

import time

import numpy as np


class Kamera:
    def __init__(self, indeks: int = 0, lebar: int = 1280, tinggi: int = 720):
        import cv2
        self.cap = cv2.VideoCapture(indeks)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, lebar)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, tinggi)
        # kunci eksposur & white balance agar warna stabil antarfoto (jika kamera mendukung)
        self.cap.set(cv2.CAP_PROP_AUTO_WB, 0)

    def ambil(self, buang: int = 3) -> np.ndarray:
        for _ in range(buang):          # buang beberapa frame lama di buffer
            self.cap.read()
        ok, frame = self.cap.read()
        if not ok:
            raise RuntimeError("Kamera tidak memberi gambar")
        return frame

    def tutup(self):
        self.cap.release()


def baca_qr(bgr: np.ndarray) -> str | None:
    """Baca QR TPS (isi contoh: 'TPS-07|Kel. Jebres'). Pakai OpenCV bawaan, tanpa paket tambahan."""
    import cv2
    teks, _, _ = cv2.QRCodeDetector().detectAndDecode(bgr)
    return teks or None


def buat_qr_tps(kode: str, nama: str, path: str):
    """Buat stiker QR untuk ditempel di kabin truk / papan TPS (butuh paket qrcode)."""
    import qrcode
    qrcode.make(f"{kode}|{nama}").save(path)


class Konveyor:
    """Pengendali konveyor mini lewat serial. mode_kering=True mencetak perintah
    tanpa Arduino, supaya aplikasi bisa diuji di laptop mana pun."""

    def __init__(self, port: str | None = None, mode_kering: bool = False):
        self.mode_kering = mode_kering or port is None
        if not self.mode_kering:
            import serial
            self.ser = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)  # Arduino reset saat port dibuka

    def _kirim(self, perintah: str) -> str:
        if self.mode_kering:
            print("[konveyor-simulasi]", perintah)
            return "OK (simulasi)"
        self.ser.write((perintah + "\n").encode())
        return self.ser.readline().decode(errors="ignore").strip()

    def jalan(self, kecepatan: int = 150):
        return self._kirim(f"JALAN {int(np.clip(kecepatan, 0, 255))}")

    def stop(self):
        return self._kirim("STOP")

    def arahkan(self, rute: str):
        assert rute in {"U", "B", "M", "R"}
        return self._kirim(f"RUTE {rute}")

    def tunggu_benda(self, batas_detik: float = 30) -> bool:
        """Tunggu sinyal sensor IR bahwa benda sampai di bawah kamera."""
        if self.mode_kering:
            return True
        t0 = time.time()
        while time.time() - t0 < batas_detik:
            if self.ser.readline().decode(errors="ignore").strip() == "BENDA":
                return True
        return False
