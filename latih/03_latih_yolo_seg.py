"""Latih segmentasi YOLO-seg (backend "yolo"), tahap setelah ada anotasi poligon.

Anotasi: CVAT / Label Studio / Roboflow, ekspor format "YOLO segmentation".
Struktur:  data/yolo/images/{train,val}/*.jpg  dan  data/yolo/labels/{train,val}/*.txt
Pembagian train/val PER MUATAN (bukan per foto) jika satu muatan difoto beberapa kali.

  pip install ultralytics
  python latih/03_latih_yolo_seg.py --data data/yolo --epoch 100

Ekspor untuk perangkat tepi:
  Raspberry Pi 5 -> format ncnn (paling cepat di CPU ARM)
  Jetson Orin Nano -> format engine (TensorRT, FP16/INT8)

Lisensi: Ultralytics AGPL-3.0. Cukup untuk riset/hackathon; untuk produk
komersial tertutup perlu lisensi Enterprise atau ganti model (lihat visi.py).
Titik awal yang baik sebelum foto lokal: pralatih di dataset ZeroWaste atau
TACO (cek lisensi masing-masing), lalu fine-tune dengan foto Putri Cempo.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from karta.konstanta import FRAKSI  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", default="yolo11n-seg.pt")
    ap.add_argument("--epoch", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--ekspor", default="ncnn", help="ncnn | onnx | engine | none")
    a = ap.parse_args()
    from ultralytics import YOLO

    root = Path(a.data).resolve()
    yaml = root / "data.yaml"
    yaml.write_text(f"path: {root}\ntrain: images/train\nval: images/val\n"
                    + "names:\n" + "".join(f"  {i}: {k}\n" for i, k in enumerate(FRAKSI)))
    model = YOLO(a.model)
    model.train(data=str(yaml), epochs=a.epoch, imgsz=a.imgsz, seed=2026, deterministic=True,
                hsv_h=0.015, hsv_s=0.5, hsv_v=0.4, degrees=10, flipud=0.5, fliplr=0.5,
                mosaic=1.0, copy_paste=0.3, patience=25)
    m = model.val()
    print("mask mAP50-95:", m.seg.map, "| mask mAP50:", m.seg.map50)
    if a.ekspor != "none":
        model.export(format=a.ekspor, imgsz=a.imgsz)


if __name__ == "__main__":
    main()
