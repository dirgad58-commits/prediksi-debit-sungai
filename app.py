# -*- coding: utf-8 -*-
"""
Pemantau Debit Sungai - dashboard prediksi debit 1 hari ke depan dan risiko banjir.

Menu:
  1. Beranda risiko
  2. Eksplorasi data
  3. Prediksi debit (input pengguna + simpan ke database)
  4. Performa model dan riwayat prediksi

Jalankan:  streamlit run app.py
"""
import json
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
# Penyimpanan berbasis CSV mandiri (tanpa dependensi database eksternal)

warnings.filterwarnings("ignore", category=UserWarning)

st.set_page_config(
    page_title="Pemantau Debit Sungai",
    page_icon=":material/water:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# 1. Konstanta tampilan
# ----------------------------------------------------------------------------
FONT = "Public Sans, Segoe UI, Helvetica, Arial, sans-serif"
INK = "#0E2A3A"
TEAL = "#12708A"
MUTED = "#5F7080"
GRID = "#E6EBEE"
SLATE = "#8FA0AD"

STATUS = ["Normal", "Waspada", "Siaga", "Awas"]
WARNA_STATUS = {"Normal": "#2F7F5F", "Waspada": "#C79A2B",
                "Siaga": "#D1701F", "Awas": "#B3261E"}
BADGE_BG = {"Normal": "#E4F1EB", "Waspada": "#FAF0D6",
            "Siaga": "#FBE6D4", "Awas": "#F8DEDB"}
BADGE_FG = {"Normal": "#1F5E45", "Waspada": "#7A5A0C",
            "Siaga": "#8E4510", "Awas": "#8A1C15"}
KETERANGAN_STATUS = {
    "Normal": "Debit prediksi berada di bawah ambang Waspada (P75) kota ini.",
    "Waspada": "Debit prediksi melewati ambang Waspada (P75). Pantau perkembangan hujan.",
    "Siaga": "Debit prediksi melewati ambang Siaga (P90). Tinjau kesiapan penanganan.",
    "Awas": "Debit prediksi melewati ambang Awas (P95). Ini kondisi tertinggi menurut data latih.",
}
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
         "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

IKON = {
    "waves": '<path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "rain": '<path d="M4 14.9A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 2.5 8.2"/><path d="M16 14v6"/><path d="M8 14v6"/><path d="M12 16v6"/>',
    "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
    "chart": '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
    "gauge": '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
    "layers": '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 12 10 5 10-5"/><path d="m2 17 10 5 10-5"/>',
}


def ikon(nama, ukuran=20):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ukuran}" height="{ukuran}" '
            f'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{IKON[nama]}</svg>')


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Public+Sans:wght@400;500;600;700&display=swap');

:root{
  --ink: #0F172A;
  --teal: #0D768A;
  --teal-dark: #0A5A6A;
  --teal-light: #E6F4F7;
  --muted: #64748B;
  --line: #E2E8F0;
  --line-light: #F1F5F9;
  --paper: #F8FAFC;
  --card-bg: #FFFFFF;
  --card-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.05), 0 1px 2px -1px rgba(15, 23, 42, 0.05);
  --card-shadow-hover: 0 4px 6px -1px rgba(15, 23, 42, 0.07), 0 2px 4px -2px rgba(15, 23, 42, 0.05);
}

html, body, .stApp, .stMarkdown, .stMarkdown p, label, input, textarea, button,
[data-testid="stWidgetLabel"] p, [data-baseweb="select"] div, [data-baseweb="tab"] p,
h1, h2, h3, h4, h5, h6, table, td, th, li{
  font-family: 'Plus Jakarta Sans', 'Public Sans', 'Segoe UI', -apple-system, sans-serif !important;
  -webkit-font-smoothing: antialiased;
}
span[data-testid="stIconMaterial"]{font-family:'Material Symbols Rounded' !important;}

.stApp{
  background-color: var(--paper) !important;
  color: var(--ink);
}

.block-container{
  max-width: 1320px;
  padding-top: 2rem;
  padding-bottom: 3.5rem;
}

#MainMenu, footer, [data-testid="stAppDeployButton"], [data-testid="stToolbar"]{
  visibility: hidden;
  height: 0;
}
[data-testid="stHeader"]{background: transparent;}

/* ---------- Container Cards Berbingkai (Streamlit Border Wrapper) ---------- */
[data-testid="stVerticalBlockBorderWrapper"] {
  background-color: var(--card-bg) !important;
  border: 1px solid var(--line) !important;
  border-radius: 12px !important;
  padding: 1.25rem 1.5rem !important;
  box-shadow: var(--card-shadow) !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color: #CBD5E1 !important;
  box-shadow: var(--card-shadow-hover) !important;
}

/* ---------- Sidebar Modern Minimalis ---------- */
[data-testid="stSidebar"]{
  background: #0B1926 !important;
  border-right: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stSidebar"] *{
  color: #94A3B8;
}
[data-testid="stSidebar"] .block-container{
  padding-top: 1.25rem;
}
.brand{
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 8px 4px 20px 4px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  margin-bottom: 16px;
}
.brand-mark{
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, #0D768A 0%, #08505E 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff !important;
  flex: none;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
.brand-mark svg{stroke: #fff;}
.brand-name{
  font-weight: 700;
  font-size: 15.5px;
  color: #F8FAFC !important;
  line-height: 1.2;
  letter-spacing: -0.01em;
}
.brand-sub{
  font-size: 12px;
  color: #64748B !important;
  margin-top: 2px;
}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]{
  border-radius: 8px;
  padding: 9px 12px;
  margin-bottom: 3px;
  text-decoration: none;
  transition: all 0.15s ease;
}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"]:hover{
  background: rgba(255,255,255,0.06);
  color: #F8FAFC !important;
}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"]{
  background: rgba(255,255,255,0.12);
  border-left: 3px solid #0D768A;
}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] *{
  color: #F8FAFC !important;
  font-weight: 600;
}
[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] p{
  font-size: 14px;
  font-weight: 500;
}
.side-note{
  border-top: 1px solid rgba(255,255,255,0.08);
  margin-top: 24px;
  padding-top: 16px;
  font-size: 12px;
  line-height: 1.55;
  color: #64748B !important;
}
.side-note b{
  color: #E2E8F0 !important;
  font-weight: 600;
}
.dot{
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 7px;
  vertical-align: middle;
}

/* ---------- Header Halaman Premium ---------- */
.pg-head{
  display: flex;
  gap: 16px;
  align-items: center;
  padding: 18px 22px;
  background: var(--card-bg);
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: var(--card-shadow);
  margin-bottom: 24px;
}
.pg-icon{
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: var(--teal-light);
  color: var(--teal);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.pg-title{
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.015em;
  color: var(--ink);
  line-height: 1.2;
  margin: 0;
}
.pg-sub{
  font-size: 14px;
  color: var(--muted);
  margin-top: 3px;
}
.sec-title{
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--ink);
  margin: 0 0 4px 0;
}
.sec-sub{
  font-size: 13px;
  color: var(--muted);
  margin: 0 0 14px 0;
  line-height: 1.5;
}

/* ---------- Kartu KPI ---------- */
.kpi{
  background: var(--card-bg);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px 18px;
  height: 100%;
  box-shadow: var(--card-shadow);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: all 0.2s ease;
}
.kpi:hover{
  border-color: #CBD5E1;
  box-shadow: var(--card-shadow-hover);
  transform: translateY(-1px);
}
.kpi-top{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}
.kpi-lbl{
  font-size: 12.5px;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.kpi-ic{
  width: 34px;
  height: 34px;
  border-radius: 8px;
  background: var(--teal-light);
  color: var(--teal);
  display: flex;
  align-items: center;
  justify-content: center;
}
.kpi-val{
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.025em;
  margin-top: 8px;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
  line-height: 1.15;
}
.kpi-val small{
  font-size: 14px;
  font-weight: 500;
  color: var(--muted);
  letter-spacing: 0;
  margin-left: 4px;
}
.kpi-cap{
  font-size: 12px;
  color: var(--muted);
  margin-top: 6px;
  line-height: 1.45;
}

/* ---------- Badge Status ---------- */
.badge{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px 3px 8px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.01em;
  white-space: nowrap;
}
.badge i{
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}

/* ---------- Tabel HTML Elegan ---------- */
.tbl-wrap{
  overflow-x: auto;
  border-radius: 10px;
  border: 1px solid var(--line);
}
table.tbl{
  width: 100%;
  border-collapse: collapse;
  font-size: 13.5px;
}
table.tbl th{
  background: #F8FAFC;
  color: #475569;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-align: left;
  padding: 11px 14px;
  border-bottom: 1px solid var(--line);
  white-space: nowrap;
}
table.tbl th.num, table.tbl td.num{
  text-align: right;
  font-variant-numeric: tabular-nums;
}
table.tbl td{
  padding: 11px 14px;
  border-bottom: 1px solid var(--line-light);
  color: var(--ink);
  vertical-align: middle;
  background: #FFFFFF;
}
table.tbl tr:hover td{
  background: #F8FAFC;
}
table.tbl tr:last-child td{border-bottom: 0;}
table.tbl td small{
  display: block;
  color: var(--muted);
  font-size: 12px;
  margin-top: 1px;
}
.bar{
  height: 7px;
  width: 120px;
  background: #E2E8F0;
  border-radius: 4px;
  overflow: hidden;
  display: inline-block;
}
.bar span{display: block; height: 100%; border-radius: 4px;}

/* ---------- Daftar Perhatian ---------- */
.att{
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--line-light);
}
.att:last-child{border-bottom: 0;}
.att-name{font-weight: 600; font-size: 14.5px; color: var(--ink);}
.att-sub{font-size: 12.5px; color: var(--muted); margin-top: 1px;}
.att-right{text-align: right;}
.att-val{font-variant-numeric: tabular-nums; font-weight: 700; font-size: 14.5px; color: var(--ink);}

/* ---------- Skala Ambang Horizontal ---------- */
.scale{position: relative; padding: 42px 14px 84px 14px;}
.rail{position: relative; height: 12px;}
.track{display: flex; height: 12px; border-radius: 6px; overflow: hidden;}
.seg{display: block; height: 100%; opacity: 0.9;}
.m-pred{position: absolute; top: -12px; width: 3px; height: 36px; background: var(--ink); transform: translateX(-50%); border-radius: 2px;}
.m-pred span{
  position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); margin-bottom: 5px;
  background: var(--ink); color: #fff !important; padding: 3px 9px; border-radius: 4px; font-size: 12px;
  font-weight: 600; white-space: nowrap; font-variant-numeric: tabular-nums;
  box-shadow: 0 2px 4px rgba(0,0,0,0.15);
}
.m-now{
  position: absolute; top: 50%; width: 14px; height: 14px; border-radius: 50%; background: #fff;
  border: 3px solid var(--ink); transform: translate(-50%,-50%); box-sizing: border-box;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
.tick{position: absolute; top: 20px; transform: translateX(-50%); text-align: center; font-size: 12px;
  line-height: 1.3; color: var(--muted); white-space: nowrap; font-variant-numeric: tabular-nums;}
.tick i{display: block; width: 1px; height: 6px; background: #9AA9B4; margin: 0 auto 2px auto;}
.tick b{display: block; color: var(--ink); font-weight: 600;}
.tick.low{top: 56px;}
.legend{display: flex; gap: 20px; font-size: 12.5px; color: var(--muted); margin-top: -6px; padding-left: 14px; align-items: center;}
.legend .sw{display: inline-block; vertical-align: middle; margin-right: 6px;}
.sw-now{width: 12px; height: 12px; border-radius: 50%; border: 3px solid var(--ink); box-sizing: border-box; background: #fff;}
.sw-pred{width: 3px; height: 14px; background: var(--ink); border-radius: 2px;}

/* ---------- Hasil Prediksi ---------- */
.res-head{display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap;}
.res-city{font-size: 13.5px; font-weight: 500; color: var(--muted);}
.res-big{
  font-size: 44px; font-weight: 700; letter-spacing: -0.03em; line-height: 1.1; margin-top: 4px;
  color: var(--ink); font-variant-numeric: tabular-nums;
}
.res-big small{font-size: 18px; font-weight: 500; color: var(--muted); margin-left: 6px; letter-spacing: 0;}
.res-delta{font-size: 14px; color: var(--muted); margin-top: 6px;}
.res-note{
  font-size: 13.5px; color: var(--ink); background: #F8FAFC; border: 1px solid var(--line);
  border-radius: 8px; padding: 12px 14px; margin-top: 16px; line-height: 1.5;
}
.mini-grid{display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 16px;}
.mini{
  border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; background: #FFFFFF;
}
.mini .l{font-size: 12px; font-weight: 500; color: var(--muted);}
.mini .v{font-size: 18px; font-weight: 700; color: var(--ink); font-variant-numeric: tabular-nums; margin-top: 3px;}

.callout{
  border-left: 3px solid var(--teal); background: #FFFFFF; border-radius: 0 8px 8px 0;
  padding: 14px 18px; font-size: 13.5px; line-height: 1.6; color: var(--ink);
  border-top: 1px solid var(--line); border-right: 1px solid var(--line); border-bottom: 1px solid var(--line);
}
.callout b{font-weight: 650;}

/* ---------- Kontrol, Tombol, Form Modern ---------- */
.stButton > button, .stDownloadButton > button{
  border-radius: 8px; font-weight: 600; padding: 0.55rem 1.2rem;
  border: 1px solid #CBD5E1; background: #FFFFFF; color: var(--ink);
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  transition: all 0.15s ease-in-out;
}
.stButton > button:hover, .stDownloadButton > button:hover{
  border-color: var(--teal); color: var(--teal); background: #F8FAFC;
  transform: translateY(-1px);
}
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"]{
  background: var(--teal) !important; border-color: var(--teal) !important; color: #fff !important;
  box-shadow: 0 1px 2px rgba(13,118,138,0.2) !important;
}
.stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover{
  background: var(--teal-dark) !important; border-color: var(--teal-dark) !important; color: #fff !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px -1px rgba(13,118,138,0.25) !important;
}
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible{
  outline: 3px solid rgba(13,118,138,0.3); outline-offset: 2px;
}
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="base-input"]{
  border-radius: 8px !important;
  border-color: #CBD5E1 !important;
}
[data-testid="stWidgetLabel"] p{font-size: 13.5px; font-weight: 600; color: var(--ink);}
button[data-baseweb="tab"]{padding: 10px 4px; margin-right: 22px;}
button[data-baseweb="tab"] p{font-size: 14.5px; font-weight: 600; color: var(--muted);}
button[data-baseweb="tab"][aria-selected="true"] p{color: var(--teal);}
div[data-baseweb="tab-highlight"]{background-color: var(--teal) !important; height: 2px;}
[data-testid="stExpander"]{border: 1px solid var(--line); border-radius: 8px; background: #fff;}
[data-testid="stDataFrame"]{border: 1px solid var(--line); border-radius: 8px; overflow: hidden;}

@media (max-width: 900px){
  .res-big{font-size: 34px;}
  .mini-grid{grid-template-columns: 1fr;}
  .block-container{padding-left: 1rem; padding-right: 1rem;}
}
@media (prefers-reduced-motion: reduce){ *{transition: none !important;} }
</style>
"""


def H(s):
    """Tampilkan HTML (tanpa indentasi supaya tidak dibaca sebagai code block)."""
    st.markdown("".join(line.strip() for line in s.strip().splitlines()),
                unsafe_allow_html=True)


def fmt(v, d=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    s = f"{v:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def tgl_id(d):
    d = pd.Timestamp(d)
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


def badge(status):
    return (f'<span class="badge" style="background:{BADGE_BG[status]};color:{BADGE_FG[status]}">'
            f'<i style="background:{WARNA_STATUS[status]}"></i>{status}</span>')


def judul_halaman(nama_ikon, judul, sub):
    H(f'<div class="pg-head"><div class="pg-icon">{ikon(nama_ikon, 24)}</div>'
      f'<div><h1 class="pg-title">{judul}</h1><div class="pg-sub">{sub}</div></div></div>')


def judul_seksi(judul, sub=None):
    H(f'<div class="sec-title">{judul}</div>' + (f'<div class="sec-sub">{sub}</div>' if sub else ""))


def kartu_kpi(label, nilai, keterangan, nama_ikon, satuan=""):
    sat = f"<small>{satuan}</small>" if satuan else ""
    return (f'<div class="kpi"><div class="kpi-top"><div class="kpi-lbl">{label}</div>'
            f'<div class="kpi-ic">{ikon(nama_ikon, 20)}</div></div>'
            f'<div class="kpi-val">{nilai}{sat}</div><div class="kpi-cap">{keterangan}</div></div>')


def tata_grafik(fig, tinggi=380):
    fig.update_layout(
        template="plotly_white", height=tinggi,
        margin=dict(l=8, r=8, t=30, b=8),
        font=dict(family=FONT, size=13, color=INK),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.1, x=0, title=None),
        hoverlabel=dict(font_family=FONT, bgcolor="#fff", bordercolor=GRID),
    )
    fig.update_xaxes(showgrid=False, linecolor="#C9D3DA", ticks="outside", tickcolor="#C9D3DA")
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def tampil_grafik(fig):
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False,
                                                   "modeBarButtonsToRemove": ["lasso2d", "select2d"]})


# ----------------------------------------------------------------------------
# 2. Muat artefak model
# ----------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent
ART = next((p for p in (BASE / "artifacts_banjir", BASE) if (p / "model_meta.json").exists()),
           BASE / "artifacts_banjir")


@st.cache_resource(show_spinner=False)
def muat_model():
    return joblib.load(ART / "model_gbr_debit.joblib")


@st.cache_data(show_spinner=False)
def muat_meta():
    with open(ART / "model_meta.json", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def muat_riwayat():
    d = pd.read_csv(ART / "riwayat_harian.csv", parse_dates=["obs_date"])
    return d.sort_values(["kota", "obs_date"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def muat_eda():
    return pd.read_csv(ART / "ringkasan_eda.csv")


st.markdown(CSS, unsafe_allow_html=True)

try:
    MODEL = muat_model()
    META = muat_meta()
    RIW = muat_riwayat()
    EDA = muat_eda()
except FileNotFoundError as e:
    st.error(f"Berkas artefak tidak ditemukan: {e.filename}. "
             "Letakkan folder artifacts_banjir di samping app.py "
             "(isi: model_gbr_debit.joblib, model_meta.json, riwayat_harian.csv, ringkasan_eda.csv).")
    st.stop()

KOTA = META["daftar_kota"]
TGL_AKHIR = RIW["obs_date"].max()
TGL_POTONG = pd.Timestamp(META["tanggal_potong_split"])


# ----------------------------------------------------------------------------
# 3. Logika fitur (sama dengan notebook: buat_fitur)
# ----------------------------------------------------------------------------
def buat_fitur(data, dengan_target=True, daftar_kota=None):
    """
    data: kolom kota, obs_date, debit, hujan (harian, per kota).
    Mengembalikan baris dengan 35 fitur sesuai META['fitur_urut'].
    Jika dengan_target=True, ditambah dlog_target dan debit_besok.
    """
    daftar_kota = daftar_kota or META["daftar_kota"]
    bagian = []
    for _, g in data.sort_values(["kota", "obs_date"]).groupby("kota", sort=False):
        g = g.copy()
        L = np.log1p(g["debit"].clip(lower=0))
        h = g["hujan"]
        g["log_debit_t0"] = L
        g["dlog_1"] = L.diff(1)
        g["dlog_3"] = L.diff(3)
        g["dlog_7"] = L.diff(7)
        g["dlog_mean7"] = L.diff(1).rolling(7).mean()
        g["hujan_t0"] = h
        for k in (1, 2, 3):
            g[f"hujan_lag{k}"] = h.shift(k)
        g["hujan_sum3"] = h.rolling(3).sum()
        g["hujan_sum7"] = h.rolling(7).sum()
        bulan = g["obs_date"].dt.month
        g["bulan_sin"] = np.sin(2 * np.pi * bulan / 12)
        g["bulan_cos"] = np.cos(2 * np.pi * bulan / 12)
        if dengan_target:
            g["debit_besok"] = g["debit"].shift(-1)
            g["dlog_target"] = np.log1p(g["debit_besok"]) - L
        bagian.append(g)
    f = pd.concat(bagian)
    for k in daftar_kota:
        f[f"kota_{k}"] = (f["kota"] == k).astype(int)
    wajib = list(META["fitur_urut"]) + (["dlog_target"] if dengan_target else [])
    return f.dropna(subset=wajib)


def ke_debit(debit_t0, dlog):
    """debit_besok = expm1(log1p(debit_hari_ini) + dlog), minimal 0."""
    return np.maximum(np.expm1(np.log1p(np.asarray(debit_t0, dtype=float)) + np.asarray(dlog)), 0.0)


def klasifikasi(kota, nilai):
    a = META["ambang_per_kota"][kota]
    if nilai >= a["awas_p95"]:
        return "Awas"
    if nilai >= a["siaga_p90"]:
        return "Siaga"
    if nilai >= a["waspada_p75"]:
        return "Waspada"
    return "Normal"


@st.cache_data(show_spinner=False)
def snapshot_kota():
    """Kondisi terakhir tiap kota dan prediksi untuk hari berikutnya."""
    ekor = RIW.groupby("kota").tail(10)[["kota", "obs_date", "debit", "hujan"]]
    f = buat_fitur(ekor, dengan_target=False)
    terakhir = f.sort_values("obs_date").groupby("kota").tail(1).copy()
    dlog = MODEL.predict(terakhir[META["fitur_urut"]])
    terakhir["debit_pred"] = ke_debit(terakhir["debit"], dlog)
    info = RIW.groupby("kota").first()[["river_name", "province", "latitude", "longitude"]]
    out = terakhir[["kota", "obs_date", "debit", "hujan", "debit_pred"]].merge(info, on="kota")
    out["status_kini"] = [klasifikasi(k, v) for k, v in zip(out["kota"], out["debit"])]
    out["status_besok"] = [klasifikasi(k, v) for k, v in zip(out["kota"], out["debit_pred"])]
    out["rasio_awas"] = [v / META["ambang_per_kota"][k]["awas_p95"]
                         for k, v in zip(out["kota"], out["debit_pred"])]
    out["perubahan_pct"] = np.where(out["debit"] > 0, (out["debit_pred"] / out["debit"] - 1) * 100, np.nan)
    return out.sort_values("rasio_awas", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def hitung_backtest():
    f = buat_fitur(RIW[["kota", "obs_date", "debit", "hujan"]], dengan_target=True)
    dlog = MODEL.predict(f[META["fitur_urut"]])
    f["prediksi"] = ke_debit(f["debit"], dlog)
    f["tanggal_target"] = f["obs_date"] + pd.Timedelta(days=1)
    f["uji"] = f["obs_date"] >= TGL_POTONG
    return f[["kota", "obs_date", "tanggal_target", "debit", "debit_besok", "prediksi", "uji"]]


# ----------------------------------------------------------------------------
# 4. Penyimpanan Riwayat Prediksi: Berkas CSV Mandiri
# ----------------------------------------------------------------------------
FILE_LOG_CSV = BASE / "artifacts_banjir" / "riwayat_prediksi.csv"
KOLOM_LOG = [
    "id", "waktu_prediksi", "kota", "tanggal_acuan", "tanggal_target",
    "debit_hari_ini", "hujan_hari_ini", "hujan_sum3", "hujan_sum7",
    "prediksi_debit", "baseline_debit", "status_risiko", "catatan"
]


def simpan_prediksi(baris):
    """Menyimpan baris prediksi ke berkas CSV riwayat."""
    if FILE_LOG_CSV.exists():
        try:
            df = pd.read_csv(FILE_LOG_CSV)
        except Exception:
            df = pd.DataFrame(columns=KOLOM_LOG)
    else:
        df = pd.DataFrame(columns=KOLOM_LOG)

    baris_baru = dict(baris)
    baris_baru["id"] = int(df["id"].max() + 1) if (not df.empty and "id" in df.columns and pd.notna(df["id"].max())) else 1
    
    if hasattr(baris_baru["waktu_prediksi"], "strftime"):
        baris_baru["waktu_prediksi"] = baris_baru["waktu_prediksi"].strftime("%Y-%m-%d %H:%M:%S")
    baris_baru["tanggal_acuan"] = str(baris_baru["tanggal_acuan"])
    baris_baru["tanggal_target"] = str(baris_baru["tanggal_target"])

    df_baru = pd.concat([df, pd.DataFrame([baris_baru])], ignore_index=True)
    df_baru.to_csv(FILE_LOG_CSV, index=False, encoding="utf-8")


def baca_riwayat(batas=500):
    """Membaca riwayat prediksi dari berkas CSV."""
    if not FILE_LOG_CSV.exists():
        return pd.DataFrame(columns=KOLOM_LOG)
    try:
        df = pd.read_csv(FILE_LOG_CSV)
        if df.empty:
            return df
        if "id" in df.columns:
            df = df.sort_values("id", ascending=False)
        return df.head(batas)
    except Exception:
        return pd.DataFrame(columns=KOLOM_LOG)


# ----------------------------------------------------------------------------
# 5. Komponen visual khusus: skala ambang
# ----------------------------------------------------------------------------
def skala_html(kota, sekarang, prediksi=None):
    a = META["ambang_per_kota"][kota]
    w, s, aw = a["waspada_p75"], a["siaga_p90"], a["awas_p95"]
    mx = max(aw * 1.3, sekarang * 1.1, (prediksi or 0) * 1.1)

    def pct(v):
        return min(max(v / mx * 100, 0), 100)

    batas = [(0, w, "Normal"), (w, s, "Waspada"), (s, aw, "Siaga"), (aw, mx, "Awas")]
    segs = "".join(
        f'<span class="seg" style="width:{pct(b) - pct(a_):.2f}%;background:{WARNA_STATUS[n]}"></span>'
        for a_, b, n in batas)
    ticks = "".join(
        f'<span class="tick{" low" if i == 1 else ""}" style="left:{pct(v):.2f}%"><i></i>'
        f'<b>{nm}</b>{fmt(v, 1)}</span>'
        for i, (nm, v) in enumerate([("Waspada", w), ("Siaga", s), ("Awas", aw)]))
    pred = ""
    if prediksi is not None:
        pred = (f'<div class="m-pred" style="left:{pct(prediksi):.2f}%">'
                f'<span>{fmt(prediksi, 1)}</span></div>')
    kini = f'<div class="m-now" style="left:{pct(sekarang):.2f}%"></div>'
    legend = ('<div class="legend"><span><i class="sw sw-now"></i>Debit hari ini</span>'
              + ('<span><i class="sw sw-pred"></i>Prediksi besok</span>' if prediksi is not None else "")
              + '<span>Satuan m³/s</span></div>')
    return (f'<div class="scale"><div class="rail"><div class="track">{segs}</div>'
            f'{ticks}{kini}{pred}</div></div>{legend}')


# ----------------------------------------------------------------------------
# 6. Halaman 1 - Beranda risiko
# ----------------------------------------------------------------------------
def halaman_beranda():
    snap = snapshot_kota()
    judul_halaman("gauge", "Beranda risiko",
                  "Ringkasan kondisi debit terakhir dan prediksi satu hari ke depan untuk 22 kota.")

    n_kini = int((snap["status_kini"] != "Normal").sum())
    n_besok = int((snap["status_besok"] != "Normal").sum())
    n_siaga = int(snap["status_besok"].isin(["Siaga", "Awas"]).sum())
    tgl_target = TGL_AKHIR + pd.Timedelta(days=1)

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(kartu_kpi("Data terakhir", tgl_id(TGL_AKHIR),
                          f"Prediksi berlaku untuk {tgl_id(tgl_target)}", "calendar"),
                unsafe_allow_html=True)
    k2.markdown(kartu_kpi("Kota dipantau", str(len(KOTA)),
                          "Denpasar dan Surabaya tidak memiliki data debit", "pin"),
                unsafe_allow_html=True)
    k3.markdown(kartu_kpi("Waspada atau lebih, besok", f"{n_besok}", f"Hari ini: {n_kini} kota. "
                          f"Siaga atau Awas besok: {n_siaga} kota.", "alert", satuan=f"dari {len(snap)} kota"),
                unsafe_allow_html=True)
    mae = META["metrik_uji"]["GBR"]["MAE"]
    base = META["metrik_uji"]["Baseline"]["MAE"]
    k4.markdown(kartu_kpi("Galat rata-rata model (MAE)", fmt(mae), f"Baseline persistence: {fmt(base)} m³/s "
                          "pada data uji", "target", satuan="m³/s"),
                unsafe_allow_html=True)

    st.write("")
    kiri, kanan = st.columns([1.35, 1], gap="medium")

    with kiri:
        with st.container(border=True, key="card_peta"):
            judul_seksi("Peta status prediksi besok",
                        "Warna titik menunjukkan status risiko menurut ambang persentil masing-masing kota.")
            fig = px.scatter_map(
                snap, lat="latitude", lon="longitude", color="status_besok",
                category_orders={"status_besok": STATUS}, color_discrete_map=WARNA_STATUS,
                hover_name="kota",
                hover_data={"river_name": True, "debit": ":.2f", "debit_pred": ":.2f",
                            "latitude": False, "longitude": False, "status_besok": False},
                labels={"river_name": "Sungai", "debit": "Debit hari ini", "debit_pred": "Prediksi besok"},
                zoom=3.0, center={"lat": -2.6, "lon": 117.5}, map_style="carto-positron", height=430)
            fig.update_traces(marker=dict(size=13))
            tata_grafik(fig, 430)
            fig.update_layout(margin=dict(l=0, r=0, t=0, b=0),
                              legend=dict(orientation="h", y=0.02, x=0.01, bgcolor="rgba(255,255,255,.85)"))
            tampil_grafik(fig)

    with kanan:
        with st.container(border=True, key="card_perhatian"):
            judul_seksi("Paling dekat dengan ambang Awas",
                        "Diurutkan dari perbandingan debit prediksi terhadap ambang Awas (P95) kota.")
            baris = ""
            for _, r in snap.head(6).iterrows():
                baris += (f'<div class="att"><div><div class="att-name">{r["kota"]}</div>'
                          f'<div class="att-sub">{r["river_name"]}, {fmt(r["rasio_awas"] * 100, 0)}% dari ambang Awas</div></div>'
                          f'<div class="att-right"><div class="att-val">{fmt(r["debit_pred"])} m³/s</div>'
                          f'{badge(r["status_besok"])}</div></div>')
            H(baris)

    st.write("")
    with st.container(border=True, key="card_tabel"):
        judul_seksi("Semua kota",
                    f"Kondisi pada {tgl_id(TGL_AKHIR)} dan prediksi untuk {tgl_id(tgl_target)}.")
        head = ('<tr><th>Kota</th><th class="num">Debit hari ini</th><th class="num">Prediksi besok</th>'
                '<th class="num">Perubahan</th><th>Posisi terhadap ambang Awas</th>'
                '<th>Status hari ini</th><th>Status besok</th></tr>')
        isi = ""
        for _, r in snap.sort_values("kota").iterrows():
            lebar = min(r["rasio_awas"], 1.0) * 100
            perub = "-" if np.isnan(r["perubahan_pct"]) else f'{r["perubahan_pct"]:+.1f}'.replace(".", ",") + "%"
            isi += (f'<tr><td><b>{r["kota"]}</b><small>{r["river_name"]}, {r["province"]}</small></td>'
                    f'<td class="num">{fmt(r["debit"])}</td><td class="num">{fmt(r["debit_pred"])}</td>'
                    f'<td class="num">{perub}</td>'
                    f'<td><span class="bar"><span style="width:{lebar:.1f}%;background:{WARNA_STATUS[r["status_besok"]]}"></span></span> '
                    f'<span style="font-size:12.5px;color:#5F7080;margin-left:6px">{fmt(r["rasio_awas"] * 100, 0)}%</span></td>'
                    f'<td>{badge(r["status_kini"])}</td><td>{badge(r["status_besok"])}</td></tr>')
        H(f'<div class="tbl-wrap"><table class="tbl"><thead>{head}</thead><tbody>{isi}</tbody></table></div>')
        st.caption("Satuan debit m³/s. Status dihitung dari ambang P75 (Waspada), P90 (Siaga), dan P95 (Awas) "
                   "debit per kota pada data latih.")


# ----------------------------------------------------------------------------
# 7. Halaman 2 - Eksplorasi data
# ----------------------------------------------------------------------------
def halaman_eksplorasi():
    judul_halaman("chart", "Eksplorasi data",
                  "Telusuri tren debit dan hujan, respons sungai terhadap hujan, serta peringkat risiko kota.")

    kol, _ = st.columns([1, 2])
    kota = kol.selectbox("Kota", KOTA, index=KOTA.index("Banda Aceh"), key="eks_kota")
    g = RIW[RIW["kota"] == kota].copy()
    a = META["ambang_per_kota"][kota]
    sungai = g["river_name"].iloc[0]
    prov = g["province"].iloc[0]
    st.caption(f"Sungai {sungai}, {prov}. Rentang data {tgl_id(g['obs_date'].min())} sampai {tgl_id(g['obs_date'].max())}.")

    t1, t2, t3, t4 = st.tabs(["Tren harian", "Respons terhadap hujan", "Pola bulanan", "Peringkat risiko kota"])

    with t1:
        with st.container(border=True, key="card_tren"):
            periode = st.radio("Periode", ["30 hari terakhir", "90 hari terakhir", "Seluruh data"],
                               horizontal=True, index=1, key="eks_periode")
            gg = g if periode == "Seluruh data" else g.tail(30 if periode.startswith("30") else 90)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.05)
            fig.add_trace(go.Scatter(x=gg["obs_date"], y=gg["debit"], mode="lines", name="Debit",
                                     line=dict(color=TEAL, width=2.2)), row=1, col=1)
            for nm, key, warna in (("Waspada P75", "waspada_p75", WARNA_STATUS["Waspada"]),
                                   ("Siaga P90", "siaga_p90", WARNA_STATUS["Siaga"]),
                                   ("Awas P95", "awas_p95", WARNA_STATUS["Awas"])):
                fig.add_hline(y=a[key], line=dict(color=warna, width=1.2, dash="dash"),
                              annotation_text=nm, annotation_position="top left",
                              annotation_font=dict(size=11.5, color=warna), row=1, col=1)
            fig.add_trace(go.Bar(x=gg["obs_date"], y=gg["hujan"], name="Hujan",
                                 marker_color="#7FA7B8"), row=2, col=1)
            fig.update_yaxes(title_text="Debit (m³/s)", row=1, col=1)
            fig.update_yaxes(title_text="Hujan (mm)", row=2, col=1)
            tata_grafik(fig, 520)
            tampil_grafik(fig)
            st.caption("Garis putus-putus adalah ambang risiko kota dari data latih. Jika debit tidak terlihat "
                       "melewati ambang, skala sumbu menyesuaikan rentang data pada periode terpilih.")

    with t2:
        c1, c2 = st.columns(2, gap="medium")
        hasil = [(lag, g["hujan"].shift(lag).corr(g["debit"], method="spearman")) for lag in range(0, 8)]
        lag_df = pd.DataFrame(hasil, columns=["lag", "rho"])
        terbaik = int(lag_df.loc[lag_df["rho"].idxmax(), "lag"])
        with c1:
            with st.container(border=True, key="card_lag"):
                judul_seksi("Korelasi debit dengan hujan tertunda",
                            f"Korelasi Spearman antara debit dan hujan n hari sebelumnya. Puncak pada lag {terbaik} hari.")
                fig = go.Figure(go.Bar(
                    x=lag_df["lag"], y=lag_df["rho"],
                    marker_color=[TEAL if l == terbaik else "#B9C7D0" for l in lag_df["lag"]],
                    hovertemplate="Lag %{x} hari<br>Spearman %{y:.2f}<extra></extra>"))
                fig.update_xaxes(title_text="Lag hujan (hari)", dtick=1)
                fig.update_yaxes(title_text="Korelasi Spearman")
                tata_grafik(fig, 340)
                tampil_grafik(fig)
        with c2:
            with st.container(border=True, key="card_scatter"):
                judul_seksi("Hujan 3 hari terhadap debit")
                sc = pd.DataFrame({"hujan3": g["hujan"].rolling(3).sum(), "debit": g["debit"]}).dropna()
                rho = sc["hujan3"].corr(sc["debit"], method="spearman")
                st.markdown(f'<div class="sec-sub">Korelasi Spearman {fmt(rho)} pada {len(sc)} hari.</div>',
                            unsafe_allow_html=True)
                fig = px.scatter(sc, x="hujan3", y="debit", opacity=0.55,
                                 labels={"hujan3": "Total hujan 3 hari (mm)", "debit": "Debit (m³/s)"})
                fig.update_traces(marker=dict(color=TEAL, size=7))
                tata_grafik(fig, 340)
                tampil_grafik(fig)

    with t3:
        with st.container(border=True, key="card_bulan"):
            judul_seksi("Debit per bulan", "Median dan nilai maksimum debit harian pada tiap bulan kalender.")
            gm = g.assign(per=g["obs_date"].dt.to_period("M")).groupby("per")["debit"].agg(["median", "max"]).reset_index()
            gm["label"] = [f"{BULAN[p.month - 1]} {p.year}" for p in gm["per"]]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=gm["label"], y=gm["median"], name="Median", marker_color=TEAL))
            fig.add_trace(go.Bar(x=gm["label"], y=gm["max"], name="Maksimum", marker_color="#B9C7D0"))
            fig.update_layout(barmode="group")
            fig.update_yaxes(title_text="Debit (m³/s)")
            tata_grafik(fig, 380)
            tampil_grafik(fig)
            st.caption("Data hanya mencakup sekitar satu tahun, sehingga setiap bulan berisi satu pengamatan musim. "
                       "Pola ini belum cukup untuk menyimpulkan musiman jangka panjang.")

    with t4:
        c1, c2 = st.columns([1.1, 1], gap="medium")
        urut = EDA.sort_values("rasio_puncak")
        with c1:
            with st.container(border=True, key="card_rank"):
                judul_seksi("Rasio puncak terhadap median",
                            "Debit maksimum dibagi median. Nilai besar menandakan lonjakan ekstrem.")
                top5 = set(EDA.sort_values("skor_peringkat").head(5)["kota"])
                fig = go.Figure(go.Bar(
                    x=urut["rasio_puncak"], y=urut["kota"], orientation="h",
                    marker_color=[TEAL if k in top5 else "#B9C7D0" for k in urut["kota"]],
                    hovertemplate="%{y}<br>Rasio puncak %{x:.1f}x<extra></extra>"))
                fig.update_xaxes(title_text="Rasio puncak (kali)")
                fig.update_yaxes(showgrid=False)
                tata_grafik(fig, 560)
                tampil_grafik(fig)
                st.caption("Warna tua menandai lima kota dengan skor peringkat risiko terbaik (paling berisiko).")
        with c2:
            with st.container(border=True, key="card_rank_tbl"):
                judul_seksi("Tabel peringkat",
                            "Skor peringkat gabungan; nilai lebih kecil berarti lebih berisiko.")
                tabel = EDA.sort_values("skor_peringkat").rename(columns={
                    "kota": "Kota", "med": "Median", "maks": "Maksimum", "rasio_puncak": "Rasio puncak",
                    "frek_lonjakan_pct": "Hari lonjakan (%)", "skor_peringkat": "Skor"})
                st.dataframe(tabel, hide_index=True, height=520, column_config={
                    "Median": st.column_config.NumberColumn(format="%.2f"),
                    "Maksimum": st.column_config.NumberColumn(format="%.1f"),
                    "Rasio puncak": st.column_config.NumberColumn(format="%.1f"),
                    "Hari lonjakan (%)": st.column_config.NumberColumn(format="%.1f"),
                    "Skor": st.column_config.NumberColumn(format="%.2f")})


# ----------------------------------------------------------------------------
# 8. Halaman 3 - Prediksi debit
# ----------------------------------------------------------------------------
def hitung_prediksi(kota, tgl, debit_seri, hujan_seri):
    """debit_seri dan hujan_seri: 8 nilai, urut dari t-7 sampai hari ini (t)."""
    tanggal = pd.date_range(end=pd.Timestamp(tgl), periods=8)
    df = pd.DataFrame({"kota": kota, "obs_date": tanggal,
                       "debit": [float(x) for x in debit_seri],
                       "hujan": [float(x) for x in hujan_seri]})
    f = buat_fitur(df, dengan_target=False)
    baris = f.iloc[[-1]]
    dlog = float(MODEL.predict(baris[META["fitur_urut"]])[0])
    pred = float(ke_debit(df["debit"].iloc[-1], dlog))
    return {"kota": kota, "tgl": pd.Timestamp(tgl), "baris": baris, "dlog": dlog, "pred": pred,
            "debit0": float(df["debit"].iloc[-1]), "hujan0": float(df["hujan"].iloc[-1]),
            "sum3": float(baris["hujan_sum3"].iloc[0]), "sum7": float(baris["hujan_sum7"].iloc[0]),
            "status": klasifikasi(kota, pred)}


def kurva_skenario_hujan(hasil, maks_hujan=150, n=16):
    """Prediksi debit besok bila curah hujan hari ini diganti nilai lain (fitur lain tetap)."""
    b = hasil["baris"]
    nilai = np.linspace(0, maks_hujan, n)
    X = pd.concat([b] * n, ignore_index=True)
    X["hujan_t0"] = nilai
    X["hujan_sum3"] = b["hujan_sum3"].iloc[0] - b["hujan_t0"].iloc[0] + nilai
    X["hujan_sum7"] = b["hujan_sum7"].iloc[0] - b["hujan_t0"].iloc[0] + nilai
    dlog = MODEL.predict(X[META["fitur_urut"]])
    return nilai, ke_debit(np.full(n, hasil["debit0"]), dlog)


def halaman_prediksi():
    judul_halaman("rain", "Prediksi debit",
                  "Masukkan kondisi hari ini dan riwayat 7 hari sebelumnya untuk memperkirakan debit besok.")

    tmin = (RIW.groupby("kota")["obs_date"].min().max() + pd.Timedelta(days=7)).date()
    tmax = TGL_AKHIR.date()
    kiri, kanan = st.columns([5, 7], gap="large")

    with kiri:
        with st.container(border=True, key="card_form"):
            judul_seksi("Data masukan",
                        "Nilai awal diambil dari data historis pada tanggal terpilih dan dapat diubah.")
            kota = st.selectbox("Kota", KOTA, key="p_kota")
            tgl = st.date_input("Tanggal acuan (hari ini)", value=tmax, min_value=tmin, max_value=tmax,
                                format="DD/MM/YYYY", key="p_tgl")
            g = RIW[RIW["kota"] == kota].set_index("obs_date").sort_index()
            jendela = g.loc[pd.Timestamp(tgl) - pd.Timedelta(days=7): pd.Timestamp(tgl)]
            if len(jendela) < 8:
                st.error("Riwayat 8 hari tidak lengkap pada tanggal ini. Pilih tanggal acuan lain.")
                return
            sfx = f"{kota}_{tgl}"
            c1, c2 = st.columns(2)
            d0 = c1.number_input("Debit hari ini (m³/s)", min_value=0.0, step=0.1, format="%.2f",
                                 value=float(jendela["debit"].iloc[-1]), key=f"d0_{sfx}")
            h0 = c2.number_input("Hujan hari ini (mm)", min_value=0.0, step=0.5, format="%.2f",
                                 value=float(jendela["hujan"].iloc[-1]), key=f"h0_{sfx}")
            with st.expander("Riwayat 7 hari sebelumnya"):
                sebelum = jendela.iloc[:-1].iloc[::-1]  # t-1 ... t-7
                tabel = pd.DataFrame({
                    "Hari": [f"t-{i}" for i in range(1, 8)],
                    "Debit (m³/s)": sebelum["debit"].round(2).to_list(),
                    "Hujan (mm)": sebelum["hujan"].round(2).to_list()})
                ed = st.data_editor(tabel, hide_index=True, disabled=["Hari"], key=f"ed_{sfx}",
                                    column_config={
                                        "Debit (m³/s)": st.column_config.NumberColumn(min_value=0.0, format="%.2f"),
                                        "Hujan (mm)": st.column_config.NumberColumn(min_value=0.0, format="%.2f")})
                st.caption("Hujan t-7 tidak dipakai model, hanya debit t-7. Kolom kosong tidak diizinkan.")
            hitung = st.button("Hitung prediksi", type="primary", icon=":material/calculate:", key="btn_hitung")

        if hitung:
            if ed[["Debit (m³/s)", "Hujan (mm)"]].isna().any().any():
                st.error("Ada nilai yang kosong pada tabel riwayat. Lengkapi sebelum menghitung.")
            else:
                debit_seri = ed["Debit (m³/s)"].to_list()[::-1] + [d0]      # t-7 ... t
                hujan_seri = ed["Hujan (mm)"].to_list()[::-1] + [h0]
                st.session_state["hasil"] = hitung_prediksi(kota, tgl, debit_seri, hujan_seri)

    with kanan:
        hasil = st.session_state.get("hasil")
        if not hasil:
            with st.container(border=True, key="card_kosong"):
                judul_seksi("Hasil prediksi",
                            "Pilih kota dan tanggal, periksa nilai masukan, lalu tekan Hitung prediksi.")
                H(f'<div class="callout"><b>Cara membaca hasil.</b> Model memprediksi perubahan log debit satu hari ke depan, '
                  f'lalu mengubahnya kembali menjadi m³/s. Status risiko dibandingkan dengan ambang P75, P90, dan P95 '
                  f'debit kota tersebut pada data latih.</div>')
            return

        tgl_target = hasil["tgl"] + pd.Timedelta(days=1)
        selisih = hasil["pred"] - hasil["debit0"]
        persen = f'{(hasil["pred"] / hasil["debit0"] - 1) * 100:+.1f}'.replace(".", ",") + "%" if hasil["debit0"] > 0 else "-"
        arah = "naik" if selisih > 0 else "turun" if selisih < 0 else "tetap"
        mae = META["metrik_uji"]["GBR"]["MAE"]

        with st.container(border=True, key="card_hasil"):
            H(f'<div class="res-head"><div><div class="res-city">{hasil["kota"]}, prediksi untuk {tgl_id(tgl_target)}</div>'
              f'<div class="res-big">{fmt(hasil["pred"])}<small>m³/s</small></div>'
              f'<div class="res-delta">Debit {arah} {fmt(abs(selisih))} m³/s ({persen}) dari hari ini, {fmt(hasil["debit0"])} m³/s</div></div>'
              f'<div>{badge(hasil["status"])}</div></div>')
            H(f'<div class="res-note">{KETERANGAN_STATUS[hasil["status"]]}</div>')
            H(f'<div class="mini-grid">'
              f'<div class="mini"><div class="l">Hujan hari ini</div><div class="v">{fmt(hasil["hujan0"], 1)} mm</div></div>'
              f'<div class="mini"><div class="l">Total hujan 3 hari</div><div class="v">{fmt(hasil["sum3"], 1)} mm</div></div>'
              f'<div class="mini"><div class="l">Total hujan 7 hari</div><div class="v">{fmt(hasil["sum7"], 1)} mm</div></div></div>')
            st.write("")
            judul_seksi("Posisi terhadap ambang risiko")
            H(skala_html(hasil["kota"], hasil["debit0"], hasil["pred"]))
            st.caption(f"Galat rata-rata model pada data uji seluruh kota: {fmt(mae)} m³/s. "
                       "Untuk kota dengan debit kecil, galat relatif bisa lebih kecil atau lebih besar dari angka ini.")

        st.write("")
        with st.container(border=True, key="card_sens"):
            judul_seksi("Sensitivitas terhadap hujan hari ini",
                        "Prediksi debit besok jika hujan hari ini diganti nilai lain, dengan masukan lain tetap sama.")
            nilai, debit = kurva_skenario_hujan(hasil)
            a = META["ambang_per_kota"][hasil["kota"]]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=nilai, y=debit, mode="lines+markers", name="Prediksi besok",
                                     line=dict(color=TEAL, width=2.4), marker=dict(size=6)))
            fig.add_trace(go.Scatter(x=[hasil["hujan0"]], y=[hasil["pred"]], mode="markers", name="Masukan saat ini",
                                     marker=dict(size=13, color="#fff", line=dict(color=INK, width=3))))
            for nm, key, warna in (("Waspada", "waspada_p75", WARNA_STATUS["Waspada"]),
                                   ("Siaga", "siaga_p90", WARNA_STATUS["Siaga"]),
                                   ("Awas", "awas_p95", WARNA_STATUS["Awas"])):
                fig.add_hline(y=a[key], line=dict(color=warna, width=1.1, dash="dash"),
                              annotation_text=nm, annotation_position="top left",
                              annotation_font=dict(size=11.5, color=warna))
            fig.update_xaxes(title_text="Hujan hari ini (mm)")
            fig.update_yaxes(title_text="Debit besok (m³/s)")
            tata_grafik(fig, 340)
            tampil_grafik(fig)

        st.write("")
        with st.container(border=True, key="card_simpan"):
            judul_seksi("Simpan ke riwayat",
                        "Penyimpanan aktif: Berkas CSV riwayat prediksi (tersimpan otomatis).")
            catatan = st.text_input("Catatan (opsional)", max_chars=200, key="p_catatan",
                                    placeholder="Contoh: skenario hujan lebat")
            if st.button("Simpan ke riwayat", icon=":material/save:", key="btn_simpan"):
                try:
                    simpan_prediksi({
                        "waktu_prediksi": datetime.now(),
                        "kota": hasil["kota"],
                        "tanggal_acuan": hasil["tgl"].date(),
                        "tanggal_target": tgl_target.date(),
                        "debit_hari_ini": hasil["debit0"],
                        "hujan_hari_ini": hasil["hujan0"],
                        "hujan_sum3": hasil["sum3"],
                        "hujan_sum7": hasil["sum7"],
                        "prediksi_debit": hasil["pred"],
                        "baseline_debit": hasil["debit0"],
                        "status_risiko": hasil["status"],
                        "catatan": catatan or None})
                    st.success("Prediksi tersimpan. Lihat di menu Performa model dan riwayat.")
                except Exception as e:  # noqa: BLE001
                    st.error(f"Gagal menyimpan riwayat: {str(e).splitlines()[0][:200]}")


# ----------------------------------------------------------------------------
# 9. Halaman 4 - Performa model dan riwayat
# ----------------------------------------------------------------------------
NAMA_FITUR = {
    "hujan_t0": "Hujan hari ini", "hujan_lag1": "Hujan 1 hari lalu", "hujan_lag2": "Hujan 2 hari lalu",
    "hujan_lag3": "Hujan 3 hari lalu", "hujan_sum3": "Total hujan 3 hari", "hujan_sum7": "Total hujan 7 hari",
    "log_debit_t0": "Level debit hari ini (log)", "dlog_1": "Perubahan debit 1 hari",
    "dlog_3": "Perubahan debit 3 hari", "dlog_7": "Perubahan debit 7 hari",
    "dlog_mean7": "Rata-rata perubahan debit 7 hari", "bulan_sin": "Musim (sinus bulan)",
    "bulan_cos": "Musim (kosinus bulan)",
}


def halaman_performa():
    judul_halaman("activity", "Performa model dan riwayat prediksi",
                  "Evaluasi Gradient Boosting Regressor terhadap baseline persistence, serta prediksi yang pernah disimpan.")
    m = META["metrik_uji"]
    t1, t2, t3 = st.tabs(["Performa model", "Uji per kota", "Riwayat prediksi"])

    with t1:
        def turun(a, b):
            return (1 - a / b) * 100

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(kartu_kpi("MAE", fmt(m["GBR"]["MAE"], 3), f"Baseline {fmt(m['Baseline']['MAE'], 3)}. "
                              f"Lebih rendah {fmt(turun(m['GBR']['MAE'], m['Baseline']['MAE']), 1)}%.", "target",
                              satuan="m³/s"), unsafe_allow_html=True)
        c2.markdown(kartu_kpi("RMSE", fmt(m["GBR"]["RMSE"], 3), f"Baseline {fmt(m['Baseline']['RMSE'], 3)}. "
                              f"Lebih rendah {fmt(turun(m['GBR']['RMSE'], m['Baseline']['RMSE']), 1)}%.", "activity",
                              satuan="m³/s"), unsafe_allow_html=True)
        c3.markdown(kartu_kpi("R2", fmt(m["GBR"]["R2"], 3), f"Baseline {fmt(m['Baseline']['R2'], 3)}.", "chart"),
                    unsafe_allow_html=True)
        c4.markdown(kartu_kpi("Recall kejadian Siaga", fmt(m["recall_siaga"], 2),
                              "Dari 17 kejadian Siaga pada data uji. Baseline persistence: 0,41.", "alert"),
                    unsafe_allow_html=True)
        st.write("")

        g1, g2 = st.columns([1, 1.2], gap="medium")
        with g1:
            with st.container(border=True, key="card_cmp"):
                judul_seksi("Galat model dan baseline", "Semakin rendah semakin baik.")
                fig = go.Figure()
                for nama, warna in (("Baseline", "#B9C7D0"), ("GBR", TEAL)):
                    fig.add_trace(go.Bar(
                        x=["MAE", "RMSE"], y=[m[nama]["MAE"], m[nama]["RMSE"]],
                        name="Persistence" if nama == "Baseline" else "Gradient Boosting",
                        marker_color=warna, text=[fmt(m[nama]["MAE"], 2), fmt(m[nama]["RMSE"], 2)],
                        textposition="outside", cliponaxis=False))
                fig.update_layout(barmode="group")
                fig.update_yaxes(title_text="m³/s")
                tata_grafik(fig, 360)
                tampil_grafik(fig)
        with g2:
            with st.container(border=True, key="card_imp"):
                judul_seksi("Fitur yang paling berpengaruh", "Feature importance model, 12 teratas.")
                imp = pd.Series(META["feature_importance"]).sort_values(ascending=False)
                jumlah_kota = float(imp[[i for i in imp.index if i.startswith("kota_")]].sum())
                imp = imp.head(12).iloc[::-1]
                label = [NAMA_FITUR.get(i, "Kota: " + i.replace("kota_", "")) for i in imp.index]
                fig = go.Figure(go.Bar(x=imp.values, y=label, orientation="h", marker_color=TEAL,
                                       hovertemplate="%{y}<br>%{x:.3f}<extra></extra>"))
                fig.update_xaxes(title_text="Kepentingan relatif")
                fig.update_yaxes(showgrid=False)
                tata_grafik(fig, 360)
                tampil_grafik(fig)
                st.caption(f"Seluruh kolom identitas kota bersama-sama menyumbang {fmt(jumlah_kota * 100, 1)}% kepentingan.")

        st.write("")
        H('<div class="callout"><b>Catatan untuk laporan.</b> Data hanya sekitar satu tahun (12 Okt 2025 sampai 9 Okt 2026). '
          f'Data uji dimulai {tgl_id(TGL_POTONG)} dan didominasi musim kering, sehingga lonjakan besar jarang muncul. '
          'Recall Siaga dihitung dari hanya 17 kejadian, jadi selisihnya terhadap baseline belum pasti stabil. '
          'Ambang Waspada, Siaga, dan Awas berasal dari persentil debit data latih tiap kota.</div>')

    with t2:
        bt = hitung_backtest()
        uji = bt[bt["uji"]]
        with st.container(border=True, key="card_bt"):
            kol, _ = st.columns([1, 2])
            kota = kol.selectbox("Kota", KOTA, key="bt_kota")
            u = uji[uji["kota"] == kota]
            mae_g = (u["prediksi"] - u["debit_besok"]).abs().mean()
            mae_b = (u["debit"] - u["debit_besok"]).abs().mean()
            judul_seksi(f"Aktual dan prediksi di {kota}",
                        f"Periode uji {tgl_id(u['tanggal_target'].min())} sampai {tgl_id(u['tanggal_target'].max())}. "
                        f"MAE model {fmt(mae_g)} m³/s, baseline {fmt(mae_b)} m³/s.")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=u["tanggal_target"], y=u["debit_besok"], name="Aktual", mode="lines",
                                     line=dict(color=INK, width=2.2)))
            fig.add_trace(go.Scatter(x=u["tanggal_target"], y=u["prediksi"], name="Prediksi model", mode="lines",
                                     line=dict(color=TEAL, width=2, dash="solid")))
            fig.add_trace(go.Scatter(x=u["tanggal_target"], y=u["debit"], name="Baseline persistence", mode="lines",
                                     line=dict(color=SLATE, width=1.4, dash="dot")))
            fig.update_yaxes(title_text="Debit (m³/s)")
            tata_grafik(fig, 380)
            tampil_grafik(fig)

        st.write("")
        with st.container(border=True, key="card_bt_tbl"):
            judul_seksi("Ringkasan galat per kota pada data uji",
                        "Dihitung ulang dari riwayat dan model tersimpan. Angka agregat resmi ada di tab Performa model.")
            rows = []
            for k, u in uji.groupby("kota"):
                mg = (u["prediksi"] - u["debit_besok"]).abs().mean()
                mb = (u["debit"] - u["debit_besok"]).abs().mean()
                rows.append({"Kota": k, "Jumlah hari uji": len(u), "MAE model": mg, "MAE baseline": mb,
                             "Selisih (%)": (1 - mg / mb) * 100 if mb > 0 else np.nan})
            tb = pd.DataFrame(rows).sort_values("Kota")
            st.dataframe(tb, hide_index=True, height=420, column_config={
                "MAE model": st.column_config.NumberColumn(format="%.3f"),
                "MAE baseline": st.column_config.NumberColumn(format="%.3f"),
                "Selisih (%)": st.column_config.NumberColumn(format="%.1f",
                                                             help="Positif berarti model lebih baik dari baseline.")})

    with t3:
        with st.container(border=True, key="card_log"):
            judul_seksi("Riwayat prediksi tersimpan",
                        "Sumber: Berkas CSV riwayat prediksi. Menampilkan hingga 500 data terbaru.")
            try:
                log = baca_riwayat()
            except Exception as e:  # noqa: BLE001
                st.error(f"Gagal membaca riwayat dari berkas CSV: {str(e).splitlines()[0][:200]}")
                return
            if log.empty:
                H('<div class="callout"><b>Belum ada prediksi tersimpan.</b> Buka menu Prediksi debit, hitung prediksi, '
                  'lalu pilih Simpan ke riwayat.</div>')
                return
            pilih = st.multiselect("Filter kota", sorted(log["kota"].unique()), key="log_kota")
            if pilih:
                log = log[log["kota"].isin(pilih)]
            tampil = log.rename(columns={
                "id": "ID", "waktu_prediksi": "Waktu", "kota": "Kota", "tanggal_acuan": "Tanggal acuan",
                "tanggal_target": "Tanggal target", "debit_hari_ini": "Debit hari ini", "hujan_hari_ini": "Hujan hari ini",
                "hujan_sum3": "Hujan 3 hari", "hujan_sum7": "Hujan 7 hari", "prediksi_debit": "Prediksi debit",
                "baseline_debit": "Baseline", "status_risiko": "Status", "catatan": "Catatan"})
            st.dataframe(tampil, hide_index=True, height=420, column_config={
                "Debit hari ini": st.column_config.NumberColumn(format="%.2f"),
                "Hujan hari ini": st.column_config.NumberColumn(format="%.1f"),
                "Hujan 3 hari": st.column_config.NumberColumn(format="%.1f"),
                "Hujan 7 hari": st.column_config.NumberColumn(format="%.1f"),
                "Prediksi debit": st.column_config.NumberColumn(format="%.2f"),
                "Baseline": st.column_config.NumberColumn(format="%.2f")})
            st.download_button("Unduh CSV", tampil.to_csv(index=False).encode("utf-8"),
                               file_name="riwayat_prediksi.csv", mime="text/csv",
                               icon=":material/download:", key="dl_log")


# ----------------------------------------------------------------------------
# 10. Navigasi dan sidebar (Halaman Utama Default: Prediksi Debit)
# ----------------------------------------------------------------------------
p_prediksi = st.Page(halaman_prediksi, title="Prediksi debit", icon=":material/water_drop:",
                    url_path="prediksi", default=True)
p_beranda = st.Page(halaman_beranda, title="Beranda risiko", icon=":material/dashboard:", url_path="beranda")
p_eksplor = st.Page(halaman_eksplorasi, title="Eksplorasi data", icon=":material/insights:", url_path="eksplorasi")
p_performa = st.Page(halaman_performa, title="Performa dan riwayat", icon=":material/analytics:", url_path="performa")

nav = st.navigation([p_prediksi, p_beranda, p_eksplor, p_performa], position="hidden")

with st.sidebar:
    H(f'<div class="brand"><div class="brand-mark">{ikon("waves", 22)}</div>'
      f'<div><div class="brand-name">Pemantau Debit Sungai</div>'
      f'<div class="brand-sub">Prediksi 1 hari ke depan</div></div></div>')
    for pg in (p_prediksi, p_beranda, p_eksplor, p_performa):
        st.page_link(pg)
    H(f'<div class="side-note"><b>Data terakhir</b><br>{tgl_id(TGL_AKHIR)}<br><br>'
      f'<b>Penyimpanan</b><br><span class="dot" style="background:#10B981"></span>Berkas CSV aktif (22 kota)<br><br>'
      f'<b>Model</b><br>Gradient Boosting Regressor, 35 fitur</div>')

nav.run()
