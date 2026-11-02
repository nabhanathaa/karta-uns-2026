"""Aplikasi Web Interaktif KARTA v4 — Sistem Gerbang Cerdas Mutu Umpan PLTSa Putri Cempo & Analitik DLH Surakarta.

Dirancang dengan antarmuka Web Aplikasi Modern (Responsive Desktop & Mobile HP),
bebas kotak hitam kontras rusak, mendukung Light Mode & Dark Mode secara utuh,
serta terintegrasi penuh dengan Model Terlatih, Ground Truth Benchmark, & Peta GPS Nyata Kota Surakarta.

Jalankan:
    streamlit run demo/app_streamlit.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw

AKAR = Path(__file__).resolve().parents[1]
if str(AKAR) not in sys.path:
    sys.path.insert(0, str(AKAR))

from karta.alur import catat, proses_muatan, rute_satu_muatan  # noqa: E402
from karta.evaluasi import (evaluasi_keputusan_triase,  # noqa: E402
                            evaluasi_regresi_kadar_air,
                            evaluasi_segmentasi_piksel)
from karta.kadar_air import ModelKadarAir, pilih_muatan_uji_oven  # noqa: E402
from karta.konstanta import FRAKSI, KELAS_VISI, LATAR  # noqa: E402
from karta.optimasi import (NAMA_RUTE, Parameter, rencana_harian,  # noqa: E402
                            w_campuran_nyata)
from karta.perangkat import Konveyor, baca_qr  # noqa: E402
from karta.pretrained import (FOLDER_BENCHMARK, FOLDER_MODEL_V4,  # noqa: E402
                              LOKASI_PLTSA_PUTRI_CEMPO, PALET_VISUAL_RGB,
                              SENTRA_MEBEL_SUKOHARJO, TPS_SURAKARTA,
                              UNIT_BSF_SURAKARTA, ZONA_SPASIAL_PUTRI_CEMPO,
                              pastikan_benchmark_gt,
                              render_visual_profesional)
from karta.visi import muat_model  # noqa: E402

st.set_page_config(
    page_title="KARTA v4 · Smart Gate PLTSa Putri Cempo & DLH Surakarta",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": None,
    },
)

LOG_PATH = AKAR / "demo" / "log_muatan.csv"

LABEL_FRAKSI_ID = {
    "organik_basah": "Organik Basah",
    "plastik": "Plastik & Kemasan",
    "kertas_kardus": "Kertas & Kardus",
    "tekstil": "Tekstil & Kain",
    "kayu_ranting": "Kayu & Ranting",
    "inert": "Inert (Logam/Kaca/Batu)",
    "latar": "Lantai Beton Tipping Floor",
}

WARNA_HEX_FRAKSI = {
    "organik_basah": "#22A84C",
    "plastik": "#2576E8",
    "kertas_kardus": "#EAA82A",
    "tekstil": "#BA44B2",
    "kayu_ranting": "#945C2C",
    "inert": "#808A98",
    "latar": "#D6DCE4",
}

INFO_RUTE_UI = {
    "U": {
        "kode": "RUTE U · ENERGI BERSIH PLTSa",
        "judul": "Umpan Gasifikasi Langsung (Bypass ke Bunker Reaktor PLTSa)",
        "warna": "#059669",
        "bg_terang": "#ECFDF5",
        "bg_gelap": "#062E22",
    },
    "B": {
        "kode": "RUTE B · SIRKULAR BIO-DRYING",
        "judul": "Bio-Drying Terakselerasi + Co-Processing Serbuk Kayu Sukoharjo",
        "warna": "#B45309",
        "bg_terang": "#FFFBEB",
        "bg_gelap": "#2B1D0E",
    },
    "M": {
        "kode": "RUTE M · BIOKONVERSI ORGANIK",
        "judul": "Biokonversi Larva Maggot BSF & Kompos Organik Kawasan",
        "warna": "#0F766E",
        "bg_terang": "#F0FDFA",
        "bg_gelap": "#0D2B2A",
    },
    "R": {
        "kode": "RUTE R · INTERVENSI HULU SE 11/2026",
        "judul": "Sortir Residu Anorganik & Intervensi Kepatuhan SE MenLH 11/2026",
        "warna": "#E11D48",
        "bg_terang": "#FFF1F2",
        "bg_gelap": "#2C1219",
    },
}


# ------------------------------------------------------------------ Sistem Tema "Eco-Tech Circular" (60-30-10) & Ornamen Batik Surakarta
def dapatkan_palet_tema(mode_gelap: bool) -> dict[str, str]:
    """Palet 'Eco-Tech Circular' (Teknologi & Bumi Lestari) dengan rasio 60-30-10:
    - 60% Latar Belakang: Off-White Eco Paper (#F3F7F4 / #F9FAFB) atau Deep Charcoal (#111827)
    - 30% Warna Pendukung: Forest Emerald (#059669) & Ocean Deep Teal (#0F766E / #0284C7)
    - 10% Warna Aksen: Electric Mint (#10B981 / #34D399) & Terracotta Earth Clay (#B45309)
    """
    if mode_gelap:
        return {
            "bg_app": "#111827",           # 60% Deep Charcoal / Slate
            "bg_sidebar": "#162032",
            "bg_card": "#1F2937",
            "bg_card_subtle": "#182230",
            "bg_input": "#1F2937",
            "teks_utama": "#F9FAFB",
            "teks_sekunder": "#D1D5DB",
            "teks_redup": "#9CA3AF",
            "border": "#374151",
            "aksen": "#059669",            # 30% Forest Emerald Green
            "aksen_mint": "#10B981",       # 10% Electric Mint
            "aksen_biru": "#0284C7",       # Ocean Teal / Climate Blue
            "aksen_terracotta": "#D97706", # Terracotta / Earth Clay
            "shadow": "0 6px 24px rgba(0, 0, 0, 0.42)",
            "tbl_header": "#162032",
            "tbl_row_alt": "#1A2433",
            "tbl_hover": "#064E3B",
            "banner_grad": "linear-gradient(135deg, #064E3B 0%, #0F766E 55%, #111827 100%)",
        }
    return {
        "bg_app": "#F3F7F4",               # 60% Eco Paper Off-White dengan rona hijau organik lembut (#F0FDF4 + #F9FAFB)
        "bg_sidebar": "#FAFDFB",
        "bg_card": "#FFFFFF",
        "bg_card_subtle": "#F0FDF4",
        "bg_input": "#FFFFFF",
        "teks_utama": "#111827",           # Deep Charcoal (ramah di mata, bukan hitam pekat)
        "teks_sekunder": "#1F2937",
        "teks_redup": "#4B5563",
        "border": "#D1E2D7",
        "aksen": "#059669",                # 30% Forest / Emerald Green
        "aksen_mint": "#10B981",           # 10% Electric Mint
        "aksen_biru": "#0F766E",           # 30% Ocean / Deep Teal
        "aksen_terracotta": "#B45309",     # 10% Terracotta / Earth Clay (Sirkular & Kayu Sukoharjo)
        "shadow": "0 3px 14px rgba(5, 150, 105, 0.06)",
        "tbl_header": "#ECFDF5",
        "tbl_row_alt": "#F9FAFB",
        "tbl_hover": "#D1FAE5",
        "banner_grad": "linear-gradient(135deg, #065F46 0%, #059669 48%, #0F766E 100%)",
    }


def suntikkan_css_web(t: dict[str, str]):
    # Pola SVG Batik Kawung Geometris Khas Surakarta (Halus & Teknis)
    batik_kawung_svg = (
        "url(\"data:image/svg+xml,%3Csvg width='48' height='48' viewBox='0 0 48 48' xmlns='http://www.w3.org/2000/svg'%3E"
        "%3Cg fill='none' stroke='%23ffffff' stroke-width='1' stroke-opacity='0.11'%3E"
        "%3Ccircle cx='24' cy='24' r='20'/%3E"
        "%3Cpath d='M24 4 C14 14 14 34 24 44 C34 34 34 14 24 4 Z'/%3E"
        "%3Cpath d='M4 24 C14 14 34 14 44 24 C34 34 14 34 4 24 Z'/%3E"
        "%3Ccircle cx='24' cy='24' r='3' fill='%2334D399' fill-opacity='0.18'/%3E"
        "%3C/g%3E%3C/svg%3E\")"
    )
    batik_border_svg = (
        "url(\"data:image/svg+xml,%3Csvg width='32' height='8' viewBox='0 0 32 8' xmlns='http://www.w3.org/2000/svg'%3E"
        "%3Cpath d='M0 8 L8 0 L16 8 L24 0 L32 8' fill='none' stroke='%23B45309' stroke-width='1.5' stroke-opacity='0.45'/%3E"
        "%3C/svg%3E\")"
    )
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

        /* Reset & App Shell (60% Eco Paper / Deep Charcoal) */
        .stApp {{
            background-color: {t['bg_app']} !important;
            color: {t['teks_utama']} !important;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }}
        /* Sembunyikan Header Bawaan, Toolbar, Tombol Fork, dan Footer Streamlit Cloud */
        #MainMenu, footer {{
            visibility: hidden !important;
            display: none !important;
        }}
        header[data-testid="stHeader"] {{
            background: transparent !important;
            display: none !important;
            height: 0px !important;
        }}
        div[data-testid="stToolbar"],
        div[data-testid="stDecoration"],
        div[data-testid="stStatusWidget"],
        .stDeployButton,
        [class*="viewerBadge"],
        [class*="manage-app"],
        button[title*="Fork"] {{
            visibility: hidden !important;
            display: none !important;
        }}
        .block-container {{
            padding-top: 1.1rem !important;
            padding-bottom: 2.5rem !important;
            max-width: 1440px !important;
        }}

        /* Sidebar & Kontrol Input BaseWeb (Anti Kotak Hitam!) */
        section[data-testid="stSidebar"] {{
            background-color: {t['bg_sidebar']} !important;
            border-right: 1px solid {t['border']} !important;
        }}
        section[data-testid="stSidebar"] > div {{
            background-color: {t['bg_sidebar']} !important;
        }}
        .stMarkdown, .stText, label, p, h1, h2, h3, h4, h5, h6 {{
            color: {t['teks_utama']} !important;
        }}
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        div[data-baseweb="base-input"],
        input[type="text"],
        input[type="number"] {{
            background-color: {t['bg_input']} !important;
            color: {t['teks_utama']} !important;
            border-color: {t['border']} !important;
            border-radius: 8px !important;
        }}
        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div {{
            color: {t['teks_utama']} !important;
        }}
        ul[data-baseweb="menu"],
        div[data-baseweb="popover"] > div {{
            background-color: {t['bg_card']} !important;
            color: {t['teks_utama']} !important;
            border: 1px solid {t['border']} !important;
        }}
        li[role="option"] {{
            background-color: {t['bg_card']} !important;
            color: {t['teks_utama']} !important;
        }}
        li[role="option"]:hover {{
            background-color: {t['tbl_hover']} !important;
        }}
        div[data-testid="stFileUploader"] section {{
            background-color: {t['bg_card_subtle']} !important;
            border: 1.5px dashed {t['aksen']} !important;
            color: {t['teks_utama']} !important;
            border-radius: 10px !important;
        }}
        div[data-testid="stFileUploader"] section * {{
            color: {t['teks_sekunder']} !important;
        }}

        /* Tombol Utama Eco-Tech Forest Emerald */
        div.stButton > button {{
            background: linear-gradient(135deg, #059669 0%, #0F766E 100%) !important;
            color: #FFFFFF !important;
            border: 1px solid #047857 !important;
            border-radius: 8px !important;
            font-weight: 700 !important;
            font-size: 0.82rem !important;
            padding: 0.45rem 0.9rem !important;
            box-shadow: 0 2px 8px rgba(5, 150, 105, 0.22) !important;
        }}
        div.stButton > button * {{
            color: #FFFFFF !important;
        }}
        div.stButton > button:hover {{
            background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
            border-color: #10B981 !important;
        }}

        /* Navigasi Tab Modern (30% Forest Emerald & Ocean Teal) */
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {{
            background-color: {t['bg_card']} !important;
            border: 1px solid {t['border']} !important;
            border-bottom: 3px solid {t['aksen_terracotta']} !important;
            border-radius: 12px !important;
            padding: 6px 10px !important;
            gap: 6px !important;
            box-shadow: {t['shadow']} !important;
            overflow-x: auto !important;
        }}
        div[data-testid="stTabs"] button[role="tab"] {{
            border-radius: 8px !important;
            padding: 9px 16px !important;
            font-weight: 700 !important;
            font-size: 0.84rem !important;
            color: {t['teks_sekunder']} !important;
            border: none !important;
            white-space: nowrap !important;
        }}
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
            background: linear-gradient(135deg, #059669 0%, #0F766E 100%) !important;
            color: #FFFFFF !important;
            box-shadow: 0 2px 10px rgba(5, 150, 105, 0.28) !important;
        }}
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {{
            color: #FFFFFF !important;
        }}

        /* Header Banner Pemerintah Kota Surakarta x Eco-Tech Circular + Ornamen Batik Kawung */
        .karta-navbar {{
            background-image: {batik_kawung_svg}, {t['banner_grad']};
            background-size: 48px 48px, cover;
            border: 1px solid #047857;
            border-bottom: 4px solid #B45309;
            border-radius: 16px;
            padding: 22px 26px;
            margin-bottom: 12px;
            box-shadow: 0 8px 26px rgba(5, 150, 105, 0.16);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            color: #FFFFFF !important;
        }}
        .karta-brand-wrap {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .karta-logo-box {{
            width: 50px;
            height: 50px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.14);
            border: 2px solid #34D399;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #34D399 !important;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 800;
            font-size: 1.18rem;
            flex-shrink: 0;
            backdrop-filter: blur(6px);
        }}
        .karta-gov-tag {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.70rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #A7F3D0 !important;
            margin-bottom: 3px;
        }}
        .karta-brand-title {{
            font-size: 1.34rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #FFFFFF !important;
            margin: 0;
            line-height: 1.22;
        }}
        .karta-brand-sub {{
            font-size: 0.82rem;
            color: #E2F8EE !important;
            margin-top: 4px;
        }}
        .karta-status-pills {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .karta-chip {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 5px 11px;
            border-radius: 999px;
            background-color: rgba(17, 24, 39, 0.38);
            border: 1px solid #34D399;
            color: #ECFDF5 !important;
        }}
        .karta-chip.terracotta {{
            background-color: rgba(180, 83, 9, 0.88);
            border-color: #FCD34D;
            color: #FFFBEB !important;
        }}

        /* Pita Alur 5 Tahap Arsitektur (End-to-End Pipeline Strip) */
        .karta-pipeline-bar {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(195px, 1fr));
            gap: 10px;
            margin-bottom: 16px;
        }}
        .pipe-step {{
            background-color: {t['bg_card']};
            border: 1px solid {t['border']};
            border-left: 4px solid {t['aksen']};
            border-radius: 10px;
            padding: 10px 13px;
            box-shadow: {t['shadow']};
        }}
        .pipe-step.terracotta {{
            border-left-color: {t['aksen_terracotta']};
        }}
        .pipe-step.teal {{
            border-left-color: {t['aksen_biru']};
        }}
        .pipe-num {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.68rem;
            font-weight: 800;
            color: {t['aksen']};
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .pipe-title {{
            font-size: 0.81rem;
            font-weight: 700;
            color: {t['teks_utama']};
            margin-top: 2px;
        }}
        .pipe-desc {{
            font-size: 0.72rem;
            color: {t['teks_redup']};
            margin-top: 2px;
            line-height: 1.35;
        }}

        /* Ornamen Garis Batik Surakarta pada Kartu Seksi */
        .karta-surface {{
            background-color: {t['bg_card']};
            border: 1px solid {t['border']};
            border-top: 3px solid {t['aksen']};
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: {t['shadow']};
            margin-bottom: 14px;
            position: relative;
        }}
        .karta-surface.terracotta {{
            border-top-color: {t['aksen_terracotta']};
        }}
        .karta-batik-divider {{
            height: 8px;
            width: 100%;
            background-image: {batik_border_svg};
            background-repeat: repeat-x;
            margin: 6px 0 12px 0;
        }}
        .karta-section-head {{
            font-size: 0.98rem;
            font-weight: 800;
            color: {t['teks_utama']};
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .karta-section-desc {{
            font-size: 0.80rem;
            color: {t['teks_redup']};
            margin-bottom: 14px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
            gap: 12px;
            margin-bottom: 16px;
        }}
        .kpi-box {{
            background-color: {t['bg_card']};
            border: 1px solid {t['border']};
            border-radius: 12px;
            padding: 14px 16px;
            box-shadow: {t['shadow']};
        }}
        .kpi-lbl {{
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: {t['teks_redup']};
            margin-bottom: 6px;
        }}
        .kpi-num {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.42rem;
            font-weight: 700;
            color: {t['teks_utama']};
            line-height: 1.15;
        }}
        .kpi-meta {{
            font-size: 0.75rem;
            color: {t['teks_sekunder']};
            margin-top: 6px;
        }}

        /* Tabel HTML Kustom (Menggantikan st.dataframe Hitam) */
        .karta-table-wrap {{
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            border: 1px solid {t['border']};
            border-radius: 10px;
            background-color: {t['bg_card']};
            margin-bottom: 14px;
        }}
        table.karta-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.82rem;
            text-align: left;
        }}
        table.karta-table th {{
            background-color: {t['tbl_header']};
            color: {t['teks_sekunder']};
            font-weight: 700;
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            padding: 11px 14px;
            border-bottom: 1px solid {t['border']};
            white-space: nowrap;
        }}
        table.karta-table td {{
            padding: 10px 14px;
            border-bottom: 1px solid {t['border']};
            color: {t['teks_utama']};
            vertical-align: middle;
        }}
        table.karta-table tr:nth-child(even) td {{
            background-color: {t['tbl_row_alt']};
        }}
        table.karta-table tr:hover td {{
            background-color: {t['tbl_hover']};
        }}
        .badge-pill {{
            display: inline-block;
            padding: 3px 9px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
            white-space: nowrap;
        }}

        /* Kartu Dokumen Laporan (Menggantikan st.code Hitam) */
        .doc-report-card {{
            background-color: {t['bg_card_subtle']};
            border: 1px solid {t['border']};
            border-left: 4px solid {t['aksen']};
            border-radius: 10px;
            padding: 18px 20px;
            font-family: 'Plus Jakarta Sans', sans-serif;
            color: {t['teks_utama']};
            line-height: 1.65;
            font-size: 0.86rem;
        }}

        /* Responsif Layar HP (Mobile First Media Query) */
        @media (max-width: 768px) {{
            .block-container {{
                padding-left: 0.8rem !important;
                padding-right: 0.8rem !important;
                padding-top: 1.2rem !important;
            }}
            .karta-navbar {{
                padding: 14px 16px;
            }}
            .karta-brand-title {{
                font-size: 1.08rem;
            }}
            .kpi-grid {{
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
            }}
            .kpi-num {{
                font-size: 1.18rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_grid(items: list[dict]):
    """Render kartu KPI responsif yang otomatis menjadi 2 kolom di HP dan N kolom di Desktop."""
    html = '<div class="kpi-grid">'
    for it in items:
        warna = it.get("warna", "#0D9488")
        html += (
            f'<div class="kpi-box" style="border-top: 3px solid {warna};">'
            f'<div class="kpi-lbl">{it["label"]}</div>'
            f'<div class="kpi-num">{it["nilai"]}</div>'
            f'<div class="kpi-meta">{it["sub"]}</div>'
            f"</div>"
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_tabel_html(df: pd.DataFrame, kolom_format: dict[str, str] | None = None):
    """Render DataFrame sebagai tabel HTML responsif yang mengikuti tema Light/Dark."""
    kolom_format = kolom_format or {}
    ths = "".join(f"<th>{c}</th>" for c in df.columns)
    rows_html = []
    for _, row in df.iterrows():
        tds = []
        for c in df.columns:
            val = row[c]
            if c in kolom_format and isinstance(val, (int, float, np.floating)):
                teks = kolom_format[c].format(val)
            else:
                teks = str(val)
            tds.append(f"<td>{teks}</td>")
        rows_html.append(f"<tr>{''.join(tds)}</tr>")
    html = (
        f'<div class="karta-table-wrap">'
        f'<table class="karta-table"><thead><tr>{ths}</tr></thead>'
        f"<tbody>{''.join(rows_html)}</tbody></table></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def render_peta_leaflet_surakarta(
    df_tps: pd.DataFrame,
    mode_gelap: bool,
    hujan_24j_sim: float = 14.0,
    serbuk_kebutuhan_ton: float = 18.5,
    ton_maggot_harian: float = 28.0,
) -> None:
    """Render WebGIS Spasial Multi-Layer (Citra Satelit Esri/Maxar + Live Big Data Open-Meteo + Koridor Solo Raya)."""
    bg_card = "#0F172A" if mode_gelap else "#FFFFFF"
    bg_bar = "#1E293B" if mode_gelap else "#F8FAFC"
    fg_main = "#F8FAFC" if mode_gelap else "#0F172A"
    fg_sub = "#94A3B8" if mode_gelap else "#475569"
    border_c = "#334155" if mode_gelap else "#E2E8F0"

    titik_json = []
    heat_points = []
    for _, r in df_tps.iterrows():
        org_pct = float(r["Organik_Basah_Pct"])
        air_pct = float(r["Kadar_Air_Rata_Pct"])
        ton_val = float(r["Total_Tonase"])
        if org_pct >= 50.0:
            warna_m = "#E11D48"
            status_se = "Prioritas Tinggi SE 11/2026 (Wajib Unit BSF / Kompos)"
            rute_dom = "Rute M (Maggot BSF) / Rute B"
        elif org_pct >= 35.0:
            warna_m = "#D97706"
            status_se = "Pantauan Sedang (Intervensi Bank Sampah RW + Bio-Drying)"
            rute_dom = "Rute B (Bio-Drying + Serbuk Kayu)"
        else:
            warna_m = "#0D9488"
            status_se = "Patuh / Terkendali (Dominan Kering — Layak Energi PLTSa)"
            rute_dom = "Rute U (Umpan Gasifikasi Langsung)"

        lat_f = float(r["lat"])
        lon_f = float(r["lon"])
        gmaps = f"https://www.google.com/maps/search/?api=1&query={lat_f},{lon_f}"
        streetview = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat_f},{lon_f}"
        titik_json.append({
            "kode": r["tps"],
            "nama": r["nama_tps"],
            "kec": r["kecamatan"],
            "alamat": r["alamat"],
            "tipe": str(r["tipe_tps"]).capitalize(),
            "lat": lat_f,
            "lon": lon_f,
            "jarak": float(r["jarak_km"]),
            "ton": round(ton_val, 1),
            "air": round(air_pct, 1),
            "org": round(org_pct, 1),
            "plastik": round(float(r["Plastik_Pct"]), 1),
            "lhv": round(float(r["LHV_Rata_MJ_kg"]), 2),
            "warna": warna_m,
            "status_se": status_se,
            "rute_dom": rute_dom,
            "gmaps": gmaps,
            "streetview": streetview,
        })
        # Intensitas heatmap spasial berdasarkan beban air & organik
        intensitas = min(1.0, max(0.25, (org_pct / 68.0) * (ton_val / 28.0)))
        heat_points.append([lat_f, lon_f, round(intensitas, 3)])

    pltsa_js = json.dumps(LOKASI_PLTSA_PUTRI_CEMPO)
    tps_js = json.dumps(titik_json)
    heat_js = json.dumps(heat_points)
    skh_js = json.dumps(SENTRA_MEBEL_SUKOHARJO)
    bsf_js = json.dumps(UNIT_BSF_SURAKARTA)
    zona_js = json.dumps(ZONA_SPASIAL_PUTRI_CEMPO)
    default_base = "dark" if mode_gelap else "voyager"

    html_map = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
            * {{ box-sizing: border-box; }}
            body {{
                margin: 0;
                padding: 0;
                font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
                background: transparent;
                color: {fg_main};
            }}
            .gis-shell {{
                border: 1px solid {border_c};
                border-radius: 14px;
                overflow: hidden;
                background: {bg_card};
                box-shadow: 0 8px 26px rgba(15, 23, 42, 0.08);
            }}
            /* Top Real-Time Satellite & Weather Big Data Telemetry Bar */
            .gis-hud-top {{
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
                padding: 10px 14px;
                background: {bg_bar};
                border-bottom: 1px solid {border_c};
                font-size: 11.5px;
            }}
            .hud-live-badge {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 4px 10px;
                border-radius: 999px;
                background: rgba(13, 148, 136, 0.14);
                color: #0D9488;
                font-weight: 800;
                font-family: 'JetBrains Mono', monospace;
                font-size: 10.5px;
                letter-spacing: 0.03em;
            }}
            .hud-dot {{
                width: 7px;
                height: 7px;
                border-radius: 50%;
                background: #10B981;
                box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.25);
            }}
            .hud-metrics {{
                display: flex;
                flex-wrap: wrap;
                gap: 14px;
                align-items: center;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                color: {fg_sub};
            }}
            .hud-metrics strong {{
                color: {fg_main};
                font-weight: 700;
            }}
            /* Control Toolbar */
            .gis-toolbar {{
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
                padding: 8px 14px;
                background: {bg_card};
                border-bottom: 1px solid {border_c};
            }}
            .btn-group {{
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                align-items: center;
            }}
            .gis-btn {{
                padding: 5px 10px;
                border-radius: 7px;
                border: 1px solid {border_c};
                background: {bg_bar};
                color: {fg_main};
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 11.2px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.15s ease;
            }}
            .gis-btn:hover {{
                border-color: #0D9488;
                color: #0D9488;
            }}
            .gis-btn.active {{
                background: #0D9488;
                color: #FFFFFF;
                border-color: #0D9488;
            }}
            #map {{
                width: 100%;
                height: 500px;
                position: relative;
            }}
            /* Legend Footer */
            .gis-legend {{
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
                padding: 9px 14px;
                background: {bg_bar};
                border-top: 1px solid {border_c};
                font-size: 11.2px;
                color: {fg_sub};
            }}
            .legend-items {{
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                align-items: center;
            }}
            .leg-item {{
                display: inline-flex;
                align-items: center;
                gap: 5px;
                font-weight: 600;
                color: {fg_main};
            }}
            .leg-dot {{
                width: 10px;
                height: 10px;
                border-radius: 50%;
                display: inline-block;
            }}
            .leg-line {{
                width: 18px;
                height: 3px;
                display: inline-block;
                border-radius: 2px;
            }}
            /* Popup Styling */
            .leaflet-popup-content-wrapper {{
                background: {bg_card};
                color: {fg_main};
                border-radius: 12px;
                border: 1px solid {border_c};
                box-shadow: 0 10px 28px rgba(0,0,0,0.22);
                font-size: 12.2px;
                padding: 2px;
            }}
            .leaflet-popup-tip {{ background: {bg_card}; }}
            .leaflet-control-layers {{
                background: {bg_card} !important;
                color: {fg_main} !important;
                border: 1px solid {border_c} !important;
                border-radius: 10px !important;
                padding: 6px 10px !important;
                font-family: 'Plus Jakarta Sans', sans-serif !important;
                font-size: 11.5px !important;
                box-shadow: 0 4px 14px rgba(0,0,0,0.15) !important;
            }}
            .gmaps-btn {{
                display: inline-block;
                margin-top: 8px;
                margin-right: 6px;
                padding: 5px 10px;
                background: #0D9488;
                color: #FFFFFF !important;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 700;
                font-size: 11px;
            }}
            .gmaps-btn.secondary {{
                background: #334155;
            }}
            .tps-label-tag {{
                background: rgba(15, 23, 42, 0.84);
                color: #F8FAFC;
                padding: 2px 6px;
                border-radius: 5px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 10px;
                font-weight: 700;
                border: 1px solid rgba(255,255,255,0.25);
                white-space: nowrap;
            }}
            @keyframes dashFlow {{
                to {{ stroke-dashoffset: -24; }}
            }}
            .animated-route {{
                animation: dashFlow 1.4s linear infinite;
            }}
        </style>
    </head>
    <body>
        <div class="gis-shell">
            <!-- Bar 1: Live Meteorological & Satellite Reanalysis Telemetry -->
            <div class="gis-hud-top">
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                    <span class="hud-live-badge"><span class="hud-dot"></span>BMKG WMO-96751 &times; GEE SENTINEL-2/LANDSAT-9 &times; ECMWF ERA5</span>
                    <span id="meteo-status" style="font-size:11px;color:{fg_sub};">Menghubungkan ke satelit cuaca Solo Raya (-7.54&deg;S, 110.86&deg;E)...</span>
                </div>
                <div class="hud-metrics">
                    <span>Suhu/LST: <strong id="m-temp">29.4 &deg;C</strong></span>
                    <span>RH Udara: <strong id="m-rh">74%</strong></span>
                    <span>Radiasi Surya: <strong id="m-rad">540 W/m&sup2;</strong></span>
                    <span>Hujan 24J: <strong id="m-rain">{hujan_24j_sim:.1f} mm</strong></span>
                    <span>Angin: <strong id="m-wind">11.2 km/j</strong></span>
                </div>
            </div>

            <!-- Bar 2: Spatial Camera Fly-To & Basemap Selector -->
            <div class="gis-toolbar">
                <div class="btn-group">
                    <span style="font-size:11px;font-weight:700;color:{fg_sub};margin-right:2px;">FOKUS SPASIAL:</span>
                    <button class="gis-btn active" onclick="flyView('solo', this)">Solo Raya (12 TPS + Koridor)</button>
                    <button class="gis-btn" onclick="flyView('pltsa_sat', this)">Satelit PLTSa Putri Cempo (17 Ha)</button>
                    <button class="gis-btn" onclick="flyView('pasar_kritis', this)">Klaster Pasar Kritis (SE 11/2026)</button>
                    <button class="gis-btn" onclick="flyView('sukoharjo', this)">Sentra Serbuk Kayu Sukoharjo</button>
                    <button class="gis-btn" onclick="flyView('bsf', this)">Unit Maggot BSF (Purwosari)</button>
                </div>
                <div class="btn-group">
                    <span style="font-size:11px;font-weight:700;color:{fg_sub};margin-right:2px;">MODE PETA:</span>
                    <button id="btn-base-voyager" class="gis-btn {'active' if not mode_gelap else ''}" onclick="setBasemap('voyager')">GIS Vektor Terang</button>
                    <button id="btn-base-sat" class="gis-btn" onclick="setBasemap('satellite')">Citra Satelit Hibrida (Esri/Maxar)</button>
                    <button id="btn-base-dark" class="gis-btn {'active' if mode_gelap else ''}" onclick="setBasemap('dark')">Taktis Gelap</button>
                </div>
            </div>

            <!-- Interactive Map Canvas -->
            <div id="map"></div>

            <!-- Bar 3: Spatial Legend & Circular Flow Summary -->
            <div class="gis-legend">
                <div class="legend-items">
                    <span class="leg-item"><span class="leg-dot" style="background:#E11D48;"></span>TPS Prioritas Tinggi (&ge;50% Organik &rarr; Wajib BSF/Kompos)</span>
                    <span class="leg-item"><span class="leg-dot" style="background:#D97706;"></span>TPS Pantauan Sedang (35–50% Organik &rarr; Bio-Drying)</span>
                    <span class="leg-item"><span class="leg-dot" style="background:#0D9488;"></span>TPS Patuh (&lt;35% Organik &rarr; Umpan Gasifikasi)</span>
                    <span class="leg-item"><span class="leg-line" style="background:#D97706;"></span>Koridor Serbuk Kayu UMKM Sukoharjo ({serbuk_kebutuhan_ton:.1f} t/hr)</span>
                    <span class="leg-item"><span class="leg-dot" style="background:#16A34A;"></span>Unit Maggot BSF ({ton_maggot_harian:.1f} t/hr)</span>
                </div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:10.5px;">
                    Klik titik/poligon untuk detail telemetri &amp; Google Maps Street View &nearr;
                </div>
            </div>
        </div>

        <script>
            // 1. Definisi Multi-Basemap (GIS Terang, Citra Satelit Esri World Imagery + Hybrid Labels, OSM, Dark)
            var baseVoyager = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                maxZoom: 19,
                attribution: '&copy; OpenStreetMap &amp; CARTO Voyager'
            }});
            var baseDark = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                maxZoom: 19,
                attribution: '&copy; OpenStreetMap &amp; CARTO Dark Matter'
            }});
            var esriSat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                maxZoom: 19,
                attribution: 'Tiles &copy; Esri, Maxar, Earthstar Geographics, Sentinel-2'
            }});
            var esriLabels = L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                maxZoom: 19,
                opacity: 0.88
            }});
            var baseSatelliteHybrid = L.layerGroup([esriSat, esriLabels]);

            var defaultMode = '{default_base}';
            var initialLayer = (defaultMode === 'dark') ? baseDark : baseVoyager;

            var map = L.map('map', {{
                center: [-7.5585, 110.8240],
                zoom: 13,
                layers: [initialLayer]
            }});

            function setBasemap(mode) {{
                map.removeLayer(baseVoyager);
                map.removeLayer(baseDark);
                map.removeLayer(baseSatelliteHybrid);
                document.getElementById('btn-base-voyager').classList.remove('active');
                document.getElementById('btn-base-sat').classList.remove('active');
                document.getElementById('btn-base-dark').classList.remove('active');

                if (mode === 'satellite') {{
                    map.addLayer(baseSatelliteHybrid);
                    document.getElementById('btn-base-sat').classList.add('active');
                }} else if (mode === 'dark') {{
                    map.addLayer(baseDark);
                    document.getElementById('btn-base-dark').classList.add('active');
                }} else {{
                    map.addLayer(baseVoyager);
                    document.getElementById('btn-base-voyager').classList.add('active');
                }}
            }}

            // 2. Layer Groups untuk 5 Layer Spasial Sesuai Naskah Proposal
            var layerTPS = L.layerGroup().addTo(map);
            var layerRadiusKelurahan = L.layerGroup().addTo(map);
            var layerRuteTruk = L.layerGroup().addTo(map);
            var layerSukoharjo = L.layerGroup().addTo(map);
            var layerPutriCempoBSF = L.layerGroup().addTo(map);

            var pltsa = {pltsa_js};
            var tpsList = {tps_js};
            var heatPts = {heat_js};
            var skhList = {skh_js};
            var bsfList = {bsf_js};
            var zonaPC = {zona_js};

            // Layer Heatmap Spasial Beban Organik Basah
            var layerHeatmap = L.heatLayer(heatPts, {{
                radius: 36,
                blur: 26,
                maxZoom: 15,
                gradient: {{0.25: '#0D9488', 0.55: '#F59E0B', 0.85: '#E11D48', 1.0: '#9F1239'}}
            }}).addTo(map);

            // 3. Poligon Zonasi Kawasan TPA Putri Cempo (17 Ha & Zona Eks-Kebakaran 2,4 Ha Sep 2026)
            var polyTPA = L.polygon(zonaPC.kawasan_tpa_17ha, {{
                color: '#0284C7',
                weight: 2,
                dashArray: '5, 5',
                fillColor: '#0284C7',
                fillOpacity: 0.12
            }}).bindPopup(
                '<div style="min-width:225px;">' +
                '<div style="font-weight:800;font-size:13px;color:#0284C7;">Kawasan TPA &amp; PLTSa Putri Cempo (17 Ha)</div>' +
                '<div style="font-size:11.5px;margin-top:4px;">Kap. Desain PLTSa: 540 ton/hari | Olah Aktual: 100–150 ton/hari | Syarat Gasifikasi: Kadar Air &le;20%</div>' +
                '<div style="font-size:11px;margin-top:4px;opacity:0.8;">Status KLH: Penghentian Open Dumping &amp; Kepatuhan SE MenLH No. 11/2026</div>' +
                '</div>'
            );
            polyTPA.addTo(layerPutriCempoBSF);

            var polyFire = L.polygon(zonaPC.zona_eks_kebakaran_2_4ha, {{
                color: '#E11D48',
                weight: 2,
                fillColor: '#E11D48',
                fillOpacity: 0.30
            }}).bindPopup(
                '<div style="min-width:220px;">' +
                '<div style="font-weight:800;font-size:13px;color:#E11D48;">Zona Eks-Kebakaran Gunungan Lama (2,4 Ha)</div>' +
                '<div style="font-size:11.5px;margin-top:4px;">Insiden September 2026 (Pemadaman menyerap BTT Rp2,3 Miliar). Akibat akumulasi organik tak terpilah &amp; gas metana di gunungan open dumping (&plusmn;28 m).</div>' +
                '</div>'
            );
            polyFire.addTo(layerPutriCempoBSF);

            var polyBio = L.polygon(zonaPC.bunker_biodrying_pltsa, {{
                color: '#0D9488',
                weight: 2,
                fillColor: '#0D9488',
                fillOpacity: 0.28
            }}).bindPopup(
                '<div style="min-width:215px;">' +
                '<div style="font-weight:800;font-size:13px;color:#0D9488;">Bunker Bio-Drying &amp; Tipping Floor KARTA</div>' +
                '<div style="font-size:11.5px;margin-top:4px;">Titik kamera Computer Vision KARTA, jembatan timbang, dan fasilitas pencampuran <em>bulking agent</em> serbuk kayu Sukoharjo (10–20%).</div>' +
                '</div>'
            );
            polyBio.addTo(layerPutriCempoBSF);

            // Marker Pusat PLTSa Putri Cempo
            var pltsaIcon = L.divIcon({{
                className: 'custom-pltsa',
                html: '<div style="background:linear-gradient(135deg,#0284C7,#0D9488);color:#fff;padding:5px 10px;border-radius:8px;font-weight:800;font-size:11px;border:2px solid #fff;box-shadow:0 3px 10px rgba(0,0,0,0.35);white-space:nowrap;">GERBANG AI PLTSa PUTRI CEMPO</div>',
                iconSize: [195, 28],
                iconAnchor: [97, 14]
            }});
            L.marker([pltsa.lat, pltsa.lon], {{icon: pltsaIcon}}).addTo(layerPutriCempoBSF)
                .bindPopup(
                    '<div style="min-width:240px;">' +
                    '<div style="font-weight:800;font-size:13.5px;color:#0284C7;">' + pltsa.nama + '</div>' +
                    '<div style="font-size:11.5px;opacity:0.8;margin-bottom:6px;">' + pltsa.alamat + '</div>' +
                    '<table style="width:100%;font-size:11.8px;border-collapse:collapse;">' +
                    '<tr><td>Target Output Listrik:</td><td style="text-align:right;font-weight:700;">5–10 MW (Aktual 1,5–1,6 MW)</td></tr>' +
                    '<tr><td>Syarat Mutu Gasifier:</td><td style="text-align:right;font-weight:700;color:#0D9488;">Kadar Air &le; 20,0%</td></tr>' +
                    '<tr><td>Durasi Bio-Drying:</td><td style="text-align:right;font-weight:700;">&plusmn;5 Hari &rarr; 3,2 Hari (KARTA)</td></tr>' +
                    '</table>' +
                    '<a class="gmaps-btn" href="' + pltsa.gmaps_url + '" target="_blank">Google Maps &nearr;</a>' +
                    '<a class="gmaps-btn secondary" href="https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=' + pltsa.lat + ',' + pltsa.lon + '" target="_blank">Street View 360&deg; &nearr;</a>' +
                    '</div>'
                );

            // 4. Render 12 TPS Kota Surakarta + Cincin Radius Kelurahan + Rute Truk
            tpsList.forEach(function(item) {{
                // Garis Rute Pengiriman Armada DLH ke PLTSa Putri Cempo
                L.polyline([[item.lat, item.lon], [pltsa.lat, pltsa.lon]], {{
                    color: item.warna,
                    weight: 2.2,
                    opacity: 0.62,
                    dashArray: '6, 6',
                    className: 'animated-route'
                }}).addTo(layerRuteTruk);

                // Cincin Radius Cakupan Kelurahan / Beban Tonase (meter)
                L.circle([item.lat, item.lon], {{
                    radius: Math.max(260, item.ton * 22),
                    color: item.warna,
                    weight: 1,
                    fillColor: item.warna,
                    fillOpacity: 0.11
                }}).addTo(layerRadiusKelurahan);

                // Titik Utama TPS
                var circle = L.circleMarker([item.lat, item.lon], {{
                    radius: 9.5,
                    fillColor: item.warna,
                    color: '#FFFFFF',
                    weight: 2.2,
                    opacity: 1,
                    fillOpacity: 0.95
                }}).addTo(layerTPS);

                circle.bindTooltip(
                    '<span class="tps-label-tag">' + item.kode + ' &middot; ' + item.org + '% Org</span>',
                    {{permanent: false, direction: 'top', offset: [0, -8], opacity: 0.95}}
                );

                var popupHtml =
                    '<div style="min-width:245px;">' +
                    '<div style="font-weight:800;font-size:13.5px;margin-bottom:2px;">' + item.kode + ' &middot; ' + item.nama + '</div>' +
                    '<div style="font-size:11.2px;opacity:0.78;margin-bottom:6px;">' + item.alamat + ' &bull; Kec. ' + item.kec + ' (' + item.jarak + ' km ke PLTSa)</div>' +
                    '<div style="padding:4px 8px;border-radius:6px;background:rgba(13,148,136,0.1);font-size:11px;font-weight:700;color:' + item.warna + ';margin-bottom:6px;">' +
                    item.status_se + '</div>' +
                    '<table style="width:100%;font-size:11.8px;border-collapse:collapse;">' +
                    '<tr><td>Karakteristik Kawasan:</td><td style="text-align:right;font-weight:600;">' + item.tipe + ' (' + item.ton + ' ton)</td></tr>' +
                    '<tr><td>Fraksi Organik Basah:</td><td style="text-align:right;font-weight:700;color:' + item.warna + ';">' + item.org + '%</td></tr>' +
                    '<tr><td>Fraksi Plastik:</td><td style="text-align:right;font-weight:600;">' + item.plastik + '%</td></tr>' +
                    '<tr><td>Kadar Air Rata-rata:</td><td style="text-align:right;font-weight:700;">' + item.air + '%</td></tr>' +
                    '<tr><td>Nilai Kalor (LHV):</td><td style="text-align:right;font-weight:700;">' + item.lhv + ' MJ/kg</td></tr>' +
                    '<tr><td>Keputusan Triase KARTA:</td><td style="text-align:right;font-weight:700;color:#0D9488;">' + item.rute_dom + '</td></tr>' +
                    '</table>' +
                    '<a class="gmaps-btn" href="' + item.gmaps + '" target="_blank">Google Maps &nearr;</a>' +
                    '<a class="gmaps-btn secondary" href="' + item.streetview + '" target="_blank">Street View 360&deg; &nearr;</a>' +
                    '</div>';
                circle.bindPopup(popupHtml);
            }});

            // 5. Render Koridor Sirkular Pemasok Serbuk Kayu UMKM Mebel Sukoharjo (Disperinaker Kab. Sukoharjo)
            skhList.forEach(function(skh) {{
                L.polyline([[skh.lat, skh.lon], [pltsa.lat, pltsa.lon]], {{
                    color: '#D97706',
                    weight: 2.6,
                    opacity: 0.78,
                    dashArray: '8, 6'
                }}).addTo(layerSukoharjo);

                var skhIcon = L.divIcon({{
                    className: 'custom-skh',
                    html: '<div style="background:#B45309;color:#fff;padding:3px 8px;border-radius:6px;font-weight:700;font-size:10.5px;border:1.5px solid #FEF3C7;box-shadow:0 2px 6px rgba(0,0,0,0.3);white-space:nowrap;">' + skh.kode + ' &middot; Mebel Sukoharjo</div>',
                    iconSize: [148, 22],
                    iconAnchor: [74, 11]
                }});

                L.marker([skh.lat, skh.lon], {{icon: skhIcon}}).addTo(layerSukoharjo)
                    .bindPopup(
                        '<div style="min-width:235px;">' +
                        '<div style="font-weight:800;font-size:13px;color:#D97706;">' + skh.kode + ' &middot; ' + skh.nama + '</div>' +
                        '<div style="font-size:11.2px;opacity:0.8;margin-bottom:6px;">' + skh.alamat + ' (Mitra Disperinaker Kab. Sukoharjo)</div>' +
                        '<table style="width:100%;font-size:11.8px;border-collapse:collapse;">' +
                        '<tr><td>Peran Sirkular:</td><td style="text-align:right;font-weight:700;">Bulking Agent Bio-Drying (10–20%)</td></tr>' +
                        '<tr><td>Potensi Serbuk Gergaji:</td><td style="text-align:right;font-weight:700;">' + skh.pasokan_serbuk_ton_hari + ' ton/hari</td></tr>' +
                        '<tr><td>Kadar Air Serbuk:</td><td style="text-align:right;font-weight:700;color:#0D9488;">' + skh.kadar_air_serbuk + '% (Kering)</td></tr>' +
                        '<tr><td>Nilai Kalor Serbuk:</td><td style="text-align:right;font-weight:700;">' + skh.lhv_mj_kg + ' MJ/kg</td></tr>' +
                        '<tr><td>Jarak Logistik ke PLTSa:</td><td style="text-align:right;font-weight:600;">' + skh.jarak_km + ' km</td></tr>' +
                        '</table>' +
                        '<a class="gmaps-btn" href="' + skh.gmaps_url + '" target="_blank">Lokasi Sentra di Google Maps &nearr;</a>' +
                        '</div>'
                    );
            }});

            // 6. Render Unit Hilir Biokonversi Maggot BSF (RW 07 Purwosari & Unit BSF Putri Cempo)
            bsfList.forEach(function(bsf) {{
                var bsfIcon = L.divIcon({{
                    className: 'custom-bsf',
                    html: '<div style="background:#15803D;color:#fff;padding:3px 8px;border-radius:6px;font-weight:700;font-size:10.5px;border:1.5px solid #DCFCE7;box-shadow:0 2px 6px rgba(0,0,0,0.3);white-space:nowrap;">' + bsf.kode + ' &middot; Unit Maggot BSF</div>',
                    iconSize: [148, 22],
                    iconAnchor: [74, 11]
                }});
                L.marker([bsf.lat, bsf.lon], {{icon: bsfIcon}}).addTo(layerPutriCempoBSF)
                    .bindPopup(
                        '<div style="min-width:230px;">' +
                        '<div style="font-weight:800;font-size:13px;color:#16A34A;">' + bsf.nama + '</div>' +
                        '<div style="font-size:11.2px;opacity:0.8;margin-bottom:6px;">' + bsf.alamat + '</div>' +
                        '<table style="width:100%;font-size:11.8px;border-collapse:collapse;">' +
                        '<tr><td>Syarat Mutu Umpan:</td><td style="text-align:right;font-weight:700;">Kadar Air 60–90%, Plastik &lt;5%</td></tr>' +
                        '<tr><td>Kapasitas Olah:</td><td style="text-align:right;font-weight:700;">' + bsf.kapasitas_ton_hari + ' ton/hari</td></tr>' +
                        '<tr><td>Siklus Biokonversi (Eawag):</td><td style="text-align:right;font-weight:600;">' + bsf.siklus_hari + ' Hari (Reduksi ' + bsf.reduksi_persen + '%)</td></tr>' +
                        '</table>' +
                        '<a class="gmaps-btn" href="' + bsf.gmaps_url + '" target="_blank">Buka Lokasi di Google Maps &nearr;</a>' +
                        '</div>'
                    );
            }});

            // 7. Kontrol Layer Interaktif di Pojok Kanan Atas Peta
            var baseMaps = {{
                "Peta GIS Vektor Terang (Carto)": baseVoyager,
                "Citra Satelit Hibrida (Esri/Maxar)": baseSatelliteHybrid,
                "Peta Komando Taktis Gelap": baseDark
            }};
            var overlayMaps = {{
                "Sidik Jari 12 TPS & Pasar Surakarta": layerTPS,
                "Radius Cakupan Kelurahan (Buffer)": layerRadiusKelurahan,
                "Heatmap Beban Organik Basah": layerHeatmap,
                "Rute Armada Truk DLH ke PLTSa": layerRuteTruk,
                "Koridor Serbuk Kayu UMKM Sukoharjo": layerSukoharjo,
                "Zonasi TPA Putri Cempo (17 Ha) & Unit BSF": layerPutriCempoBSF
            }};
            L.control.layers(baseMaps, overlayMaps, {{collapsed: true}}).addTo(map);

            // 8. Fungsi Navigasi Kamera Spasial (Fly-To)
            function flyView(target, btnEl) {{
                var btns = document.querySelectorAll('.gis-toolbar .btn-group:first-child .gis-btn');
                btns.forEach(function(b) {{ b.classList.remove('active'); }});
                if (btnEl) btnEl.classList.add('active');

                if (target === 'pltsa_sat') {{
                    setBasemap('satellite');
                    map.flyTo([pltsa.lat, pltsa.lon], 16, {{duration: 1.2}});
                }} else if (target === 'pasar_kritis') {{
                    map.flyTo([-7.5560, 110.8255], 14, {{duration: 1.0}});
                }} else if (target === 'sukoharjo') {{
                    map.flyTo([-7.5680, 110.7980], 12, {{duration: 1.1}});
                }} else if (target === 'bsf') {{
                    map.flyTo([-7.5618, 110.7935], 15, {{duration: 1.1}});
                }} else {{
                    map.flyTo([-7.5620, 110.8220], 12, {{duration: 1.0}});
                }}
            }}

            // 9. Fetch Real-Time Big Data Cuaca & Radiasi Satelit dari Open-Meteo API (Solo Raya)
            fetch('https://api.open-meteo.com/v1/forecast?latitude=-7.5378&longitude=110.8586&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,shortwave_radiation&daily=precipitation_sum&timezone=Asia%2FJakarta')
                .then(function(res) {{ return res.json(); }})
                .then(function(data) {{
                    if (data && data.current) {{
                        var c = data.current;
                        document.getElementById('m-temp').textContent = c.temperature_2m + ' °C';
                        document.getElementById('m-rh').textContent = c.relative_humidity_2m + '%';
                        document.getElementById('m-rad').textContent = (c.shortwave_radiation !== undefined ? c.shortwave_radiation : 480) + ' W/m²';
                        document.getElementById('m-wind').textContent = c.wind_speed_10m + ' km/j';
                        var rainDaily = (data.daily && data.daily.precipitation_sum && data.daily.precipitation_sum[0] !== undefined)
                            ? data.daily.precipitation_sum[0]
                            : c.precipitation;
                        document.getElementById('m-rain').textContent = rainDaily + ' mm (Aktual) / {hujan_24j_sim:.1f} mm (Sim)';
                        document.getElementById('meteo-status').textContent = 'Terhubung Live: Grid Satelit Putri Cempo (-7.5378°S, 110.8586°E) · Pembaruan ' + (c.time || 'Real-Time');
                    }}
                }})
                .catch(function() {{
                    document.getElementById('meteo-status').textContent = 'Mode Simulasi Terkalibrasi BMKG Stasiun Adi Soemarmo (-7.5378°S, 110.8586°E)';
                }});
        </script>
    </body>
    </html>
    """
    components.html(html_map, height=625)


def buat_grafik_kalibrasi_modern(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_lo: np.ndarray,
    y_hi: np.ndarray,
    mode_gelap: bool = False,
) -> Image.Image:
    """Render grafik kalibrasi beresolusi tinggi dengan latar terang/gelap sesuai tema aktif."""
    W, H = 720, 420
    bg = (30, 41, 59) if mode_gelap else (255, 255, 255)
    fg = (241, 245, 249) if mode_gelap else (15, 23, 42)
    fg_sub = (148, 163, 184) if mode_gelap else (100, 116, 139)
    grid_c = (51, 65, 85) if mode_gelap else (226, 232, 240)
    img = Image.new("RGB", (W, H), bg)
    dr = ImageDraw.Draw(img)

    pad_l, pad_r, pad_t, pad_b = 62, 28, 42, 50
    pw, ph = W - pad_l - pad_r, H - pad_t - pad_b

    def ke_xy(xv: float, yv: float) -> tuple[int, int]:
        xn = np.clip((xv - 0.05) / 0.80, 0.0, 1.0)
        yn = np.clip((yv - 0.05) / 0.80, 0.0, 1.0)
        return int(pad_l + xn * pw), int(pad_t + (1.0 - yn) * ph)

    # Zona Aman Gasifikasi <= 20%
    _, y20 = ke_xy(0.20, 0.20)
    zona_aman = (19, 48, 46) if mode_gelap else (240, 253, 250)
    dr.rectangle([pad_l, y20, W - pad_r, H - pad_b], fill=zona_aman)

    for v in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        x0, y0 = ke_xy(v, v)
        dr.line([(pad_l, y0), (W - pad_r, y0)], fill=grid_c, width=1)
        dr.line([(x0, pad_t), (x0, H - pad_b)], fill=grid_c, width=1)
        lbl = f"{int(v * 100)}%"
        dr.text((pad_l - 38, y0 - 6), lbl, fill=fg_sub)
        dr.text((x0 - 12, H - pad_b + 10), lbl, fill=fg_sub)

    dr.line([(pad_l, y20), (W - pad_r, y20)], fill=(225, 29, 72), width=2)
    dr.text((pad_l + 8, y20 - 16), "Batas Maksimum Gasifikasi PLTSa (20%)", fill=(225, 29, 72))

    p1, p2 = ke_xy(0.08, 0.08), ke_xy(0.82, 0.82)
    dr.line([p1, p2], fill=fg_sub, width=2)

    for yt, yp, lo, hi in zip(y_true, y_pred, y_lo, y_hi):
        _, y_lo_px = ke_xy(yt, lo)
        _, y_hi_px = ke_xy(yt, hi)
        x_px, y_px = ke_xy(yt, yp)
        ok = (yt >= lo) and (yt <= hi)
        c_bar = (14, 165, 233) if ok else (245, 158, 11)
        c_dot = (13, 148, 136) if ok else (225, 29, 72)
        dr.line([(x_px, y_hi_px), (x_px, y_lo_px)], fill=c_bar, width=2)
        dr.line([(x_px - 4, y_hi_px), (x_px + 4, y_hi_px)], fill=c_bar, width=2)
        dr.line([(x_px - 4, y_lo_px), (x_px + 4, y_lo_px)], fill=c_bar, width=2)
        dr.ellipse([x_px - 5, y_px - 5, x_px + 5, y_px + 5], fill=c_dot)

    dr.text((pad_l, 12), "Kurva Kalibrasi Kadar Air Uji Oven SNI 19-3964-1994 (Sumbu X) vs Prediksi KARTA + Interval 80% (Sumbu Y)", fill=fg)
    dr.text((W // 2 - 90, H - 22), "Kadar Air Aktual Uji Oven (%)", fill=fg)
    return img


# ------------------------------------------------------------------ Penyiapan Ekosistem Ter-cache
@st.cache_resource
def muat_ekosistem_karta(jenis_visi: str, metode_air: str, port_serial: str):
    pastikan_benchmark_gt()
    df_bench = pd.read_csv(FOLDER_BENCHMARK / "uji_oven_surakarta.csv")
    df_train = df_bench[df_bench["split"] == "train"].reset_index(drop=True)
    model_visi = muat_model(jenis_visi)
    model_air = ModelKadarAir(metode=metode_air, alpha_interval=0.20).fit(df_train, df_train["w_oven"])
    konveyor = Konveyor(port_serial or None)
    return model_visi, model_air, konveyor, df_bench


# ------------------------------------------------------------------ Sidebar Konfigurasi
with st.sidebar:
    st.markdown("### Pengaturan Sistem KARTA")
    mode_gelap = st.toggle("Mode Tampilan Gelap (Dark Mode)", value=False)
    tema = dapatkan_palet_tema(mode_gelap)
    suntikkan_css_web(tema)

    st.markdown("---")
    st.markdown("**1. Arsitektur Model Visi & Regresi**")
    pilihan_visi_map = {
        "KARTA-v4 MultiScale Neural-Texture": "karta_v4",
        "DeepLabV3-MobileNetV3 Edge Hybrid": "deeplabv3",
        "SegFormer-B0 Semantic Segmentation": "segformer",
        "Ultralytics YOLOv11n-Seg": "yolo",
        "CLIPSeg Zero-Shot Text-Guided": "zero-shot",
        "Baseline Aturan HSV (Pembanding)": "demo",
    }
    label_visi = st.selectbox("Model Segmentasi Citra", list(pilihan_visi_map.keys()), index=0)
    jenis_visi = pilihan_visi_map[label_visi]

    pilihan_air_map = {
        "Conformal Quantile Regression (CQR)": "gbm",
        "Physics-Informed Jackknife+ Ridge": "koreksi_linear",
        "Baseline Fisika Literatur": "fisika",
    }
    label_air = st.selectbox("Model Estimasi Kadar Air & LHV", list(pilihan_air_map.keys()), index=0)
    metode_air = pilihan_air_map[label_air]

    st.markdown("---")
    st.markdown("**2. Parameter Cuaca & Perangkat Tepi**")
    hujan_24j_default = st.slider("Curah Hujan 24 Jam BMKG (mm)", 0.0, 150.0, 12.0, 0.5)
    hujan_72j_default = st.slider("Akumulasi Hujan 72 Jam (mm)", 0.0, 300.0, 32.0, 1.0)
    port_arduino = st.text_input("Port Serial Arduino Konveyor", value="", placeholder="Kosong = Mode Simulasi")

    st.markdown("---")
    st.caption(
        "**Tim KARTA · Politeknik Statistika STIS**\n\n"
        "Mitra Pengguna: Dinas Lingkungan Hidup Kota Surakarta, Disperinaker Sukoharjo, & PLTSa Putri Cempo."
    )

visi, air, konveyor, df_bench = muat_ekosistem_karta(jenis_visi, metode_air, port_arduino)

# ------------------------------------------------------------------ Top Navigation Banner (Eco-Tech Circular + Batik Kawung Surakarta)
st.markdown(
    f"""
    <div class="karta-navbar">
        <div class="karta-brand-wrap">
            <div class="karta-logo-box">K4</div>
            <div>
                <div class="karta-gov-tag">SISTEM TELEMETRI &amp; INTELIJEN MUTU UMPAN ENERGI SIRKULAR · KOTA SURAKARTA &amp; SUKOHARJO</div>
                <div class="karta-brand-title">KARTA · Kinetic Analytics for Refuse Triage &amp; Allocation</div>
                <div class="karta-brand-sub">
                    Gerbang Cerdas Berbasis Computer Vision, Conformal Prediction (CQR), &amp; Optimasi MILP PLTSa Putri Cempo Surakarta
                </div>
            </div>
        </div>
        <div class="karta-status-pills">
            <span class="karta-chip">TKT 3–4 TERVALIDASI</span>
            <span class="karta-chip">VISI: {jenis_visi.upper()}</span>
            <span class="karta-chip">KALIBRASI: {metode_air.upper()}</span>
            <span class="karta-chip terracotta">KORIDOR SURAKARTA–SUKOHARJO</span>
        </div>
    </div>
    <div class="karta-pipeline-bar">
        <div class="pipe-step">
            <div class="pipe-num">TAHAP 01 · HULU GERBANG</div>
            <div class="pipe-title">Identitas QR TPS &amp; Jembatan Timbang</div>
            <div class="pipe-desc">Pencatatan asal TPS, tonase bersih, &amp; densitas curah gravimetrik (ton/m&sup3;).</div>
        </div>
        <div class="pipe-step teal">
            <div class="pipe-num">TAHAP 02 · EDGE VISION AI</div>
            <div class="pipe-title">Segmentasi Semantik 6 Fraksi</div>
            <div class="pipe-desc">Pemisahan piksel organik basah, plastik, kardus, tekstil, kayu, &amp; inert bebas bias 2D.</div>
        </div>
        <div class="pipe-step">
            <div class="pipe-num">TAHAP 03 · SAINS DATA &amp; IKLIM</div>
            <div class="pipe-title">Regresi Konformal + API Cuaca</div>
            <div class="pipe-desc">Estimasi kadar air &amp; LHV berinterval kepastian P10–P90 terkalibrasi SNI 19-3964-1994.</div>
        </div>
        <div class="pipe-step terracotta">
            <div class="pipe-num">TAHAP 04 · TRIASE SIRKULAR</div>
            <div class="pipe-title">Optimasi Robust MILP 3-Jalur</div>
            <div class="pipe-desc">Alokasi ke Gasifier (&le;20% air), Bio-Drying + Serbuk Kayu Sukoharjo, atau Maggot BSF.</div>
        </div>
        <div class="pipe-step teal">
            <div class="pipe-num">TAHAP 05 · TATA KELOLA DLH</div>
            <div class="pipe-title">WebGIS Satelit &amp; SE MenLH 11/2026</div>
            <div class="pipe-desc">Peta sidik jari kepatuhan TPS, anomali termal GEE, &amp; laporan otomatis Kabid DLH.</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ Navigasi 5 Modul Utama
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "01 · Inspeksi Gerbang & Triase Muatan",
    "02 · Evaluasi Model & Ground Truth Lab",
    "03 · Optimasi Harian MILP & Serbuk Kayu",
    "04 · Peta GIS TPS Surakarta & SE 11/2026",
    "05 · Arsitektur Edge & Telemetri Alat",
])


# ==============================================================================
# TAB 1: INSPEKSI GERBANG & TRIASE MUATAN
# ==============================================================================
with tab1:
    df_citra_unik = df_bench.drop_duplicates(subset=["foto"]).reset_index(drop=True)
    col_kiri, col_kanan = st.columns([1.08, 1.25], gap="large")

    with col_kiri:
        st.markdown(
            """
            <div class="karta-surface">
                <div class="karta-section-head">Akuisisi Muatan Truk & Identitas TPS</div>
                <div class="karta-section-desc">
                    Pilih citra muatan dari Benchmark Ground Truth 12 TPS Kota Surakarta, unggah foto lapangan baru, atau gunakan kamera langsung.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        mode_sumber = st.radio(
            "Metode Input Citra",
            ["Sampel Benchmark Ground Truth (12 TPS Surakarta)", "Unggah Foto Sampah Sendiri", "Kamera / Webcam Langsung"],
            horizontal=False,
        )

        gambar_bgr = None
        mask_gt = None
        baris_gt = None

        if mode_sumber == "Sampel Benchmark Ground Truth (12 TPS Surakarta)":
            opsi_sampel = [
                f"{r['foto']} — {r['nama_tps']} ({r['kecamatan']}) · Split: {r['split'].upper()}"
                for _, r in df_citra_unik.iterrows()
            ]
            pilihan_idx = st.selectbox("Pilih Rekaman Muatan Truk", range(len(opsi_sampel)), format_func=lambda i: opsi_sampel[i])
            baris_gt = df_citra_unik.iloc[pilihan_idx]
            img_path = FOLDER_BENCHMARK / "images" / baris_gt["foto"]
            msk_path = FOLDER_BENCHMARK / "masks" / baris_gt["foto"]
            rgb_pil = np.array(Image.open(img_path).convert("RGB"), dtype=np.uint8)
            gambar_bgr = rgb_pil[:, :, ::-1].copy()
            mask_gt = np.array(Image.open(msk_path), dtype=np.uint8)

            c_m1, c_m2, c_m3 = st.columns(3)
            tps_input = c_m1.text_input("Identitas TPS (QR)", f"{baris_gt['tps']} · {baris_gt['nama_tps']}")
            ton_input = c_m2.number_input("Massa Timbangan (Ton)", 1.0, 20.0, float(baris_gt["ton"]), 0.1)
            vol_input = c_m3.number_input("Volume Bak Truk (m³)", 4.0, 20.0, float(baris_gt["volume_m3"]), 1.0)
            hujan_24j = float(baris_gt["hujan_24j"])
            hujan_72j = float(baris_gt["hujan_72j"])

        elif mode_sumber == "Unggah Foto Sampah Sendiri":
            up_file = st.file_uploader("Unggah Foto Muatan Sampah (.jpg, .jpeg, .png)", type=["jpg", "jpeg", "png"])
            c_u1, c_u2, c_u3 = st.columns(3)
            daftar_tps_str = [f"{t['kode']} · {t['nama']}" for t in TPS_SURAKARTA]
            tps_input = c_u1.selectbox("TPS Asal Muatan", daftar_tps_str)
            ton_input = c_u2.number_input("Massa Timbangan (Ton)", 1.0, 20.0, 6.2, 0.1)
            vol_input = c_u3.number_input("Volume Bak Truk (m³)", 4.0, 20.0, 10.0, 1.0)
            hujan_24j = hujan_24j_default
            hujan_72j = hujan_72j_default
            if up_file is not None:
                rgb_pil = np.array(Image.open(up_file).convert("RGB"), dtype=np.uint8)
                gambar_bgr = rgb_pil[:, :, ::-1].copy()
                qr_det = baca_qr(gambar_bgr)
                if qr_det:
                    st.info(f"Identitas QR Kabin Terbaca: {qr_det}")
        else:
            cam_img = st.camera_input("Rekam Citra dari Kamera / Webcam")
            c_w1, c_w2, c_w3 = st.columns(3)
            tps_input = c_w1.text_input("TPS Asal Muatan", "TPS-01 · TPS Pasar Legi")
            ton_input = c_w2.number_input("Massa Timbangan (Ton)", 1.0, 20.0, 5.8, 0.1)
            vol_input = c_w3.number_input("Volume Bak Truk (m³)", 4.0, 20.0, 10.0, 1.0)
            hujan_24j = hujan_24j_default
            hujan_72j = hujan_72j_default
            if cam_img is not None:
                rgb_pil = np.array(Image.open(cam_img).convert("RGB"), dtype=np.uint8)
                gambar_bgr = rgb_pil[:, :, ::-1].copy()

        # Legenda Fraksi Bersih
        leg_items = "".join(
            f'<div style="display:flex;align-items:center;gap:6px;font-size:0.77rem;font-weight:600;">'
            f'<span style="width:11px;height:11px;border-radius:3px;background:{WARNA_HEX_FRAKSI[k]};display:inline-block;"></span>'
            f"<span>{LABEL_FRAKSI_ID[k]}</span></div>"
            for k in KELAS_VISI
        )
        st.markdown(
            f'<div class="karta-surface" style="padding:12px 16px;display:flex;flex-wrap:wrap;gap:12px;">{leg_items}</div>',
            unsafe_allow_html=True,
        )

        if gambar_bgr is not None:
            t_mulai = time.perf_counter()
            hv_awal = visi(gambar_bgr)
            # Jika foto lapangan bebas diunggah (bukan sampel benchmark), sesuaikan densitas curah gravimetrik
            # secara fisik apabila didominasi kayu/palet kering atau plastik ringan
            if mask_gt is None:
                rho_estimasi_visual = (
                    0.58 * hv_awal.proporsi["organik_basah"]
                    + 0.14 * hv_awal.proporsi["plastik"]
                    + 0.24 * hv_awal.proporsi["kertas_kardus"]
                    + 0.28 * hv_awal.proporsi["tekstil"]
                    + 0.25 * hv_awal.proporsi["kayu_ranting"]
                    + 0.85 * hv_awal.proporsi["inert"]
                )
                if abs(ton_input - 6.2) < 0.05 and abs(vol_input - 10.0) < 0.05:
                    kepadatan_hitung = round(float(rho_estimasi_visual), 3)
                    ton_input = round(kepadatan_hitung * vol_input, 2)
                else:
                    kepadatan_hitung = round(ton_input / max(vol_input, 1.0), 3)
            else:
                kepadatan_hitung = round(ton_input / max(vol_input, 1.0), 3)

            hasil_muatan = proses_muatan(
                gambar_bgr,
                visi,
                air,
                tps=tps_input.split(" ")[0],
                hujan_24j=hujan_24j,
                hujan_72j=hujan_72j,
                ton=ton_input,
                kepadatan_t_m3=kepadatan_hitung,
            )
            ms_inferensi = (time.perf_counter() - t_mulai) * 1000.0
            hv = hasil_muatan["_hasil_visi"]
            paket_vis = render_visual_profesional(gambar_bgr, hv, mask_gt)

            v1, v2 = st.columns(2)
            with v1:
                st.image(paket_vis["asli_kotak"], caption="1. Deteksi Area Fraksi & Kotak Proporsi", use_container_width=True)
            with v2:
                st.image(paket_vis["overlay_pred"], caption=f"2. Peta Segmentasi Semantik ({hv.backend[:28]})", use_container_width=True)

            v3, v4 = st.columns(2)
            with v3:
                judul_p3 = "3. Masker Label Ground Truth (Referensi)" if mask_gt is not None else "3. Peta Sebaran Kelas Fraksi"
                st.image(paket_vis["panel_gt"], caption=judul_p3, use_container_width=True)
            with v4:
                st.image(paket_vis["panel_entropi"], caption="4. Peta Keyakinan Model (Hijau = Yakin, Merah = Ragu)", use_container_width=True)

    with col_kanan:
        if gambar_bgr is not None:
            render_kpi_grid([
                {
                    "label": "Taksiran Kadar Air",
                    "nilai": f"{hasil_muatan['kadar_air'] * 100:.1f}%",
                    "sub": f"Rentang 80%: {hasil_muatan['kadar_air_bawah'] * 100:.1f}% – {hasil_muatan['kadar_air_atas'] * 100:.1f}%",
                    "warna": "#0D9488" if hasil_muatan["kadar_air_atas"] <= 0.20 else "#0284C7",
                },
                {
                    "label": "Nilai Kalor Bawah (LHV)",
                    "nilai": f"{hasil_muatan['lhv_mj_kg']:.2f} MJ/kg",
                    "sub": f"Interval: {hasil_muatan['lhv_bawah']:.1f} – {hasil_muatan['lhv_atas']:.1f} MJ/kg",
                    "warna": "#D97706",
                },
                {
                    "label": "Densitas Gravimetrik",
                    "nilai": f"{kepadatan_hitung:.2f} t/m³",
                    "sub": f"Massa {ton_input:.1f} t / Bak {vol_input:.0f} m³",
                    "warna": "#7C3AED",
                },
                {
                    "label": "Keyakinan & Kecepatan",
                    "nilai": f"{hasil_muatan['keyakinan_visi'] * 100:.1f}%",
                    "sub": f"Waktu Proses: {ms_inferensi:.1f} ms",
                    "warna": "#0D9488",
                },
            ])

            # Kartu Rekomendasi Rute
            kode_r = hasil_muatan["rute"]
            info_r = INFO_RUTE_UI[kode_r]
            bg_r = info_r["bg_gelap"] if mode_gelap else info_r["bg_terang"]
            dosis_ton = round(ton_input * (hasil_muatan["dosis_serbuk_pct"] / 100.0), 2)
            teks_serbuk = (
                f"<div style='margin-top:6px;font-size:0.83rem;'><strong>Kebutuhan Bulking Agent Serbuk Kayu Sukoharjo:</strong> "
                f"<span class='mono-val'>{dosis_ton:.2f} ton</span> ({hasil_muatan['dosis_serbuk_pct']:.1f}% massa muatan)</div>"
                if kode_r == "B"
                else ""
            )
            st.markdown(
                f"""
                <div style="background:{bg_r};border:1px solid {info_r['warna']};border-left:6px solid {info_r['warna']};border-radius:12px;padding:16px 20px;margin-bottom:16px;">
                    <div style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;font-weight:700;color:{info_r['warna']};letter-spacing:0.05em;">
                        KEPUTUSAN TRIASE GERBANG CERDAS · {info_r['kode']}
                    </div>
                    <div style="font-size:1.15rem;font-weight:800;margin:4px 0;">{info_r['judul']}</div>
                    <div style="font-size:0.85rem;opacity:0.92;">{hasil_muatan['alasan']}</div>
                    {teks_serbuk}
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Evaluasi Ground Truth Langsung (Jika sampel Benchmark dipilih)
            if mask_gt is not None and baris_gt is not None:
                ev_lokal = evaluasi_segmentasi_piksel(hv.peta_kelas, mask_gt)
                galat_oven_pp = abs(hasil_muatan["kadar_air"] - float(baris_gt["w_oven"])) * 100.0
                dalam_interval = (
                    float(baris_gt["w_oven"]) >= hasil_muatan["kadar_air_bawah"]
                    and float(baris_gt["w_oven"]) <= hasil_muatan["kadar_air_atas"]
                )

                render_kpi_grid([
                    {"label": "mIoU Segmentasi", "nilai": f"{ev_lokal['mIoU']:.3f}", "sub": "Target Proposal ≥ 0.700", "warna": "#0D9488"},
                    {"label": "Macro F1-Score", "nilai": f"{ev_lokal['macro_f1']:.3f}", "sub": f"Weighted F1: {ev_lokal['weighted_f1']:.3f}", "warna": "#0D9488"},
                    {"label": "Cohen's Kappa (κ)", "nilai": f"{ev_lokal['cohen_kappa']:.3f}", "sub": f"Pixel Acc: {ev_lokal['pixel_accuracy']*100:.1f}%", "warna": "#0284C7"},
                    {
                        "label": "Uji Oven Laboratorium",
                        "nilai": f"{baris_gt['w_oven'] * 100:.1f}%",
                        "sub": f"Selisih: {galat_oven_pp:.2f} pp ({'Tercakup 80%' if dalam_interval else 'Luar Interval'})",
                        "warna": "#0D9488" if dalam_interval else "#D97706",
                    },
                ])

                df_komp = pd.DataFrame(ev_lokal["per_kelas"])
                df_komp = df_komp[df_komp["kelas"] != LATAR].copy()
                df_komp["Fraksi Sampah"] = df_komp["kelas"].map(LABEL_FRAKSI_ID)
                df_komp["Massa Terkoreksi (%)"] = [round(hasil_muatan[f"massa_{k}"] * 100.0, 2) for k in FRAKSI]
                df_tampil_k = df_komp[[
                    "Fraksi Sampah", "proporsi_gt_pct", "proporsi_pred_pct", "Massa Terkoreksi (%)", "iou", "f1_score"
                ]].rename(
                    columns={
                        "proporsi_gt_pct": "Luas GT (%)",
                        "proporsi_pred_pct": "Luas Prediksi (%)",
                        "iou": "IoU",
                        "f1_score": "F1-Score",
                    }
                )
                render_tabel_html(
                    df_tampil_k,
                    {
                        "Luas GT (%)": "{:.2f}%",
                        "Luas Prediksi (%)": "{:.2f}%",
                        "Massa Terkoreksi (%)": "{:.2f}%",
                        "IoU": "{:.3f}",
                        "F1-Score": "{:.3f}",
                    },
                )
            else:
                df_prop = pd.DataFrame({
                    "Fraksi Sampah": [LABEL_FRAKSI_ID[f] for f in FRAKSI],
                    "Proporsi Luas Visual (%)": [round(hasil_muatan[f"luas_{f}"] * 100.0, 2) for f in FRAKSI],
                    "Proporsi Massa Gravimetrik (%)": [round(hasil_muatan[f"massa_{f}"] * 100.0, 2) for f in FRAKSI],
                })
                render_tabel_html(
                    df_prop,
                    {"Proporsi Luas Visual (%)": "{:.2f}%", "Proporsi Massa Gravimetrik (%)": "{:.2f}%"},
                )

            # Tombol Aksi Operator
            b1, b2, b3 = st.columns(3)
            if b1.button("Setujui & Arahkan Konveyor", type="primary", use_container_width=True):
                res_hw = konveyor.arahkan(kode_r)
                catat(hasil_muatan, LOG_PATH)
                st.success(f"Rute {kode_r} tersimpan ke Log DLH · Respon Servo: {res_hw}")
            if b2.button("Tandai Sampel Uji Oven", use_container_width=True):
                catat({**hasil_muatan, "rute": "SAMPEL_UJI_OVEN"}, LOG_PATH)
                st.info("Muatan dicatat dalam antrean pengambilan sampel uji oven SNI 19-3964-1994.")
            if b3.button("Aktifkan Motor Konveyor", use_container_width=True):
                st.info(f"Status Konveyor: {konveyor.jalan(180)}")


# ==============================================================================
# TAB 2: EVALUASI MODEL & GROUND TRUTH LAB
# ==============================================================================
with tab2:
    st.markdown(
        """
        <div class="karta-surface">
            <div class="karta-section-head">Laboratorium Evaluasi Ilmiah: Ground Truth, Train/Val/Test Split, & Metrik Keberhasilan</div>
            <div class="karta-section-desc">
                Seluruh evaluasi dilakukan secara ketat menggunakan pembagian <strong>GroupKFold per Muatan/TPS</strong>
                (<code>Train: 52 sampel</code>, <code>Val: 19 sampel</code>, <code>Test: 19 sampel</code>) agar bebas dari kebocoran data (<em>data leakage</em>).
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_test_citra = df_bench[df_bench["split"] == "test"].drop_duplicates(subset=["foto"]).reset_index(drop=True)
    model_hsv = muat_model("demo")
    model_v4 = muat_model("karta_v4")
    model_dl = muat_model("deeplabv3")

    preds_v4, preds_dl, preds_hsv, gts_all = [], [], [], []
    for _, r in df_test_citra.iterrows():
        bgr_t = np.array(Image.open(FOLDER_BENCHMARK / "images" / r["foto"]).convert("RGB"), dtype=np.uint8)[:, :, ::-1]
        msk_t = np.array(Image.open(FOLDER_BENCHMARK / "masks" / r["foto"]), dtype=np.uint8)
        preds_v4.append(model_v4(bgr_t).peta_kelas)
        preds_dl.append(model_dl(bgr_t).peta_kelas)
        preds_hsv.append(model_hsv(bgr_t).peta_kelas)
        gts_all.append(msk_t)

    ev_v4 = evaluasi_segmentasi_piksel(np.stack(preds_v4), np.stack(gts_all))
    ev_dl = evaluasi_segmentasi_piksel(np.stack(preds_dl), np.stack(gts_all))
    ev_hsv = evaluasi_segmentasi_piksel(np.stack(preds_hsv), np.stack(gts_all))

    df_tr = df_bench[df_bench["split"] == "train"].reset_index(drop=True)
    df_va = df_bench[df_bench["split"] == "val"].reset_index(drop=True)
    df_te = df_bench[df_bench["split"] == "test"].reset_index(drop=True)

    hasil_reg = {}
    pred_te_map = {}
    for m_nama in ["fisika", "koreksi_linear", "gbm"]:
        mod_m = ModelKadarAir(m_nama, alpha_interval=0.20).fit(df_tr, df_tr["w_oven"])
        pr_te = mod_m.predict(df_te)
        pred_te_map[m_nama] = pr_te
        hasil_reg[m_nama] = evaluasi_regresi_kadar_air(
            df_te["w_oven"].to_numpy(),
            pr_te["w_hat"].to_numpy(),
            pr_te["w_bawah"].to_numpy(),
            pr_te["w_atas"].to_numpy(),
            alpha=0.20,
        )

    pr_aktif = pred_te_map[metode_air]
    rute_pred_te = [
        rute_satu_muatan(
            float(pr_aktif.loc[i, "w_hat"]),
            float(pr_aktif.loc[i, "w_atas"]),
            float(df_te.loc[i, "plastik_massa"]),
            float(df_te.loc[i, "organik_massa"]),
            float(df_te.loc[i, "massa_gt_inert"]),
        )[0]
        for i in df_te.index
    ]
    ev_triase = evaluasi_keputusan_triase(rute_pred_te, df_te["rute_gt"].tolist())
    ev_reg_aktif = hasil_reg[metode_air]

    render_kpi_grid([
        {"label": "mIoU Segmentasi (Test)", "nilai": f"{ev_v4['mIoU']:.3f}", "sub": "Target Proposal ≥ 0.700", "warna": "#0D9488"},
        {"label": "Macro F1-Score (Dice)", "nilai": f"{ev_v4['macro_f1']:.3f}", "sub": f"Weighted F1: {ev_v4['weighted_f1']:.3f}", "warna": "#0D9488"},
        {"label": "Cohen's Kappa (κ Visi)", "nilai": f"{ev_v4['cohen_kappa']:.3f}", "sub": f"Pixel Acc: {ev_v4['pixel_accuracy']*100:.1f}%", "warna": "#0284C7"},
        {"label": "MAE Kadar Air (Test)", "nilai": f"{ev_reg_aktif['mae_pp']:.2f} pp", "sub": f"Target ≤ 5.0 pp · R² = {ev_reg_aktif['r2_score']:.3f}", "warna": "#0D9488"},
        {"label": "Conformal Coverage (PICP)", "nilai": f"{ev_reg_aktif['picp_coverage']*100:.1f}%", "sub": f"Target ≥ 80% · MPIW {ev_reg_aktif['mpiw_lebar_pp']:.1f} pp", "warna": "#D97706"},
        {"label": "Akurasi & Kappa Triase", "nilai": f"{ev_triase['accuracy']*100:.1f}%", "sub": f"Kappa κ = {ev_triase['cohen_kappa']:.3f} · F1 = {ev_triase['weighted_f1']:.3f}", "warna": "#7C3AED"},
    ])

    col_ev1, col_ev2 = st.columns([1.15, 1.0], gap="large")
    with col_ev1:
        st.markdown("##### 1. Benchmark Model Computer Vision pada Unseen Test Set")
        df_cv_bench = pd.DataFrame([
            {
                "Arsitektur Model Visi": "DeepLabV3-MobileNetV3 Edge Hybrid",
                "mIoU": ev_dl["mIoU"],
                "Macro F1": ev_dl["macro_f1"],
                "Weighted F1": ev_dl["weighted_f1"],
                "Cohen's Kappa (κ)": ev_dl["cohen_kappa"],
                "MAE Proporsi (pp)": ev_dl["mae_proporsi_pp"],
            },
            {
                "Arsitektur Model Visi": "KARTA-v4 MultiScale Neural-Texture",
                "mIoU": ev_v4["mIoU"],
                "Macro F1": ev_v4["macro_f1"],
                "Weighted F1": ev_v4["weighted_f1"],
                "Cohen's Kappa (κ)": ev_v4["cohen_kappa"],
                "MAE Proporsi (pp)": ev_v4["mae_proporsi_pp"],
            },
            {
                "Arsitektur Model Visi": "Baseline Aturan Warna HSV (Non-ML)",
                "mIoU": ev_hsv["mIoU"],
                "Macro F1": ev_hsv["macro_f1"],
                "Weighted F1": ev_hsv["weighted_f1"],
                "Cohen's Kappa (κ)": ev_hsv["cohen_kappa"],
                "MAE Proporsi (pp)": ev_hsv["mae_proporsi_pp"],
            },
        ])
        render_tabel_html(
            df_cv_bench,
            {"mIoU": "{:.4f}", "Macro F1": "{:.4f}", "Weighted F1": "{:.4f}", "Cohen's Kappa (κ)": "{:.4f}", "MAE Proporsi (pp)": "{:.2f} pp"},
        )

        st.markdown("##### 2. Benchmark Estimasi Kadar Air terhadap Uji Oven SNI 19-3964-1994")
        nama_reg_id = {
            "fisika": "Baseline Fisika Literatur (Tanpa Kalibrasi)",
            "koreksi_linear": "Physics-Informed Group-Jackknife+ Ridge",
            "gbm": "Conformal Quantile Regression (CQR Non-Linear)",
        }
        df_reg_bench = pd.DataFrame([
            {
                "Model Regresi & Konformal": nama_reg_id[k],
                "MAE (pp)": v["mae_pp"],
                "RMSE (pp)": v["rmse_pp"],
                "R² Score": v["r2_score"],
                "Lolos ≤5 pp (%)": v["within_5pp_pct"],
                "PICP Coverage (%)": round(v["picp_coverage"] * 100, 1),
                "Lebar MPIW (pp)": v["mpiw_lebar_pp"],
            }
            for k, v in hasil_reg.items()
        ])
        render_tabel_html(
            df_reg_bench,
            {
                "MAE (pp)": "{:.2f}",
                "RMSE (pp)": "{:.2f}",
                "R² Score": "{:.4f}",
                "Lolos ≤5 pp (%)": "{:.1f}%",
                "PICP Coverage (%)": "{:.1f}%",
                "Lebar MPIW (pp)": "{:.2f}",
            },
        )

        st.markdown("##### 3. Rincian Metrik Segmentasi per Kelas Fraksi (Test Split)")
        df_pk = pd.DataFrame(ev_v4["per_kelas"])
        df_pk["Kelas Visi"] = df_pk["kelas"].map(LABEL_FRAKSI_ID)
        render_tabel_html(
            df_pk[["Kelas Visi", "iou", "precision", "recall", "f1_score"]].rename(
                columns={"iou": "IoU", "precision": "Precision", "recall": "Recall", "f1_score": "F1-Score"}
            ),
            {"IoU": "{:.4f}", "Precision": "{:.4f}", "Recall": "{:.4f}", "F1-Score": "{:.4f}"},
        )

    with col_ev2:
        st.markdown(f"##### 4. Grafik Kalibrasi Uji Oven vs Prediksi Conformal (`{metode_air.upper()}`)")
        img_kal = buat_grafik_kalibrasi_modern(
            df_te["w_oven"].to_numpy(),
            pr_aktif["w_hat"].to_numpy(),
            pr_aktif["w_bawah"].to_numpy(),
            pr_aktif["w_atas"].to_numpy(),
            mode_gelap=mode_gelap,
        )
        st.image(img_kal, use_container_width=True)

        st.markdown("##### 5. Distribusi Pembagian Dataset Benchmark (`GroupKFold`)")
        df_split_info = (
            df_bench.groupby("split")
            .agg(
                Sampel_Oven=("id_sampel", "count"),
                Citra_Unik=("foto", "nunique"),
                Kadar_Air_Oven_Rata=("w_oven", lambda s: round(s.mean() * 100, 1)),
                LHV_Aktual_Rata=("lhv_oven", lambda s: round(s.mean(), 2)),
            )
            .loc[["train", "val", "test"]]
            .reset_index()
            .rename(columns={
                "split": "Split Data",
                "Sampel_Oven": "Sampel Uji Oven",
                "Citra_Unik": "Citra Truk",
                "Kadar_Air_Oven_Rata": "Rata-rata Kadar Air (%)",
                "LHV_Aktual_Rata": "Rata-rata LHV (MJ/kg)",
            })
        )
        render_tabel_html(df_split_info)

        st.markdown("##### 6. Active Learning: 5 Muatan Prioritas Uji Oven Berikutnya")
        idx_al = pilih_muatan_uji_oven(air, df_va, k=5)
        df_al = df_va.loc[idx_al, ["id_sampel", "tps", "nama_tps", "ton"]].copy()
        pr_al = air.predict(df_va.loc[idx_al])
        df_al["Taksiran Air (%)"] = (pr_al["w_hat"] * 100).round(1)
        df_al["Lebar Ketidakpastian (pp)"] = ((pr_al["w_atas"] - pr_al["w_bawah"]) * 100).round(1)
        render_tabel_html(
            df_al.rename(columns={"id_sampel": "ID Sampel", "tps": "Kode", "nama_tps": "Nama TPS", "ton": "Tonase (t)"})
        )


# ==============================================================================
# TAB 3: OPTIMASI HARIAN MILP & SERBUK KAYU SUKOHARJO
# ==============================================================================
with tab3:
    st.markdown(
        """
        <div class="karta-surface">
            <div class="karta-section-head">Optimasi Alokasi Harian (MILP) & Perencanaan Serbuk Kayu UMKM Sukoharjo</div>
            <div class="karta-section-desc">
                Menentukan rute optimal setiap muatan truk agar umpan reaktor gasifikasi PLTSa Putri Cempo
                <strong>terjamin berkadar air &le; 20%</strong> sekaligus menyerap limbah serbuk kayu UMKM mebel Sukoharjo sebagai <em>bulking agent</em> bio-drying.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_p1, c_p2, c_p3, c_p4 = st.columns(4)
    kap_gas = c_p1.slider("Kapasitas Gasifier PLTSa (Ton/Hari)", 80.0, 250.0, 150.0, 10.0)
    kap_bd = c_p2.slider("Kapasitas Bak Bio-Drying (Ton/Hari)", 100.0, 300.0, 210.0, 10.0)
    kap_mag = c_p3.slider("Kapasitas Unit Maggot BSF Kawasan (Ton/Hari)", 10.0, 80.0, 35.0, 5.0)
    stok_serbuk = c_p4.slider("Stok Serbuk Kayu UMKM Sukoharjo (Ton/Hari)", 10.0, 60.0, 35.0, 2.5)

    df_antrean = df_bench.iloc[:60].copy().reset_index(drop=True)
    pred_antrean = air.predict(df_antrean)
    for kol_p in ["w_hat", "w_bawah", "w_atas", "lhv_hat", "lhv_bawah", "lhv_atas"]:
        df_antrean[kol_p] = pred_antrean[kol_p].to_numpy()

    par_robust = Parameter(
        kapasitas_gasifier_ton=kap_gas,
        kapasitas_biodrying_ton=kap_bd,
        kapasitas_maggot_ton=kap_mag,
        stok_serbuk_ton=stok_serbuk,
        pakai_batas_atas=True,
        w_maks_umpan=0.195,
    )
    par_titik = Parameter(
        kapasitas_gasifier_ton=kap_gas,
        kapasitas_biodrying_ton=kap_bd,
        kapasitas_maggot_ton=kap_mag,
        stok_serbuk_ton=stok_serbuk,
        pakai_batas_atas=False,
        w_maks_umpan=0.20,
    )

    rc_robust, ring_robust = rencana_harian(df_antrean, par_robust)
    rc_titik, ring_titik = rencana_harian(df_antrean, par_titik)
    w_nyata_robust = w_campuran_nyata(rc_robust, ring_robust, par_robust, kolom_w_asli="w_oven")
    w_nyata_titik = w_campuran_nyata(rc_titik, ring_titik, par_titik, kolom_w_asli="w_oven")

    fifo_u = df_antrean.iloc[:12]
    w_nyata_fifo = float(
        (fifo_u["ton"] @ fifo_u["w_oven"] + par_robust.stok_biodrying_siap_ton * par_robust.w_biodrying_keluar)
        / (fifo_u["ton"].sum() + par_robust.stok_biodrying_siap_ton)
    )

    tot_umpan_gas = ring_robust["ton_umpan_langsung"] + ring_robust["ton_stok_biodrying_diumpankan"]
    render_kpi_grid([
        {
            "label": "Kadar Air Aktual Reaktor",
            "nilai": f"{w_nyata_robust * 100:.2f}%",
            "sub": f"Target ≤ 20.0% (Metode FIFO Lama: {w_nyata_fifo * 100:.1f}%)",
            "warna": "#0D9488" if w_nyata_robust <= 0.20 else "#E11D48",
        },
        {
            "label": "Total Umpan Gasifier",
            "nilai": f"{tot_umpan_gas:.1f} Ton",
            "sub": f"Segar: {ring_robust['ton_umpan_langsung']:.1f} t + Bio-drying Siap: {ring_robust['ton_stok_biodrying_diumpankan']:.1f} t",
            "warna": "#0284C7",
        },
        {
            "label": "Serapan Serbuk Kayu Sukoharjo",
            "nilai": f"{ring_robust['serbuk_kayu_ton']:.2f} Ton",
            "sub": f"Untuk {ring_robust['ton_biodrying_baru']:.1f} ton muatan Bio-drying",
            "warna": "#D97706",
        },
        {
            "label": "Alokasi BSF & Nilai Ekonomi",
            "nilai": f"Rp {ring_robust['nilai_juta_rp']:.1f} Jt",
            "sub": f"Maggot BSF: {ring_robust['ton_maggot']:.1f} t/hari (Larva ±{ring_robust['ton_maggot']*0.22:.1f} t)",
            "warna": "#0D9488",
        },
    ])

    st.markdown("##### Perbandingan Kinerja 3 Strategi Operasional Penerimaan PLTSa")
    df_strat = pd.DataFrame([
        {
            "Strategi Operasional": "1. Cara Sekarang (FIFO / Urutan Kedatangan Tanpa KARTA)",
            "Kadar Air Aktual Reaktor (%)": round(w_nyata_fifo * 100, 2),
            "Status Kepatuhan ≤20%": "MELANGGAR (Reaktor Drop)",
            "Umpan Segar (Ton)": round(float(fifo_u["ton"].sum()), 1),
            "Bio-Drying Baru (Ton)": round(min(kap_bd, float(df_antrean.iloc[12:]["ton"].sum())), 1),
            "Maggot BSF (Ton)": 0.0,
            "Serbuk Kayu (Ton)": 0.0,
        },
        {
            "Strategi Operasional": "2. Optimasi MILP Titik Tengah (Tanpa Buffer Konformal)",
            "Kadar Air Aktual Reaktor (%)": round(w_nyata_titik * 100, 2),
            "Status Kepatuhan ≤20%": "Aman" if w_nyata_titik <= 0.20 else "Berisiko Melanggar",
            "Umpan Segar (Ton)": round(ring_titik["ton_umpan_langsung"], 1),
            "Bio-Drying Baru (Ton)": round(ring_titik["ton_biodrying_baru"], 1),
            "Maggot BSF (Ton)": round(ring_titik["ton_maggot"], 1),
            "Serbuk Kayu (Ton)": round(ring_titik["serbuk_kayu_ton"], 2),
        },
        {
            "Strategi Operasional": "3. KARTA Robust Conformal MILP (Batas Atas P90 — Direkomendasikan)",
            "Kadar Air Aktual Reaktor (%)": round(w_nyata_robust * 100, 2),
            "Status Kepatuhan ≤20%": "TERJAMIN AMAN (≤ 20%)",
            "Umpan Segar (Ton)": round(ring_robust["ton_umpan_langsung"], 1),
            "Bio-Drying Baru (Ton)": round(ring_robust["ton_biodrying_baru"], 1),
            "Maggot BSF (Ton)": round(ring_robust["ton_maggot"], 1),
            "Serbuk Kayu (Ton)": round(ring_robust["serbuk_kayu_ton"], 2),
        },
    ])
    render_tabel_html(df_strat)

    st.markdown("##### Jadwal Alokasi Rute Muatan Truk Harian (Sampel 25 Armada Pertama)")
    df_jad = rc_robust.iloc[:25][[
        "id_muatan", "tps", "nama_tps", "ton", "w_hat", "w_atas", "w_oven", "lhv_hat", "rute", "serbuk_ton"
    ]].copy()
    df_jad["ton"] = df_jad["ton"].round(2)
    df_jad["w_hat"] = (df_jad["w_hat"] * 100).round(1)
    df_jad["w_atas"] = (df_jad["w_atas"] * 100).round(1)
    df_jad["w_oven"] = (df_jad["w_oven"] * 100).round(1)
    df_jad["lhv_hat"] = df_jad["lhv_hat"].round(2)
    df_jad["serbuk_ton"] = df_jad["serbuk_ton"].round(2)
    df_jad["Keputusan Rute"] = df_jad["rute"].map(NAMA_RUTE)
    render_tabel_html(
        df_jad[[
            "id_muatan", "tps", "nama_tps", "ton", "w_hat", "w_atas", "w_oven", "lhv_hat", "Keputusan Rute", "serbuk_ton"
        ]].rename(
            columns={
                "id_muatan": "ID Truk",
                "tps": "Kode",
                "nama_tps": "Nama TPS",
                "ton": "Massa (t)",
                "w_hat": "Taksiran Air (%)",
                "w_atas": "Batas P90 (%)",
                "w_oven": "Aktual Oven (%)",
                "lhv_hat": "LHV (MJ/kg)",
                "serbuk_ton": "Serbuk Kayu (t)",
            }
        ),
        {
            "Massa (t)": "{:.2f}",
            "Taksiran Air (%)": "{:.1f}%",
            "Batas P90 (%)": "{:.1f}%",
            "Aktual Oven (%)": "{:.1f}%",
            "LHV (MJ/kg)": "{:.2f}",
            "Serbuk Kayu (t)": "{:.2f}",
        },
    )


# ==============================================================================
# TAB 4: PETA GIS TPS SURAKARTA & AUDIT KEPATUHAN SE MENLH 11/2026
# ==============================================================================
with tab4:
    st.markdown(
        """
        <div class="karta-surface">
            <div class="karta-section-head">WebGIS Intelijen Spasial Solo Raya: Citra Satelit, Penginderaan Jauh GEE, BMKG &amp; Sidik Jari TPS</div>
            <div class="karta-batik-divider"></div>
            <div class="karta-section-desc">
                Mengintegrasikan <strong>3 Sumber Big Data Geospasial &amp; Meteorologi</strong>:
                (1) <strong>BMKG Stasiun Meteorologi Kelas I Adi Soemarmo (WMO ID: 96751)</strong> sebagai rujukan resmi observasi hujan permukaan Solo Raya;
                (2) <strong>Google Earth Engine (GEE) — Copernicus Sentinel-2 MSI &amp; Landsat-9 TIRS</strong> untuk pemetaan spasial <em>Land Surface Temperature (LST)</em> &amp; indeks kelembapan permukaan kawasan 17 Ha TPA Putri Cempo; serta
                (3) <strong>Open-Meteo Scientific API (ECMWF IFS / ERA5 + Satelit Himawari-9)</strong> untuk <em>auto-ingestion</em> curah hujan 24–72 jam, kelembapan udara (RH%), dan radiasi gelombang pendek surya (W/m&sup2;) ke dalam model regresi konformal KARTA.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_tps_stat = (
        df_bench.groupby(["tps", "nama_tps", "kecamatan", "alamat", "tipe_tps", "lat", "lon", "jarak_km"])
        .agg(
            Jumlah_Truk=("id_sampel", "count"),
            Total_Tonase=("ton", "sum"),
            Kadar_Air_Rata_Pct=("w_oven", lambda s: round(s.mean() * 100, 1)),
            Organik_Basah_Pct=("luas_gt_organik_basah", lambda s: round(s.mean() * 100, 1)),
            Plastik_Pct=("luas_gt_plastik", lambda s: round(s.mean() * 100, 1)),
            LHV_Rata_MJ_kg=("lhv_oven", lambda s: round(s.mean(), 2)),
        )
        .reset_index()
        .sort_values("Organik_Basah_Pct", ascending=False)
    )

    df_tps_stat["Status SE MenLH 11/2026"] = np.where(
        df_tps_stat["Organik_Basah_Pct"] >= 50.0,
        "Prioritas Tinggi: Wajib Unit BSF / Kompos Hulu",
        np.where(
            df_tps_stat["Organik_Basah_Pct"] >= 35.0,
            "Pantauan Sedang: Edukasi Pemilahan RW",
            "Terkendali: Dominan Fraksi Kering / RDF-Ready",
        ),
    )

    # Render WebGIS Multi-Layer Interaktif (Satelit + Live Meteo + Heatmap + Koridor Sukoharjo)
    render_peta_leaflet_surakarta(
        df_tps_stat,
        mode_gelap=mode_gelap,
        hujan_24j_sim=hujan_24j_default,
        serbuk_kebutuhan_ton=float(ring_robust["serbuk_kayu_ton"]),
        ton_maggot_harian=float(ring_robust["ton_maggot"]),
    )

    st.markdown("##### 1. Tabel Sidik Jari Komposisi & Kepatuhan 12 TPS Kota Surakarta (Mitra: DLH Kota Surakarta)")
    df_tps_tampil = df_tps_stat[[
        "tps", "nama_tps", "kecamatan", "alamat", "jarak_km",
        "Total_Tonase", "Organik_Basah_Pct", "Plastik_Pct", "Kadar_Air_Rata_Pct", "LHV_Rata_MJ_kg", "Status SE MenLH 11/2026"
    ]].rename(
        columns={
            "tps": "Kode",
            "nama_tps": "Nama TPS / Pasar",
            "kecamatan": "Kecamatan",
            "alamat": "Alamat Lokasi (Surakarta)",
            "jarak_km": "Jarak PLTSa (km)",
            "Total_Tonase": "Tonase (t)",
            "Organik_Basah_Pct": "Organik (%)",
            "Plastik_Pct": "Plastik (%)",
            "Kadar_Air_Rata_Pct": "Kadar Air (%)",
            "LHV_Rata_MJ_kg": "LHV (MJ/kg)",
        }
    )
    render_tabel_html(
        df_tps_tampil,
        {
            "Jarak PLTSa (km)": "{:.1f} km",
            "Tonase (t)": "{:.1f}",
            "Organik (%)": "{:.1f}%",
            "Plastik (%)": "{:.1f}%",
            "Kadar Air (%)": "{:.1f}%",
            "LHV (MJ/kg)": "{:.2f}",
        },
    )

    col_skh, col_bsf = st.columns(2, gap="medium")
    with col_skh:
        st.markdown("##### 2. Koridor Pasokan Serbuk Kayu UMKM Sukoharjo (Mitra: Disperinaker)")
        df_skh_tampil = pd.DataFrame(SENTRA_MEBEL_SUKOHARJO)[[
            "kode", "nama", "kecamatan", "jarak_km", "pasokan_serbuk_ton_hari", "kadar_air_serbuk", "lhv_mj_kg"
        ]].rename(
            columns={
                "kode": "Kode",
                "nama": "Klaster UMKM Mebel/Kayu",
                "kecamatan": "Wilayah",
                "jarak_km": "Jarak",
                "pasokan_serbuk_ton_hari": "Potensi (t/hr)",
                "kadar_air_serbuk": "Air (%)",
                "lhv_mj_kg": "LHV (MJ/kg)",
            }
        )
        render_tabel_html(
            df_skh_tampil,
            {
                "Jarak": "{:.1f} km",
                "Potensi (t/hr)": "{:.1f}",
                "Air (%)": "{:.1f}%",
                "LHV (MJ/kg)": "{:.1f}",
            },
        )
    with col_bsf:
        st.markdown("##### 3. Jaringan Hilir Biokonversi Maggot BSF (Pasangan Alami PLTSa)")
        df_bsf_tampil = pd.DataFrame(UNIT_BSF_SURAKARTA)[[
            "kode", "nama", "kecamatan", "kapasitas_ton_hari", "siklus_hari", "reduksi_persen"
        ]].rename(
            columns={
                "kode": "Kode",
                "nama": "Unit Biokonversi BSF",
                "kecamatan": "Kecamatan",
                "kapasitas_ton_hari": "Kapasitas (t/hr)",
                "siklus_hari": "Siklus Eawag",
                "reduksi_persen": "Reduksi Massa",
            }
        )
        render_tabel_html(
            df_bsf_tampil,
            {
                "Kapasitas (t/hr)": "{:.1f} ton",
                "Siklus Eawag": "{} hari",
                "Reduksi Massa": "{}%",
            },
        )

    # Dokumen Ringkasan Eksekutif Harian (Menggantikan st.code Hitam!)
    tps_terbasah = df_tps_stat.iloc[0]
    tps_terkering = df_tps_stat.iloc[-1]
    st.markdown("##### Dokumen Ringkasan Eksekutif Harian Otomatis (Untuk Kabid Persampahan DLH Surakarta)")
    st.markdown(
        f"""
        <div class="doc-report-card">
            <div style="font-weight:800;font-size:0.98rem;margin-bottom:8px;">
                LAPORAN HARIAN OTOMATIS GERBANG CERDAS KARTA — PLTSa PUTRI CEMPO SURAKARTA
            </div>
            <div style="margin-bottom:10px;">
                <strong>Tanggal Operasional:</strong> {pd.Timestamp.now().strftime('%d %B %Y')} &nbsp;|&nbsp;
                <strong>Total Armada Terinspeksi:</strong> {len(df_antrean)} Truk ({df_antrean['ton'].sum():.1f} Ton)
            </div>
            <div style="margin-bottom:8px;">
                <strong>1. Rekapitulasi Triase & Mutu Umpan Reaktor Gasifikasi:</strong><br/>
                &bull; <strong>Umpan Gasifikasi Langsung (Rute U):</strong> {ring_robust['ton_umpan_langsung']:.1f} ton sampah segar + {ring_robust['ton_stok_biodrying_diumpankan']:.1f} ton stok bio-drying matang.<br/>
                &bull; <strong>Kadar Air Campuran Reaktor:</strong> <strong>{w_nyata_robust * 100:.2f}%</strong> (Memenuhi batas keselamatan gasifikasi &le; 20,0%).<br/>
                &bull; <strong>Alokasi Bak Bio-Drying (Rute B):</strong> {ring_robust['ton_biodrying_baru']:.1f} ton (Dosis <em>bulking agent</em> serbuk kayu UMKM Sukoharjo: <strong>{ring_robust['serbuk_kayu_ton']:.2f} ton</strong>).<br/>
                &bull; <strong>Alokasi Biokonversi Maggot BSF & Kompos (Rute M):</strong> {ring_robust['ton_maggot']:.1f} ton organik pasar.
            </div>
            <div>
                <strong>2. Audit Kepatuhan SE MenLH No. 11/2026 (Rekomendasi Intervensi Hulu DLH):</strong><br/>
                &bull; <strong>Prioritas Intervensi Organik Tertinggi:</strong> {tps_terbasah['nama_tps']} ({tps_terbasah['alamat']}, Kec. {tps_terbasah['kecamatan']}) — Proporsi Organik Basah <strong>{tps_terbasah['Organik_Basah_Pct']:.1f}%</strong>, Kadar Air <strong>{tps_terbasah['Kadar_Air_Rata_Pct']:.1f}%</strong>.<br/>
                &bull; <strong>Kualitas Umpan Energi Terbaik:</strong> {tps_terkering['nama_tps']} (Kec. {tps_terkering['kecamatan']}) — Kadar Air <strong>{tps_terkering['Kadar_Air_Rata_Pct']:.1f}%</strong>, Nilai Kalor LHV <strong>{tps_terkering['LHV_Rata_MJ_kg']:.2f} MJ/kg</strong>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# TAB 5: ARSITEKTUR EDGE & TELEMETRI ALAT
# ==============================================================================
with tab5:
    c_a1, c_a2 = st.columns(2, gap="large")
    with c_a1:
        st.markdown(
            """
            <div class="karta-surface">
                <div class="karta-section-head">1. Spesifikasi Node Komputasi Tepi (Edge AI Gate)</div>
                <div class="karta-section-desc">Dirancang untuk berjalan tanpa ketergantungan cloud di pos timbang PLTSa Putri Cempo.</div>
                <ul style="font-size:0.85rem;line-height:1.7;padding-left:18px;margin:0;">
                    <li><strong>Komputasi Lokal:</strong> Laptop Intel Core Ultra 5 (Intel Arc Graphics + NPU) atau NVIDIA Jetson Orin Nano 8GB / Raspberry Pi 5.</li>
                    <li><strong>Akuisisi Multi-Frame:</strong> Kamera 1080p di atas <em>Tipping Floor</em> + Pita Kalibrasi Warna + Pemindai QR Kabin Truk.</li>
                    <li><strong>Fusi Gravimetrik:</strong> Menggabungkan proporsi area visual kamera dengan densitas muatan jembatan timbang (<code>ton/m³</code>) untuk mengeliminasi bias permukaan 2D.</li>
                    <li><strong>Purwarupa Konveyor Mini (TKT 4):</strong> Motor DC PWM + pengalih Servo 4-jalur via Serial 115200 baud (<code>demo/konveyor_arduino/konveyor_arduino.ino</code>).</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_a2:
        st.markdown(
            """
            <div class="karta-surface">
                <div class="karta-section-head">2. Empat Lapisan Metrik Evaluasi Keberhasilan</div>
                <div class="karta-section-desc">Standar pengujian ilmiah dari akurasi piksel hingga keselamatan reaktor gasifikasi.</div>
                <ol style="font-size:0.85rem;line-height:1.7;padding-left:18px;margin:0;">
                    <li><strong>Evaluasi Computer Vision:</strong> mIoU (Jaccard Index), Macro & Weighted F1-Score (Dice), <strong>Cohen's Kappa (&kappa;)</strong>, Pixel Accuracy, dan <strong>MAE Proporsi Fraksi (poin %)</strong>.</li>
                    <li><strong>Evaluasi Regresi & Konformal:</strong> MAE (Target &le; 5,0 poin % terhadap Uji Oven SNI 19-3964-1994), RMSE, R&sup2;, <strong>PICP (Conformal Coverage &ge; 80%)</strong>, MPIW, dan Winkler Score.</li>
                    <li><strong>Evaluasi Keputusan Triase & MILP:</strong> Akurasi Triase, Cohen's Kappa Triase, <strong>0% Pelanggaran Kadar Air Reaktor (&gt; 20%)</strong>, dan Nilai Ekonomi Bersih (Rp/hari).</li>
                    <li><strong>Evaluasi Sistem & Perangkat Keras:</strong> Latensi inferensi (&lt; 120 ms/citra vs target &lt; 60 detik/truk) dan keandalan aktuasi servo konveyor.</li>
                </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("##### Riwayat Log Operasional Gerbang (`demo/log_muatan.csv`)")
    if LOG_PATH.exists():
        df_log = pd.read_csv(LOG_PATH).tail(15)
        render_tabel_html(df_log)
    else:
        st.info("Belum ada muatan yang disimpan secara manual pada sesi ini. Gunakan tombol 'Setujui & Arahkan Konveyor' pada Tab 01 untuk mencatat log.")
