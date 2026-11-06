"""SORA - Dashboard Mutu Umpan PLTSa Putri Cempo (DLH Kota Surakarta).

Tampilan dashboard dibangun sebagai halaman web statis di folder demo/web
(HTML, CSS, JavaScript dengan ECharts, Leaflet, dan SheetJS yang disimpan lokal).
Berkas ini hanya membungkus halaman itu sebagai komponen Streamlit supaya
bisa di-deploy di Streamlit Community Cloud tanpa mengubah alamat aplikasi.

Data yang tampil adalah data SIMULASI dari demo/sora_data.py, dengan rumus dan
ambang yang sama dengan aplikasi petugas SORA di HP. Data nyata dari HP bisa
dimasukkan lewat menu Laporan > Impor CSV dari aplikasi HP.

Jalankan:
    streamlit run demo/app_streamlit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

DEMO = Path(__file__).resolve().parent
WEB = DEMO / "web"
DATA = WEB / "data" / "sora_demo.json"

st.set_page_config(
    page_title="SORA · Dashboard Mutu Umpan PLTSa",
    page_icon=str(WEB / "img" / "logo.svg") if (WEB / "img" / "logo.svg").exists() else None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"],
      [data-testid="stSidebarCollapsedControl"], [data-testid="stDecoration"], footer,
      #MainMenu, .stDeployButton { display: none !important; }
      html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: #f3f5fa !important; overflow: hidden !important;
      }
      .block-container, [data-testid="stMainBlockContainer"] {
        padding: 0 !important; margin: 0 !important; max-width: 100% !important;
      }
      [data-testid="stVerticalBlock"] { gap: 0 !important; }
      iframe { display: block; border: 0; width: 100% !important; height: 100vh !important; height: 100dvh !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not DATA.exists():
    sys.path.insert(0, str(DEMO))
    from sora_data import tulis  # noqa: E402

    tulis(DATA)

sora = components.declare_component("sora", path=str(WEB))
sora(key="sora", default=None)
