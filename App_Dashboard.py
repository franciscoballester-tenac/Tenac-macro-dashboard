# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 11:11:06 2026

@author: Francisco
"""

import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
import dropbox
import io
from dropbox.common import PathRoot

# --- SISTEMA DE CONTRASEÑA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "0220": # <-- CAMBIÁ ESTA CLAVE POR LA QUE QUIERAS
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 Ingresá la contraseña para acceder al Dashboard:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 Ingresá la contraseña para acceder al Dashboard:", type="password", on_change=password_entered, key="password")
        st.error("Contraseña incorrecta. Intentá de nuevo.")
        return False
    return True

if not check_password():
    st.stop() # Esto frena la carga de los gráficos si no ponen la clave
# -----------------------------


# 1. Page Configuration
st.set_page_config(page_title="Tenac | Macro Dashboard", page_icon="📊", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Raleway:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');
* { font-family: 'Raleway', sans-serif !important; }
[data-testid="stSidebar"] { background-color: #3C3C3B !important; }
</style>
""", unsafe_allow_html=True)
st.title("Tenac Macro Dashboard")

# 2. Base Paths y Conexión a Dropbox
USE_DROPBOX_API = "DROPBOX_APP_KEY" in st.secrets

@st.cache_resource
def get_dropbox_client():
    if USE_DROPBOX_API:
        dbx = dropbox.Dropbox(
            app_key=st.secrets["DROPBOX_APP_KEY"],
            app_secret=st.secrets["DROPBOX_APP_SECRET"],
            oauth2_refresh_token=st.secrets["DROPBOX_REFRESH_TOKEN"]
        )
        # Magia para cuentas de Dropbox Business (Team Space)
        try:
            account = dbx.users_get_current_account()
            root_ns = account.root_info.root_namespace_id
            dbx = dbx.with_path_root(PathRoot.root(root_ns))
        except Exception as e:
            print(f"Aviso de Dropbox Business: {e}")
            
        return dbx
    return None

def get_file(route):
    """Devuelve el archivo listo para leer. Ya sea desde la API (BytesIO) o ruta local."""
    if USE_DROPBOX_API:
        dbx = get_dropbox_client()
        # Aseguramos que la ruta tenga el formato correcto para la API de Dropbox
        dbx_path = "/" + str(route).replace("\\", "/").lstrip("/")
        try:
            _, res = dbx.files_download(dbx_path)
            return io.BytesIO(res.content)
        except Exception as e:
            st.error(f"Error descargando {dbx_path} de Dropbox: {e}")
            raise e
    else:
        return route

if USE_DROPBOX_API:
    DB_BASE_PATH = "RESEARCH/Database"
    ISO_PATH = "RESEARCH/Database/ISO_Master_Table.xlsx"
    MACRO_MONITOR_PATH = "RESEARCH/Main Monitors/Macro Monitors/Macro_Monitor_2.xlsx"
    LOGO_PATH = "RESEARCH/Database/Claude/Logo.png"
    IT_POLITICS_PATH = "RESEARCH/Database/IT_Politics.xlsx"
    FI_MONITOR_PATH  = "RESEARCH/Main Monitors/Pricing/Fixed Income Monitor.xlsx"
else:
    def get_base_path():
        home = os.path.expanduser("~")
        possible_names = ['Tenacam Dropbox', 'Dropbox', 'Dropbox (Personal)']
        for name in possible_names:
            check_path = os.path.join(home, name)
            if os.path.exists(check_path):
                return check_path
        return os.path.join(home, 'Tenacam Dropbox')

    DROPBOX_PATH = get_base_path()
    DB_BASE_PATH = os.path.join(DROPBOX_PATH, "RESEARCH", "Database")
    ISO_PATH = os.path.join(DB_BASE_PATH, "ISO_Master_Table.xlsx")
    MACRO_MONITOR_PATH = os.path.join(DROPBOX_PATH, "RESEARCH", "Main Monitors", "Macro Monitors", "Macro_Monitor_2.xlsx")
    LOGO_PATH = os.path.join(DB_BASE_PATH, "Claude", "Logo.png")
    IT_POLITICS_PATH = os.path.join(DB_BASE_PATH, "IT_Politics.xlsx")
    FI_MONITOR_PATH  = os.path.join(DROPBOX_PATH, "RESEARCH", "Main Monitors", "Pricing", "Fixed Income Monitor.xlsx")

# 3. MASTER DICTIONARY
DATABASES = {
    "Inflation": {
        "file": "IMF/IMF_CPI_Global_iData.xlsx",
        "iso_format": "ISO3",
        "source": "IMF",
        "metrics": {
            "YoY":                                    {"sheet": "YoY",  "calc": None, "fmt": ".1f"},
            "MoM sa":                                 {"sheet": "MoM",  "calc": None, "fmt": ".1f"},
            "3m3m saar":                              {"sheet": "3m3m", "calc": None, "fmt": ".1f"},
            "Deviation from IT Center (pp)":          {"sheet": "YoY",  "calc": None, "fmt": ".1f", "loader": "it_deviation"},
            "Deviation from IT Center 3m3m (pp)":     {"sheet": "3m3m", "calc": None, "fmt": ".1f", "loader": "it_deviation_3m3m"}
        }
    },
    "Gross Domestic Product (GDP)": {
        "file": "IMF/IMF_GDP_Global_iData.xlsx",
        "iso_format": "ISO3",
        "source": "IMF",
        "metrics": {
            "GDP YoY (Year-over-Year)":    {"sheet": "GDP_NSA", "calc": "yoy_quarterly", "fmt": ".1f"},
            "GDP QoQ saar":                {"sheet": "GDP_SA",  "calc": "qoq_saar",      "fmt": ".1f"}
        }
    },
    "Balance of Payments (BOP)": {
        "file": "IMF/IMF_BOP_Global_iData.xlsx",
        "iso_format": "ISO3",
        "source": "IMF",
        "metrics": {
            "Current Account (USD millions, 4Q rolling sum)": {"sheet": "Current_Account", "calc": "roll_4q_sum_div_1m",  "fmt": ".0f"},
            "Current Account (% of GDP, 4Q rolling sum)":    {"sheet": "Current_Account", "calc": "roll_4q_sum_to_gdp",  "fmt": ".1f"},
            "Net FDI (USD millions, 4Q rolling sum)":         {"sheet": "FDI_Net",         "calc": "roll_4q_sum_div_1m",  "fmt": ".0f"},
            "Net FDI (% of GDP, 4Q rolling sum)":            {"sheet": "FDI_Net",         "calc": "roll_4q_sum_to_gdp",  "fmt": ".1f"}
        }
    },
    "International Reserves": {
        "file": "IMF/IMF_Reserves_Global_iData.xlsx",
        "iso_format": "ISO3",
        "source": "IMF",
        "metrics": {
            "Reserves (USD millions)":          {"sheet": "Reserves",       "calc": "div_1m",         "fmt": ".0f"},
            "Reserves ex. gold (USD millions)": {"sheet": "Reserves_ex_Gold","calc": "div_1m",        "fmt": ".0f"},
            "Reserves (% of GDP)":              {"sheet": "Reserves",       "calc": "reserves_to_gdp","fmt": ".1f"},
            "Reserves ex. gold (% of GDP)":     {"sheet": "Reserves_ex_Gold","calc": "reserves_to_gdp","fmt": ".1f"}
        }
    },
    "Fiscal Monitor (FM)": {
        "file": "IMF/IMF_FM_Global_iData.xlsx",
        "iso_format": "ISO3",
        "source": "IMF",
        "metrics": {
            "Revenue (% of GDP)": {"sheet": "Revenue", "calc": None, "fmt": ".1f", "drop_projections": True},
            "Expenditure (% of GDP)": {"sheet": "Expenditure", "calc": None, "fmt": ".1f", "drop_projections": True},
            "Gross Debt (% of GDP)": {"sheet": "Gross Debt", "calc": None, "fmt": ".1f", "drop_projections": True},
            "Overall Balance (% of GDP)": {"sheet": "Net Lending", "calc": None, "fmt": ".1f", "drop_projections": True},
            "Primary Balance (% of GDP)": {"sheet": "Primary Balance", "calc": None, "fmt": ".1f", "drop_projections": True}
        }
    },
    "Energy Net Exports": {
        "file": "UN - Comtrade/energy_net_exports.xlsx",
        "iso_format": "ISO3",
        "source": "UN Comtrade",
        "metrics": {
            "Total Energy Net Exports (% of GDP)": {"sheet": "Energy Net Exp USD", "calc": "annual_to_gdp", "fmt": ".1f"},
            "Oil Net Exports (% of GDP)":          {"sheet": "Oil Net Exp USD",    "calc": "annual_to_gdp", "fmt": ".1f"},
            "Natural Gas Net Exports (% of GDP)":  {"sheet": "Nat Gas Net Exp USD","calc": "annual_to_gdp", "fmt": ".1f"}
        }
    },
    "Commodity Terms of Trade": {
        "file": "IMF/IMF_CTOT_Global_iData.xlsx",
        "iso_format": "ISO3",
        "source": "IMF",
        "metrics": {
            "Terms of Trade (10Y avg = 100)": {"sheet": "Terms_of_Trade", "calc": "reer_10y_avg", "fmt": ".1f", "change": "rel"},
            "Terms of Trade Var YoY (%)":     {"sheet": "Terms_of_Trade", "calc": "yoy_monthly",  "fmt": ".1f"}
        }
    },
    "Monetary Policy Rate": {
        "file": "Tasas_Compiladas_Master.xlsx",
        "iso_format": "ISO2",
        "source": "BIS/Bloomberg",
        "metrics": {
            "Policy Rate (%)":         {"sheet": "Sheet1", "calc": None,            "fmt": ".2f"},
            "Real MPR (%)":            {"sheet": "Sheet1", "calc": "real_mpr",      "fmt": ".2f"},
            "Real MPR vs 3m3m (%)":    {"sheet": "Sheet1", "calc": "real_mpr_3m3m", "fmt": ".2f"}
        }
    },
    "Real Effective Exchange Rate": {
        "file": "REER_Compilado_BIS_IMF.xlsx",
        "iso_format": "ISO3",
        "source": "BIS/IMF",
        "metrics": {
            "REER Broad (10Y avg = 100)": {"sheet": "REER", "calc": "reer_10y_avg", "fmt": ".1f", "change": "rel"},
            "REER Var YoY (%)":           {"sheet": "YoY",  "calc": None,           "fmt": ".1f"}
        }
    },
    "FX": {
        "file": "BBG/BBG_withformulas.xlsm",
        "iso_format": "ISO3",
        "loader": "bbg_fx",
        "source": "Bloomberg",
        "metrics": {
            "FX Spot (daily)":  {"sheet": "Daily", "calc": None,     "fmt": ".2f", "change": "rel"},
            "FX Var MoM (%)":   {"sheet": "Daily", "calc": "fx_mom", "fmt": ".1f"},
            "FX Var YoY (%)":   {"sheet": "Daily", "calc": "fx_yoy", "fmt": ".1f"}
        }
    },
    "NDF Implied Depreciation (12M)": {
        "file": "BBG/BBG_withformulas.xlsm",
        "iso_format": "ISO3",
        "loader": "bbg_ndf",
        "source": "Bloomberg",
        "metrics": {
            "NDF/Spot - 1 (%)": {"sheet": "Daily", "calc": None, "fmt": ".1f"}
        }
    },
    "Local Currency 10Y Yield": {
        "file": "BBG/BBG_withformulas.xlsm",
        "iso_format": "ISO3",
        "loader": "bbg_lc10y",
        "source": "Bloomberg",
        "metrics": {
            "10Y Yield (%)": {"sheet": "Daily", "calc": None, "fmt": ".2f"}
        }
    },
    "EM Spreads (10Y)": {
        "file": "BBG/em_spreads_10Y.xlsx",
        "iso_format": "ISO2",
        "loader": "em_spreads",
        "source": "Bloomberg",
        "metrics": {
            "10Y Spread (bps)": {"sheet": "data", "calc": None, "fmt": ".0f"}
        }
    },
    "Inflation Target Deviation": {
        "file": "IMF/IMF_CPI_Global_iData.xlsx",
        "iso_format": "ISO3",
        "loader": "it_deviation",
        "source": "IMF / Own calculation",
        "metrics": {
            "Deviation from IT Center (pp)": {"sheet": "YoY", "calc": None, "fmt": ".1f"}
        }
    },
    "Inflation Target Deviation (3m3m)": {
        "file": "IMF/IMF_CPI_Global_iData.xlsx",
        "iso_format": "ISO3",
        "loader": "it_deviation_3m3m",
        "source": "IMF / Own calculation",
        "metrics": {
            "Deviation from IT Center 3m3m (pp)": {"sheet": "3m3m", "calc": None, "fmt": ".1f"}
        }
    }
}

# Cross Variable: grouped variable menu
CV_VARIABLES = {
    "Inflation": [
        ("YoY",                        "Inflation",                          "YoY"),
        ("3m3m saar",                  "Inflation",                          "3m3m saar"),
        ("MoM sa",                     "Inflation",                          "MoM sa"),
        ("Deviation from target",      "Inflation Target Deviation",         "Deviation from IT Center (pp)"),
        ("Dev. from target (3m3m)",    "Inflation Target Deviation (3m3m)",  "Deviation from IT Center 3m3m (pp)"),
    ],
    "Growth": [
        ("YoY",      "Gross Domestic Product (GDP)", "GDP YoY (Year-over-Year)"),
        ("QoQ saar", "Gross Domestic Product (GDP)", "GDP QoQ saar"),
    ],
    "External": [
        ("Current Account (% GDP)",          "Balance of Payments (BOP)", "Current Account (% of GDP, 4Q rolling sum)"),
        ("FDI (% GDP)",                      "Balance of Payments (BOP)", "Net FDI (% of GDP, 4Q rolling sum)"),
        ("Reserves (% GDP)",                 "International Reserves",    "Reserves (% of GDP)"),
        ("Energy Net Exports (% GDP)",       "Energy Net Exports",        "Total Energy Net Exports (% of GDP)"),
        ("Oil Net Exports (% GDP)",          "Energy Net Exports",        "Oil Net Exports (% of GDP)"),
        ("Natural Gas Net Exports (% GDP)",  "Energy Net Exports",        "Natural Gas Net Exports (% of GDP)"),
    ],
    "Fiscal": [
        ("Revenue (% GDP)",         "Fiscal Monitor (FM)", "Revenue (% of GDP)"),
        ("Expenditure (% GDP)",     "Fiscal Monitor (FM)", "Expenditure (% of GDP)"),
        ("Gross Debt (% GDP)",      "Fiscal Monitor (FM)", "Gross Debt (% of GDP)"),
        ("Overall Balance (% GDP)", "Fiscal Monitor (FM)", "Overall Balance (% of GDP)"),
        ("Primary Balance (% GDP)", "Fiscal Monitor (FM)", "Primary Balance (% of GDP)"),
    ],
    "Terms of Trade": [
        ("ToT (10Y avg = 100)", "Commodity Terms of Trade", "Terms of Trade (10Y avg = 100)"),
        ("ToT Var YoY (%)",     "Commodity Terms of Trade", "Terms of Trade Var YoY (%)"),
    ],
    "Monetary Policy": [
        ("Policy Rate (%)",      "Monetary Policy Rate", "Policy Rate (%)"),
        ("Real MPR (%)",         "Monetary Policy Rate", "Real MPR (%)"),
        ("Real MPR vs 3m3m (%)", "Monetary Policy Rate", "Real MPR vs 3m3m (%)"),
    ],
    "Exchange Rates": [
        ("FX MoM (%)",         "FX",                          "FX Var MoM (%)"),
        ("FX YoY (%)",         "FX",                          "FX Var YoY (%)"),
        ("REER (10Y avg=100)", "Real Effective Exchange Rate", "REER Broad (10Y avg = 100)"),
        ("REER YoY (%)",       "Real Effective Exchange Rate", "REER Var YoY (%)"),
    ],
    "Financial": [
        ("EM Spreads (bps)",          "EM Spreads (10Y)",            "10Y Spread (bps)"),
        ("LC 10Y Yield (%)",          "Local Currency 10Y Yield",    "10Y Yield (%)"),
        ("NDF Implied Dep. 12M (%)",  "NDF Implied Depreciation (12M)", "NDF/Spot - 1 (%)"),
    ],
}

# 4. Category grouping for the sidebar
CATEGORY_GROUPS = {
    "Macro":             ["Inflation", "Gross Domestic Product (GDP)"],
    "Fiscal":            ["Fiscal Monitor (FM)"],
    "External Sector":   ["Balance of Payments (BOP)", "International Reserves", "Energy Net Exports", "Commodity Terms of Trade"],
    "Monetary Policy":   ["Monetary Policy Rate"],
    "Exchange Rates":    ["Real Effective Exchange Rate", "FX"],
    "Financial Markets": ["NDF Implied Depreciation (12M)", "Local Currency 10Y Yield", "EM Spreads (10Y)"],
}

# Tenac brand color sequence
TENAC_COLORS = ["#6BBC88", "#3245B9", "#ED483F", "#4EA72E", "#A02B93", "#0E2841", "#467886", "#96607D", "#E8E8E8", "#414042"]

import plotly.io as pio                                                                                                              
pio.templates["tenac"] = go.layout.Template(layout=go.Layout(font=dict(size=14)))
pio.templates.default = "plotly_dark+tenac"


COUNTRY_VIEW_METRICS = [
    ("Macro",    "GDP Growth YoY (%)",          "Gross Domestic Product (GDP)",   "GDP YoY (Year-over-Year)",                      ".1f"),
    ("Macro",    "Inflation YoY (%)",            "Inflation",                      "YoY",                                           ".1f"),
    ("Macro",    "IT Deviation (pp)",            "Inflation Target Deviation",     "Deviation from IT Center (pp)",                 ".1f"),
    ("Fiscal",   "Primary Balance (% GDP)",      "Fiscal Monitor (FM)",            "Primary Balance (% of GDP)",                    ".1f"),
    ("Fiscal",   "Overall Balance (% GDP)",      "Fiscal Monitor (FM)",            "Overall Balance (% of GDP)",                    ".1f"),
    ("Fiscal",   "Gross Debt (% GDP)",           "Fiscal Monitor (FM)",            "Gross Debt (% of GDP)",                         ".1f"),
    ("External", "Current Account (% GDP)",      "Balance of Payments (BOP)",      "Current Account (% of GDP, 4Q rolling sum)",    ".1f"),
    ("External", "Net FDI (% GDP)",              "Balance of Payments (BOP)",      "Net FDI (% of GDP, 4Q rolling sum)",            ".1f"),
    ("External", "Reserves (% GDP)",             "International Reserves",         "Reserves (% of GDP)",                           ".1f"),
    ("External", "Energy Net Exports (% GDP)",   "Energy Net Exports",             "Total Energy Net Exports (% of GDP)",           ".1f"),
    ("External", "Commodity ToT YoY (%)",        "Commodity Terms of Trade",       "Terms of Trade Var YoY (%)",                    ".1f"),
    ("Monetary", "Policy Rate (%)",              "Monetary Policy Rate",           "Policy Rate (%)",                               ".2f"),
    ("Monetary", "Real MPR (%)",                 "Monetary Policy Rate",           "Real MPR (%)",                                  ".2f"),
    ("FX",       "REER (10Y avg = 100)",         "Real Effective Exchange Rate",   "REER Broad (10Y avg = 100)",                    ".1f"),
    ("FX",       "FX YoY (%)",                   "FX",                             "FX Var YoY (%)",                                ".1f"),
    ("Financial","NDF Implied Dep. (%)",         "NDF Implied Depreciation (12M)", "NDF/Spot - 1 (%)",                              ".1f"),
    ("Financial","LC 10Y Yield (%)",             "Local Currency 10Y Yield",       "10Y Yield (%)",                                 ".2f"),
    ("Financial","EM Spread (bps)",              "EM Spreads (10Y)",               "10Y Spread (bps)",                              ".0f"),
]

# 5. Country groups
COUNTRY_GROUPS = {
    "All":          [], 
    "EM":           ["ARG","BRA","CHL","COL","MEX","PER","URY","PRY","BOL","CRI","DOM","GTM","HND","JAM","PAN","TTO","SLV",
                     "ECU","NIC","GUY","SUR","BLZ","HTI","BRB","ATG","DMA","GRD","LCA","VCT","KNA","VEN",
                     "POL","HUN","CZE","ROU","SRB","UKR","TUR","RUS","BGR","ALB","MKD","MNE","MDA","BIH","BLR","KOS","GEO","AZE",
                     "ZAF","NGA","GHA","KEN","TZA","EGY","MAR","CIV","ETH","AGO","CMR","TUN","DZA","SDN","MOZ","ZMB","ZWE",
                     "UGA","RWA","SEN","COD","COG","GAB","GNQ","BWA","NAM","MUS","MLI","NER","BFA","GIN","GMB","SLE",
                     "LBR","TGO","BEN","SOM","DJI","MWI","LSO","SWZ","CPV","SYC","GNB","BDI",
                     "CHN","IND","IDN","KOR","MYS","PHL","THA","VNM","PAK","LKA","KAZ","UZB","ARM","MNG",
                     "BGD","KHM","MMR","NPL","LAO","KGZ","TJK","BRN","MDV","TLS",
                     "SAU","QAT","OMN","BHR","ARE","KWT","JOR","IRN","IRQ","LBN","YEM"],
    "DM":           ["USA","CAN","GBR","DEU","FRA","ITA","ESP","NLD","BEL","CHE","SWE","NOR","DNK","FIN","AUT","PRT","IRL","GRC",
                     "JPN","AUS","NZL","SGP","HKG","ISR",
                     "HRV","SVK","SVN","EST","LVA","LTU","CYP","MLT","LUX","ISL"],
    "Latam":        ["ARG","BRA","CHL","COL","MEX","PER","URY","PRY","BOL","ECU","VEN","GUY","SUR"],
    "C. America & Carib.": ["CRI","DOM","GTM","HND","JAM","PAN","TTO","SLV","NIC","BLZ","HTI",
                            "BRB","ATG","DMA","GRD","LCA","VCT","KNA","ABW","CUW","SXM","VGB","MSR"],
    "EM Europe":    ["POL","HUN","CZE","ROU","SRB","UKR","TUR","RUS","BGR","ALB","MKD","MNE","MDA","BIH","BLR","KOS","GEO","AZE"],
    "Middle East":  ["SAU","QAT","OMN","BHR","ARE","KWT","JOR","ISR","IRN","IRQ","LBN","SYR","YEM","DZA","LBY","WBG"],
    "Africa":       ["ZAF","NGA","GHA","KEN","TZA","EGY","MAR","CIV","ETH","AGO","CMR","TUN","DZA","SDN","SSD","MOZ","ZMB",
                     "ZWE","UGA","RWA","SEN","COD","COG","GAB","GNQ","BWA","NAM","MUS","MLI","NER","BFA","GIN","GMB",
                     "SLE","LBR","TGO","BEN","CAF","SOM","DJI","MWI","LSO","SWZ","STP","CPV","COM","SYC","GNB","BDI","LBY"],
    "EM Asia":      ["CHN","IND","IDN","KOR","MYS","PHL","THA","VNM","PAK","LKA","KAZ","UZB","ARM","MNG",
                     "BGD","KHM","MMR","NPL","LAO","KGZ","TJK","BRN","MDV","TLS","BTN","FJI","MNG"],
    "DM Europe":    ["GBR","DEU","FRA","ITA","ESP","NLD","BEL","CHE","SWE","NOR","DNK","FIN","AUT","PRT","IRL","GRC",
                     "HRV","SVK","SVN","EST","LVA","LTU","CYP","MLT","LUX","ISL"],
    "DM Asia-Pac":  ["JPN","AUS","NZL","SGP","HKG"],
    "DM Americas":  ["USA","CAN"],
}

# Group category taxonomy for the tiered selector
GROUP_CATEGORIES = {
    "Broad":      ["All", "EM", "DM"],
    "Geographic": ["Latam", "C. America & Carib.", "EM Europe", "Middle East",
                   "Africa", "EM Asia", "DM Europe", "DM Asia-Pac", "DM Americas"],
    "Tradeable":  ["Any Tradeable", "Has FX Data", "Has NDF Data", "Has LC Yield", "Has EM Spread"],
    "Credit Rating": [],   # populated at runtime after loading FI Monitor
}

# S&P rating scale, best → worst quality
RATING_ORDER = [
    "AAA",
    "AA+", "AA", "AA-",
    "A+",  "A",  "A-",
    "BBB+", "BBB", "BBB-",
    "BB+",  "BB",  "BB-",
    "B+",   "B",   "B-",
    "CCC+", "CCC", "CCC-",
    "CC", "C", "SD", "RD", "D",
]

def _resolve_group(group_name, iso3_map, available):
    """Map a COUNTRY_GROUPS key to a list of country names present in `available`."""
    if group_name == "All":
        return list(available)
    names = []
    for code in COUNTRY_GROUPS.get(group_name, []):
        mapped = iso3_map.get(code)        # geographic groups store ISO3 codes
        if mapped and mapped in available:
            names.append(mapped)
        elif code in available:            # tradeable groups store country names directly
            names.append(code)
    return names

# ─────────────────────────────────────────────
# Helper: detecta cuántas filas de metadata saltar
# ─────────────────────────────────────────────
def _get_skiprows(source, sheet_name=0):
    """Detecta dinámicamente skiprows para archivos con o sin metadata header."""
    _meta = {'description', 'source', 'unit', 'frequency', 'sa'}
    if hasattr(source, 'seek'):
        source.seek(0)
    _peek = pd.read_excel(source, sheet_name=sheet_name, nrows=10, header=None)
    if hasattr(source, 'seek'):
        source.seek(0)
    return next((i for i, v in enumerate(_peek.iloc[:, 0]) if str(v).strip().lower() not in _meta), 0)

# 5. Cached loading functions
@st.cache_data
def load_iso_mapping(iso_route):
    try:
        df_iso = pd.read_excel(get_file(iso_route), usecols="A:C")
        df_iso = df_iso.astype(str).apply(lambda x: x.str.strip())
        iso3_map = dict(zip(df_iso.iloc[:, 1], df_iso.iloc[:, 0]))
        iso2_map = dict(zip(df_iso.iloc[:, 2], df_iso.iloc[:, 0]))
        return {"ISO3": iso3_map, "ISO2": iso2_map}
    except Exception as e:
        st.sidebar.warning(f"⚠️ Could not read ISO table: {e}")
        return {"ISO3": {}, "ISO2": {}}

@st.cache_data
def load_and_transform_data(route, sheet, iso_mapping, iso_format, calc_type=None, gdp_route=None, drop_projections=False):
    source = get_file(route)
    _skip = _get_skiprows(source, sheet)
    df = pd.read_excel(source, sheet_name=sheet, index_col=0, skiprows=_skip)

    df = df[df.index.notna()]
    if pd.api.types.is_numeric_dtype(df.index):
        df.index = pd.to_datetime(df.index.astype(int).astype(str))
    else:
        df.index = pd.to_datetime(df.index)
        
    df = df.sort_index()
    df.columns = [str(c).strip() for c in df.columns]

    if drop_projections:
        current_year = pd.Timestamp.now().year
        df = df[df.index.year < current_year]

    if calc_type == "yoy_quarterly":
        df = ((df / df.shift(4)) - 1) * 100
    elif calc_type == "qoq_saar":
        df = (((df / df.shift(1)) ** 4) - 1) * 100
    elif calc_type == "div_1m":
        df = df / 1_000_000
    elif calc_type == "roll_4q_sum_div_1m":
        df = df.rolling(window=4).sum() / 1_000_000
    elif calc_type == "reer_10y_avg":
        ref_mean = df.tail(120).mean()
        df = (df / ref_mean) * 100
    elif calc_type == "yoy_monthly":
        df = df.pct_change(12) * 100
    elif calc_type in ["reserves_to_gdp", "roll_4q_sum_to_gdp", "annual_to_gdp"]:
        df_target = df.rolling(window=4).sum() if calc_type == "roll_4q_sum_to_gdp" else df
        if gdp_route:
            try:
                df_gdp = pd.read_excel(get_file(gdp_route), sheet_name="GDP_USD")
                df_gdp = df_gdp.set_index('ISO')
                df_gdp.index = [str(i).strip() for i in df_gdp.index]
                year_cols = [c for c in df_gdp.columns if str(c).isdigit()]
                df_gdp_years = df_gdp[year_cols].copy()
                df_gdp_years.columns = df_gdp_years.columns.astype(int)
                
                df_ratio = pd.DataFrame(index=df_target.index, columns=df_target.columns)
                for year in df_target.index.year.unique():
                    if year in df_gdp_years.columns:
                        mask = df_target.index.year == year
                        df_ratio.loc[mask] = df_target.loc[mask].divide(df_gdp_years[year], axis=1) * 100
                df = df_ratio.astype(float)
            except Exception as e:
                st.error(f"Error processing GDP: {e}")

    if iso_mapping:
        df.rename(columns=iso_mapping, inplace=True)
    return df

@st.cache_data
def load_real_mpr(mpr_route, cpi_route, iso2_mapping, iso3_mapping, cpi_sheet="YoY"):
    src_mpr = get_file(mpr_route)
    df_mpr = pd.read_excel(src_mpr, sheet_name="Sheet1", index_col=0,
                           skiprows=_get_skiprows(src_mpr, "Sheet1"))
    df_mpr.index = pd.to_datetime(df_mpr.index)
    df_mpr = df_mpr.sort_index()
    df_mpr.columns = [str(c).strip() for c in df_mpr.columns]
    try:
        df_mpr = df_mpr.resample('ME').last()
    except ValueError:
        df_mpr = df_mpr.resample('M').last()
    df_mpr.index = df_mpr.index.to_period('M').to_timestamp()
    if iso2_mapping:
        df_mpr.rename(columns=iso2_mapping, inplace=True)

    src_cpi = get_file(cpi_route)
    df_cpi = pd.read_excel(src_cpi, sheet_name=cpi_sheet, index_col=0,
                           skiprows=_get_skiprows(src_cpi, cpi_sheet))
    df_cpi.index = pd.to_datetime(df_cpi.index)
    df_cpi = df_cpi.sort_index()
    df_cpi.columns = [str(c).strip() for c in df_cpi.columns]
    df_cpi.index = df_cpi.index.to_period('M').to_timestamp()
    if iso3_mapping:
        df_cpi.rename(columns=iso3_mapping, inplace=True)

    common_countries = sorted(
        [c for c in df_mpr.columns if c in df_cpi.columns and str(c) != "nan"],
        key=str.casefold
    )
    if not common_countries:
        return pd.DataFrame()

    df_cpi_aligned = df_cpi[common_countries].reindex(df_mpr.index).ffill(limit=3)
    i  = df_mpr[common_countries] / 100
    pi = df_cpi_aligned / 100
    return ((1 + i) / (1 + pi) - 1) * 100

@st.cache_data
def load_bbg_indicator_raw(route, indicator):
    df_raw = pd.read_excel(get_file(route), sheet_name='Daily', header=None)
    code_row      = df_raw.iloc[2]
    indicator_row = df_raw.iloc[4]
    cols = [j for j in range(1, len(indicator_row)) if str(indicator_row[j]).strip() == indicator]
    dates  = pd.to_datetime(df_raw.iloc[6:, 0], errors='coerce')
    values = df_raw.iloc[6:, cols].copy()
    values.columns = [str(code_row[j]).strip() for j in cols]
    values.index = dates
    values = values.loc[values.index.notna()].sort_index()
    values = values.apply(pd.to_numeric, errors='coerce')
    values = values[[c for c in values.columns if c.lower() != 'nan']]
    return values

def transform_bbg_fx(df_raw, iso_mapping, calc_type):
    values = df_raw.copy()
    if calc_type in ('fx_mom', 'fx_yoy'):
        try:
            df_monthly = values.resample('ME').last()
        except ValueError:
            df_monthly = values.resample('M').last()
        df_monthly.index = df_monthly.index.to_period('M').to_timestamp()
        values = df_monthly.pct_change(1) * 100 if calc_type == 'fx_mom' else df_monthly.pct_change(12) * 100
    if iso_mapping:
        values = values.rename(columns=iso_mapping)
    return values

@st.cache_data
def load_em_spreads(route, iso_mapping):
    df_raw = pd.read_excel(get_file(route), sheet_name='data', header=None)
    codes  = [str(c).strip() for c in df_raw.iloc[3, 1:].tolist()]
    dates  = pd.to_datetime(df_raw.iloc[4:, 0], errors='coerce')
    values = df_raw.iloc[4:, 1:].copy()
    values.columns = codes
    values.index = dates
    values = values.loc[values.index.notna()].sort_index()
    values = values.apply(pd.to_numeric, errors='coerce')

    if iso_mapping:
        values.rename(columns=iso_mapping, inplace=True)
    return values

@st.cache_data(ttl=0)
def load_it_targets(it_route):
    """Returns DataFrame indexed by ISO3 with columns: Centro, Piso, Techo, Tipo (all in %)."""
    df_it = pd.read_excel(get_file(it_route), sheet_name="IT")
    df_it.columns = [str(c).strip() for c in df_it.columns]
    # Use positional columns: 0=ISO3, 2=Centro, 3=Piso, 4=Techo, 5=Tipo
    df_it = df_it.iloc[:, [0, 2, 3, 4, 5]].copy()
    df_it.columns = ["ISO3", "Centro", "Piso", "Techo", "Tipo"]
    df_it["ISO3"] = df_it["ISO3"].astype(str).str.strip()
    df_it = df_it[df_it["ISO3"].notna() & (df_it["ISO3"] != "nan") & (df_it["ISO3"] != "")]
    df_it = df_it.set_index("ISO3")
    for col in ["Centro", "Piso", "Techo"]:
        df_it[col] = pd.to_numeric(df_it[col], errors="coerce") * 100  # to %
    return df_it

@st.cache_data(ttl=0)
def load_it_deviation(cpi_route, it_route, iso3_mapping, cpi_sheet="YoY"):
    """Returns DataFrame of (CPI - IT center) for all IT countries."""
    df_targets = load_it_targets(it_route)
    src_cpi = get_file(cpi_route)
    _skip = _get_skiprows(src_cpi, cpi_sheet)
    df_cpi = pd.read_excel(src_cpi, sheet_name=cpi_sheet, index_col=0, skiprows=_skip)
    df_cpi.index = pd.to_datetime(df_cpi.index)
    df_cpi = df_cpi.sort_index()
    df_cpi.columns = [str(c).strip() for c in df_cpi.columns]
    if iso3_mapping:
        df_cpi.rename(columns=iso3_mapping, inplace=True)
    result = pd.DataFrame(index=df_cpi.index)
    for iso3, row in df_targets.iterrows():
        country_name = iso3_mapping.get(iso3)
        if country_name and country_name in df_cpi.columns and pd.notna(row["Centro"]):
            result[country_name] = df_cpi[country_name] - row["Centro"]
    return result

def load_df_for_metric(db_key, metric_key):
    db_cfg     = DATABASES[db_key]
    file_route = os.path.join(DB_BASE_PATH, db_cfg["file"]).replace("\\", "/")
    iso_format = db_cfg["iso_format"]
    loader     = db_cfg.get("loader", "default")
    m_cfg      = db_cfg["metrics"][metric_key]
    metric_loader = m_cfg.get("loader", loader)

    try:
        if loader == "bbg_fx":
            return transform_bbg_fx(load_bbg_indicator_raw(file_route, "FX"), iso_dicts[iso_format], m_cfg["calc"])
        if loader == "bbg_lc10y":
            return load_bbg_indicator_raw(file_route, "LC10y").rename(columns=iso_dicts[iso_format])
        if loader == "bbg_ndf":
            df_ndf = load_bbg_indicator_raw(file_route, "NDF")
            df_fx  = load_bbg_indicator_raw(file_route, "FX")
            common = [c for c in df_ndf.columns if c in df_fx.columns]
            df = ((df_ndf[common] / df_fx[common].reindex(df_ndf.index, method="ffill")) - 1) * 100
            return df.rename(columns=iso_dicts[iso_format])
        if loader == "em_spreads":
            return load_em_spreads(file_route, iso_dicts[iso_format])
        if metric_loader == "it_deviation":
            return load_it_deviation(file_route, IT_POLITICS_PATH, iso_dicts["ISO3"])
        if metric_loader == "it_deviation_3m3m":
            return load_it_deviation(file_route, IT_POLITICS_PATH, iso_dicts["ISO3"], cpi_sheet="3m3m")
        if m_cfg["calc"] == "real_mpr":
            cpi_route = os.path.join(DB_BASE_PATH, "IMF/IMF_CPI_Global_iData.xlsx").replace("\\", "/")
            return load_real_mpr(file_route, cpi_route, iso_dicts["ISO2"], iso_dicts["ISO3"])
        if m_cfg["calc"] == "real_mpr_3m3m":
            cpi_route = os.path.join(DB_BASE_PATH, "IMF/IMF_CPI_Global_iData.xlsx").replace("\\", "/")
            return load_real_mpr(file_route, cpi_route, iso_dicts["ISO2"], iso_dicts["ISO3"], cpi_sheet="3m3m")
        return load_and_transform_data(
            file_route, m_cfg["sheet"], iso_dicts[iso_format],
            iso_format, m_cfg.get("calc"), MACRO_MONITOR_PATH,
            m_cfg.get("drop_projections", False)
        )
    except Exception as e:
        return pd.DataFrame()


@st.cache_data
def load_tradeable_groups(bbg_route, em_spreads_route, iso2_map, iso3_map):
    """Build data-driven country groups from BBG and EM Spreads datasets."""
    def _map(codes, iso_map):
        out = set()
        for c in codes:
            name = iso_map.get(str(c).strip())
            if name and str(name) != "nan":
                out.add(name)
        return sorted(out, key=str.casefold)

    groups = {}
    try:
        src = get_file(bbg_route)
        hdr = pd.read_excel(src, sheet_name="Daily", header=None, nrows=6)
        code_row = hdr.iloc[2]
        ind_row  = hdr.iloc[4]
        for ind, group_name in [
            ("FX",    "Has FX Data"),
            ("NDF",   "Has NDF Data"),
            ("LC10y", "Has LC Yield"),
        ]:
            cols  = [j for j in range(1, len(ind_row)) if str(ind_row[j]).strip() == ind]
            codes = [str(code_row[j]).strip() for j in cols]
            groups[group_name] = _map(codes, iso3_map)
    except Exception:
        pass

    try:
        src = get_file(em_spreads_route)
        hdr = pd.read_excel(src, sheet_name="data", header=None, nrows=4)
        codes = [str(c).strip() for c in hdr.iloc[3, 1:].tolist()]
        groups["Has EM Spread"] = _map(codes, iso2_map)
    except Exception:
        pass

    if groups:
        groups["Any Tradeable"] = sorted(
            set().union(*groups.values()), key=str.casefold
        )
    return groups


@st.cache_data
def load_rating_groups(fi_route, iso3_map):
    """Group ISO3 countries by S&P credit rating from Fixed Income Monitor."""
    try:
        src = get_file(fi_route)
        df = pd.read_excel(src, sheet_name="10Y (hardcoded)", header=1, usecols=[0, 5])
        df.columns = ["ISO3", "Rating"]
        df = df[df["ISO3"].notna() & df["Rating"].notna()].copy()
        df["ISO3"]   = df["ISO3"].astype(str).str.strip()
        df["Rating"] = df["Rating"].astype(str).str.strip()
        # Keep only valid 3-letter ISO3 codes (skip city-level entries like "AbuDh")
        df = df[df["ISO3"].str.match(r"^[A-Z]{3}$")]
        groups = {}
        for rating, grp in df.groupby("Rating"):
            codes = [c for c in grp["ISO3"].tolist() if c in iso3_map]
            if codes:
                groups[str(rating)] = codes
        return groups
    except Exception:
        return {}


# 5. MAIN APP LOGIC
iso_dicts = load_iso_mapping(ISO_PATH)

try:
    _bbg_r = os.path.join(DB_BASE_PATH, "BBG/BBG_withformulas.xlsm").replace("\\", "/")
    _spr_r = os.path.join(DB_BASE_PATH, "BBG/em_spreads_10Y.xlsx").replace("\\", "/")
    COUNTRY_GROUPS.update(load_tradeable_groups(_bbg_r, _spr_r, iso_dicts["ISO2"], iso_dicts["ISO3"]))
except Exception:
    pass

try:
    _rating_groups = load_rating_groups(FI_MONITOR_PATH, iso_dicts["ISO3"])
    COUNTRY_GROUPS.update(_rating_groups)
    GROUP_CATEGORIES["Credit Rating"] = [r for r in RATING_ORDER if r in _rating_groups]
except Exception:
    pass

try:
    if USE_DROPBOX_API:
        st.sidebar.image(get_file(LOGO_PATH), use_container_width=True)
    elif os.path.exists(LOGO_PATH):
        st.sidebar.image(LOGO_PATH, use_container_width=True)
except Exception:
    pass

st.sidebar.divider()
view_mode = st.sidebar.radio("", ["📊 Variable View", "🌍 Country View", "🔀 Cross Variable", "🎯 IT Tracker"],
                             horizontal=True, label_visibility="collapsed")
st.sidebar.divider()

# ── COUNTRY VIEW ──────────────────────────────────────────────────────────────
if view_mode == "🌍 Country View":
    all_country_names = sorted(
        {n for n in list(iso_dicts["ISO3"].values()) + list(iso_dicts["ISO2"].values()) if str(n) != "nan"},
        key=str.casefold
    )
    selected_country = st.sidebar.selectbox("🌍 Select Country:", all_country_names)

    st.markdown(f"## {selected_country}")
    st.caption("Latest available data · sparklines show last 5 years")
    st.divider()

    prev_cat  = None

    for cat, label, db_key, metric_key, fmt in COUNTRY_VIEW_METRICS:
        if cat != prev_cat:
            if prev_cat is not None:
                st.markdown("<hr style='margin:4px 0; border-color:#333;'>", unsafe_allow_html=True)
            st.markdown(
                f"<div style='color:#6BBC88; font-weight:600; font-size:0.82em; "
                f"letter-spacing:0.08em; margin:6px 0 2px 0;'>{cat.upper()}</div>",
                unsafe_allow_html=True
            )
            prev_cat = cat

        col_metric, col_val, col_date, col_spark = st.columns([2.5, 0.8, 1.0, 2.5])
        df_m = load_df_for_metric(db_key, metric_key)

        if df_m.empty or selected_country not in df_m.columns:
            col_metric.write(label)
            col_val.write("—")
            col_date.write("—")
            continue

        series = df_m[selected_country].dropna()
        if series.empty:
            col_metric.write(label)
            col_val.write("—")
            col_date.write("—")
            continue

        last_val  = series.iloc[-1]
        last_date = series.index[-1]
        date_str  = (str(last_date.year)
                     if (last_date.month == 1 and last_date.day == 1)
                     else last_date.strftime("%b %Y"))

        col_metric.write(label)
        col_val.write(f"{last_val:{fmt}}")
        col_date.write(date_str)

        cutoff = last_date - pd.DateOffset(years=4)
        spark = series[series.index >= cutoff]
        if not spark.empty:
            fig_s = go.Figure(go.Scatter(
                x=spark.index, y=spark.values, mode="lines",
                line=dict(color="#6BBC88", width=1.5),
            ))
            fig_s.update_layout(
                margin=dict(l=0, r=0, t=2, b=2), height=55,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(visible=False), yaxis=dict(visible=False),
                showlegend=False,
                shapes=[dict(
                    type="line", xref="paper", yref="y",
                    x0=0, x1=1, y0=0, y1=0,
                    line=dict(color="rgba(255,255,255,0.35)", width=1)
                )],
            )
            col_spark.plotly_chart(fig_s, use_container_width=True,
                                   config={"displayModeBar": False},
                                   key=f"spark_{db_key}_{metric_key}")

    st.stop()

# ── CROSS VARIABLE VIEW ───────────────────────────────────────────────────────
if view_mode == "🔀 Cross Variable":
    cv_cat_list = list(CV_VARIABLES.keys())

    st.sidebar.header("⚙️ Variables")
    st.sidebar.markdown("**Variable X (horizontal axis):**")
    xcv_cat  = st.sidebar.selectbox("xcv_cat", cv_cat_list, label_visibility="collapsed", key="cvx_cat")
    xcv_opts = {label: (db, met) for label, db, met in CV_VARIABLES[xcv_cat]}
    xcv_label = st.sidebar.selectbox("xcv_met", list(xcv_opts.keys()), label_visibility="collapsed", key="cvx_met")
    xdb, xmet = xcv_opts[xcv_label]

    st.sidebar.markdown("**Variable Y (vertical axis):**")
    ycv_cat  = st.sidebar.selectbox("ycv_cat", cv_cat_list, label_visibility="collapsed", key="cvy_cat", index=min(1, len(cv_cat_list)-1))
    ycv_opts = {label: (db, met) for label, db, met in CV_VARIABLES[ycv_cat]}
    ycv_label = st.sidebar.selectbox("ycv_met", list(ycv_opts.keys()), label_visibility="collapsed", key="cvy_met")
    ydb, ymet = ycv_opts[ycv_label]

    st.sidebar.divider()
    st.sidebar.header("🌍 Countries")

    df_x = load_df_for_metric(xdb, xmet)
    df_y = load_df_for_metric(ydb, ymet)

    valid_names_cv = set(iso_dicts["ISO3"].values()) | set(iso_dicts["ISO2"].values())
    valid_names_cv.discard("nan")
    common_countries = sorted(
        [c for c in df_x.columns if c in df_y.columns and str(c) in valid_names_cv],
        key=str.casefold
    )

    cv_sc_key = "cv_countries"
    if cv_sc_key in st.session_state:
        st.session_state[cv_sc_key] = [c for c in st.session_state[cv_sc_key] if c in common_countries]

    _avail_cats_cv = [k for k in GROUP_CATEGORIES if GROUP_CATEGORIES[k]]
    _cv_grp_type = st.sidebar.radio("", _avail_cats_cv, horizontal=True,
                                    label_visibility="collapsed", key="cv_grp_type")
    _cv_grp_opts = ["—"] + [g for g in GROUP_CATEGORIES[_cv_grp_type] if g in COUNTRY_GROUPS]
    cv_group = st.sidebar.selectbox("", _cv_grp_opts, label_visibility="collapsed", key="cv_grp")
    col_add, col_clear = st.sidebar.columns(2)
    if col_add.button("➕ Add", key="cv_add"):
        if cv_group != "—":
            names_to_add = _resolve_group(cv_group, iso_dicts["ISO3"], common_countries)
            st.session_state[cv_sc_key] = sorted(
                set(st.session_state.get(cv_sc_key, [])) | set(names_to_add), key=str.casefold
            )
    if col_clear.button("🗑️ Clear", key="cv_clear"):
        st.session_state[cv_sc_key] = []

    cv_countries = st.sidebar.multiselect("Select countries:", options=common_countries, key=cv_sc_key)

    x_label = f"{xcv_cat} · {xcv_label}"
    y_label = f"{ycv_cat} · {ycv_label}"
    st.markdown("### Cross Variable")
    st.caption(f"X: {x_label}  ·  Y: {y_label}")

    tab_scatter, tab_dual = st.tabs(["🔵 Scatter", "↔️ Dual Axis"])

    with tab_scatter:
        if not cv_countries:
            st.warning("👈 Please select at least one country.")
        elif df_x.empty or df_y.empty:
            st.warning("Could not load data for one or both variables.")
        else:
            col_date, col_tol = st.columns([2, 1])
            all_min = min(
                df_x[[c for c in cv_countries if c in df_x.columns]].dropna(how="all").index.min(),
                df_y[[c for c in cv_countries if c in df_y.columns]].dropna(how="all").index.min()
            )
            ref_default = pd.Timestamp.today()

            ref_date   = col_date.date_input("Reference date:", value=ref_default.date(),
                                             min_value=all_min.date(),
                                             max_value=pd.Timestamp.today().date(), key="cv_refdate")
            tol_months = col_tol.selectbox("Stale data warning (months):", [6, 12, 24, 36], index=1, key="cv_tol")
            ref_ts = pd.Timestamp(ref_date)

            rows = []
            for country in cv_countries:
                sx = df_x[country].dropna() if country in df_x.columns else pd.Series(dtype=float)
                sy = df_y[country].dropna() if country in df_y.columns else pd.Series(dtype=float)
                wx = sx[sx.index <= ref_ts]
                wy = sy[sy.index <= ref_ts]
                xv = wx.iloc[-1] if not wx.empty else None
                yv = wy.iloc[-1] if not wy.empty else None
                if xv is not None and yv is not None:
                    xd = wx.index[-1]
                    yd = wy.index[-1]
                    stale = ((ref_ts - xd).days > tol_months * 30 or
                             (ref_ts - yd).days > tol_months * 30)
                    rows.append({"country": country, "x_val": xv, "y_val": yv,
                                 "x_date": xd.strftime("%b %Y"),
                                 "y_date": yd.strftime("%b %Y"),
                                 "stale": stale})

            if not rows:
                st.warning(f"No data available before {ref_date}.")
            else:
                sdf  = pd.DataFrame(rows)
                xfmt = DATABASES[xdb]["metrics"][xmet].get("fmt", ".2f")
                yfmt = DATABASES[ydb]["metrics"][ymet].get("fmt", ".2f")

                fresh = sdf[~sdf["stale"]]
                stale = sdf[sdf["stale"]]

                fig_sc = go.Figure()
                for subset, color, opacity, name in [
                    (fresh, "#6BBC88", 1.0,  "Current"),
                    (stale, "#96607D", 0.55, f"Stale (> {tol_months}m old)"),
                ]:
                    if subset.empty:
                        continue
                    fig_sc.add_trace(go.Scatter(
                        x=subset["x_val"], y=subset["y_val"],
                        mode="markers+text",
                        name=name,
                        text=subset["country"],
                        textposition="top center",
                        textfont=dict(size=11, color="white"),
                        marker=dict(size=9, color=color, opacity=opacity),
                        customdata=subset[["x_date", "y_date"]].values,
                        hovertemplate=(
                            "<b>%{text}</b><br>"
                            f"X: %{{x:{xfmt}}} (%{{customdata[0]}})<br>"
                            f"Y: %{{y:{yfmt}}} (%{{customdata[1]}})"
                            "<extra></extra>"
                        )
                    ))
                fig_sc.update_layout(xaxis_title=x_label, yaxis_title=y_label, hovermode="closest")
                fig_sc.update_xaxes(gridcolor="rgba(255,255,255,0.1)", zeroline=True,
                                    zerolinecolor="rgba(255,255,255,0.35)", zerolinewidth=1)
                fig_sc.update_yaxes(gridcolor="rgba(255,255,255,0.1)", zeroline=True,
                                    zerolinecolor="rgba(255,255,255,0.35)", zerolinewidth=1)
                st.plotly_chart(fig_sc, use_container_width=True)
                n_stale = sdf["stale"].sum()
                st.caption(f"{len(sdf)}/{len(cv_countries)} countries with data · "
                           f"{n_stale} with data older than {tol_months} months (shown faded)")

    with tab_dual:
        if not cv_countries:
            st.warning("👈 Please select at least one country.")
        elif df_x.empty or df_y.empty:
            st.warning("Could not load data for one or both variables.")
        else:
            def to_monthly_ffill(df, countries):
                cols = [c for c in countries if c in df.columns]
                if not cols:
                    return pd.DataFrame()
                try:
                    return df[cols].resample('ME').last().ffill(limit=12)
                except ValueError:
                    return df[cols].resample('M').last().ffill(limit=12)

            mx = to_monthly_ffill(df_x, cv_countries)
            my = to_monthly_ffill(df_y, cv_countries)

            if mx.empty or my.empty:
                st.warning("No data available.")
            else:
                common_idx = mx.index.intersection(my.index)
                if common_idx.empty:
                    st.warning("No overlapping date range between the two variables.")
                else:
                    mx = mx.loc[common_idx]
                    my = my.loc[common_idx]
                    min_d = common_idx.min().to_pydatetime()
                    max_d = common_idx.max().to_pydatetime()
                    default_start = max(min_d, (pd.Timestamp(max_d) - pd.DateOffset(years=5)).to_pydatetime())
                    dates = st.slider("📅 Time filter:", min_value=min_d, max_value=max_d,
                                      value=(default_start, max_d), format="YYYY-MM", key="cv_slider")
                    mx_slice = mx.loc[dates[0]:dates[1]]
                    my_slice = my.loc[dates[0]:dates[1]]

                    xfmt = DATABASES[xdb]["metrics"][xmet].get("fmt", ".2f")
                    yfmt = DATABASES[ydb]["metrics"][ymet].get("fmt", ".2f")

                    fig_dual = go.Figure()
                    for i, country in enumerate(cv_countries):
                        color = TENAC_COLORS[i % len(TENAC_COLORS)]
                        if country in mx_slice.columns:
                            fig_dual.add_trace(go.Scatter(
                                x=mx_slice.index, y=mx_slice[country],
                                name=f"{country} · {xmet}",
                                line=dict(color=color, width=2),
                                yaxis="y1",
                                hovertemplate=f"{country} (X): %{{y:{xfmt}}}<extra></extra>"
                            ))
                        if country in my_slice.columns:
                            fig_dual.add_trace(go.Scatter(
                                x=my_slice.index, y=my_slice[country],
                                name=f"{country} · {ymet}",
                                line=dict(color=color, width=2, dash="dash"),
                                yaxis="y2",
                                hovertemplate=f"{country} (Y): %{{y:{yfmt}}}<extra></extra>"
                            ))

                    fig_dual.update_layout(
                        yaxis =dict(title=x_label, gridcolor="rgba(255,255,255,0.1)"),
                        yaxis2=dict(title=y_label, overlaying="y", side="right",
                                    gridcolor="rgba(255,255,255,0.0)"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        hovermode="x unified",
                        xaxis_title=""
                    )
                    st.plotly_chart(fig_dual, use_container_width=True)
                    st.caption("Solid lines = Variable X (left axis) · Dashed lines = Variable Y (right axis) · "
                               "Low-frequency series forward-filled to monthly.")

    st.stop()

# ── IT TRACKER ────────────────────────────────────────────────────────────────
if view_mode == "🎯 IT Tracker":
    st.markdown("### 🎯 Inflation Target Tracker")
    st.caption("Deviation of latest CPI YoY from the center of each country's inflation target")

    def _hex_to_rgba(hex_color, alpha=0.15):
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        return f"rgba({r},{g},{b},{alpha})"

    try:
        df_it_targets = load_it_targets(IT_POLITICS_PATH)
        cpi_route_it = os.path.join(DB_BASE_PATH, "IMF/IMF_CPI_Global_iData.xlsx").replace("\\", "/")
        df_it_dev = load_it_deviation(cpi_route_it, IT_POLITICS_PATH, iso_dicts["ISO3"])

        src_cpi_it = get_file(cpi_route_it)
        _skip_it = _get_skiprows(src_cpi_it, "YoY")
        df_cpi_it = pd.read_excel(src_cpi_it, sheet_name="YoY", index_col=0, skiprows=_skip_it)
        df_cpi_it.index = pd.to_datetime(df_cpi_it.index)
        df_cpi_it = df_cpi_it.sort_index()
        df_cpi_it.columns = [str(c).strip() for c in df_cpi_it.columns]
        df_cpi_it.rename(columns=iso_dicts["ISO3"], inplace=True)
    except Exception as e:
        st.error(f"Error loading IT data: {e}")
        st.stop()

    tab_bar_dev, tab_band = st.tabs(["📊 Deviation Bar", "📈 vs Target Band"])

    with tab_bar_dev:
        rows_dev = []
        for country in df_it_dev.columns:
            series = df_it_dev[country].dropna()
            if series.empty:
                continue
            iso3 = next((k for k, v in iso_dicts["ISO3"].items() if v == country), None)
            if iso3 is None or iso3 not in df_it_targets.index:
                continue
            target = df_it_targets.loc[iso3]
            last_dev = series.iloc[-1]
            last_date = series.index[-1]
            cpi_series = df_cpi_it[country].dropna() if country in df_cpi_it.columns else pd.Series(dtype=float)
            cpi_val = cpi_series.iloc[-1] if not cpi_series.empty else None
            if cpi_val is not None and pd.notna(target["Techo"]) and cpi_val > target["Techo"]:
                status = "Above"
            elif cpi_val is not None and pd.notna(target["Piso"]) and cpi_val < target["Piso"]:
                status = "Below"
            else:
                status = "Within"
            rows_dev.append({
                "Country": country, "ISO3": iso3,
                "CPI YoY": cpi_val, "Centro": target["Centro"],
                "Piso": target["Piso"], "Techo": target["Techo"],
                "Tipo": target["Tipo"], "Deviation": last_dev,
                "Date": last_date.strftime("%b %Y"), "Status": status,
            })

        if not rows_dev:
            st.warning("No IT deviation data available.")
        else:
            df_bar_it = pd.DataFrame(rows_dev).sort_values("Deviation", ascending=True)
            colors_it = ["#ED483F" if s == "Above" else ("#3245B9" if s == "Below" else "#6BBC88")
                         for s in df_bar_it["Status"]]
            fig_dev = go.Figure(go.Bar(
                x=df_bar_it["Deviation"],
                y=df_bar_it["Country"],
                orientation="h",
                marker_color=colors_it,
                customdata=df_bar_it[["CPI YoY", "Centro", "Piso", "Techo", "Date", "Tipo"]].values,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Deviation: %{x:.1f} pp<br>"
                    "CPI YoY: %{customdata[0]:.1f}%<br>"
                    "Target: %{customdata[2]:.1f}%–%{customdata[3]:.1f}% (center %{customdata[1]:.1f}%)<br>"
                    "Type: %{customdata[5]}<br>"
                    "Date: %{customdata[4]}"
                    "<extra></extra>"
                )
            ))
            fig_dev.add_vline(x=0, line=dict(color="white", width=1.5, dash="dash"))
            fig_dev.update_layout(
                xaxis_title="Deviation from IT Center (pp)",
                yaxis_title="",
                height=max(400, len(df_bar_it) * 28),
            )
            fig_dev.update_xaxes(gridcolor="rgba(255,255,255,0.1)")
            st.plotly_chart(fig_dev, use_container_width=True)
            st.caption("🔴 Above ceiling · 🔵 Below floor · 🟢 Within band")

    with tab_band:
        it_countries_list = sorted(df_it_dev.columns.tolist(), key=str.casefold)
        it_sc_key = "it_band_countries"
        if it_sc_key in st.session_state:
            st.session_state[it_sc_key] = [c for c in st.session_state[it_sc_key] if c in it_countries_list]
        sel_it = st.multiselect("Select countries:", options=it_countries_list, key=it_sc_key)

        if not sel_it:
            st.warning("👈 Select at least one country.")
        else:
            df_cpi_sel = df_cpi_it[[c for c in sel_it if c in df_cpi_it.columns]].dropna(how="all")
            if df_cpi_sel.empty:
                st.warning("No CPI data available for selected countries.")
            else:
                min_d = df_cpi_sel.index.min().to_pydatetime()
                max_d = df_cpi_sel.index.max().to_pydatetime()
                default_start = max(min_d, (pd.Timestamp(max_d) - pd.DateOffset(years=5)).to_pydatetime())
                dates_it = st.slider("📅 Time filter:", min_value=min_d, max_value=max_d,
                                     value=(default_start, max_d), format="YYYY-MM", key="it_slider")
                fig_band = go.Figure()
                for i, country in enumerate(sel_it):
                    iso3 = next((k for k, v in iso_dicts["ISO3"].items() if v == country), None)
                    if iso3 is None or iso3 not in df_it_targets.index:
                        continue
                    target = df_it_targets.loc[iso3]
                    color = TENAC_COLORS[i % len(TENAC_COLORS)]
                    if country not in df_cpi_it.columns:
                        continue
                    s_cpi = df_cpi_it[country].dropna()
                    s_cpi = s_cpi.loc[dates_it[0]:dates_it[1]]
                    if s_cpi.empty:
                        continue
                    if pd.notna(target["Piso"]) and pd.notna(target["Techo"]):
                        fig_band.add_trace(go.Scatter(
                            x=s_cpi.index.tolist() + s_cpi.index.tolist()[::-1],
                            y=[target["Techo"]] * len(s_cpi) + [target["Piso"]] * len(s_cpi),
                            fill="toself",
                            fillcolor=_hex_to_rgba(color, 0.15),
                            line=dict(color="rgba(0,0,0,0)"),
                            showlegend=False, hoverinfo="skip",
                        ))
                    if pd.notna(target["Centro"]):
                        fig_band.add_trace(go.Scatter(
                            x=s_cpi.index, y=[target["Centro"]] * len(s_cpi),
                            mode="lines", line=dict(color=color, width=1, dash="dot"),
                            showlegend=False, hoverinfo="skip",
                        ))
                    fig_band.add_trace(go.Scatter(
                        x=s_cpi.index, y=s_cpi.values,
                        mode="lines", name=country,
                        line=dict(color=color, width=2),
                        hovertemplate=f"{country} CPI YoY: %{{y:.1f}}%<extra></extra>",
                    ))
                fig_band.update_layout(
                    xaxis_title="", yaxis_title="CPI YoY (%)",
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                fig_band.update_yaxes(gridcolor="rgba(255,255,255,0.1)", rangemode="tozero")
                st.plotly_chart(fig_band, use_container_width=True)
                st.caption("Solid line = CPI YoY · Dotted line = IT center · Shaded area = target band")

    st.stop()

# ── VARIABLE VIEW ─────────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Data Controls")

selected_category = st.sidebar.selectbox("1️⃣ Select Category:", list(CATEGORY_GROUPS.keys()))
selected_db = st.sidebar.selectbox("2️⃣ Select Database:", CATEGORY_GROUPS[selected_category])
db_config   = DATABASES[selected_db]
file_route  = os.path.join(DB_BASE_PATH, db_config["file"]).replace("\\", "/")
iso_format  = db_config["iso_format"]
loader      = db_config.get("loader", "default")
friendly_metric = st.sidebar.selectbox("3️⃣ Select Metric:", list(db_config["metrics"].keys()))
m_cfg = db_config["metrics"][friendly_metric]
metric_loader = m_cfg.get("loader", loader)

# --- Dispatch to the right loader ---
try:
    if loader == "bbg_fx":
        df = transform_bbg_fx(load_bbg_indicator_raw(file_route, "FX"), iso_dicts[iso_format], m_cfg["calc"])
    elif loader == "bbg_lc10y":
        df = load_bbg_indicator_raw(file_route, "LC10y").rename(columns=iso_dicts[iso_format])
    elif loader == "bbg_ndf":
        df_ndf = load_bbg_indicator_raw(file_route, "NDF")
        df_fx  = load_bbg_indicator_raw(file_route, "FX")
        common = [c for c in df_ndf.columns if c in df_fx.columns]
        df_fx_aligned = df_fx[common].reindex(df_ndf.index, method='ffill')
        df = ((df_ndf[common] / df_fx_aligned) - 1) * 100
        df = df.rename(columns=iso_dicts[iso_format])
    elif loader == "em_spreads":
        df = load_em_spreads(file_route, iso_dicts[iso_format])
    elif metric_loader == "it_deviation":
        df = load_it_deviation(file_route, IT_POLITICS_PATH, iso_dicts["ISO3"])
    elif metric_loader == "it_deviation_3m3m":
        df = load_it_deviation(file_route, IT_POLITICS_PATH, iso_dicts["ISO3"], cpi_sheet="3m3m")
    elif m_cfg["calc"] == "real_mpr":
        cpi_route = os.path.join(DB_BASE_PATH, "IMF/IMF_CPI_Global_iData.xlsx").replace("\\", "/")
        df = load_real_mpr(file_route, cpi_route, iso_dicts["ISO2"], iso_dicts["ISO3"])
    elif m_cfg["calc"] == "real_mpr_3m3m":
        cpi_route = os.path.join(DB_BASE_PATH, "IMF/IMF_CPI_Global_iData.xlsx").replace("\\", "/")
        df = load_real_mpr(file_route, cpi_route, iso_dicts["ISO2"], iso_dicts["ISO3"], cpi_sheet="3m3m")
    else:
        df = load_and_transform_data(
            file_route, m_cfg["sheet"], iso_dicts[iso_format],
            iso_format, m_cfg.get("calc"), MACRO_MONITOR_PATH,
            m_cfg.get("drop_projections", False)
        )
except Exception as e:
    st.error(f"❌ Could not load data for {selected_db}. Is the file in Dropbox?")
    st.stop()

st.markdown(f"### {selected_db} ➔ {friendly_metric}")
st.caption(f"Source: {db_config.get('source', '')}")

valid_names = set(iso_dicts[iso_format].values())
available_countries = sorted(
    [str(c) for c in df.columns if str(c) in valid_names],
    key=str.casefold
)

sc_key = f"ms_{selected_db}"
if sc_key in st.session_state:
    st.session_state[sc_key] = [c for c in st.session_state[sc_key] if c in available_countries]

st.sidebar.markdown("**⚡ Quick select group:**")
_avail_cats = [k for k in GROUP_CATEGORIES if GROUP_CATEGORIES[k]]
_grp_type = st.sidebar.radio("", _avail_cats, horizontal=True,
                              label_visibility="collapsed", key=f"grp_type_{selected_db}")
_grp_opts = ["—"] + [g for g in GROUP_CATEGORIES[_grp_type] if g in COUNTRY_GROUPS]
selected_group = st.sidebar.selectbox("", _grp_opts, label_visibility="collapsed", key=f"grp_{selected_db}")
col_add, col_clear = st.sidebar.columns(2)
if col_add.button("➕ Add", key=f"add_{selected_db}"):
    if selected_group != "—":
        names_to_add = _resolve_group(selected_group, iso_dicts["ISO3"], available_countries)
        current = list(st.session_state.get(sc_key, []))
        st.session_state[sc_key] = sorted(
            set(current) | set(names_to_add),
            key=str.casefold
        )
if col_clear.button("🗑️ Clear", key=f"clear_{selected_db}"):
    st.session_state[sc_key] = []

st.sidebar.markdown("**🎯 Filter by latest value:**")
col_dir, col_val = st.sidebar.columns([1, 1])
thr_dir = col_dir.selectbox("", ["above", "below"], key=f"tdir_{selected_db}", label_visibility="collapsed")
thr_val = col_val.number_input("", value=0.0, step=0.1, key=f"tval_{selected_db}", label_visibility="collapsed")
if st.sidebar.button("Apply threshold", key=f"tapply_{selected_db}"):
    last_vals = {c: col.dropna().iloc[-1] for c, col in df[available_countries].items() if not col.dropna().empty}
    if thr_dir == "above":
        matching = [c for c in available_countries if last_vals.get(c) is not None and last_vals[c] > thr_val]
    else:
        matching = [c for c in available_countries if last_vals.get(c) is not None and last_vals[c] < thr_val]
    current = list(st.session_state.get(sc_key, []))
    st.session_state[sc_key] = sorted(set(current) | set(matching), key=str.casefold)

selected_countries = st.sidebar.multiselect("4️⃣ Select countries:", options=available_countries, key=sc_key)

df_filtered = pd.DataFrame()
if selected_countries:
    df_plot = df[selected_countries].dropna(how='all')
    if not df_plot.empty:
        min_d = df_plot.index.min().to_pydatetime()
        max_d = df_plot.index.max().to_pydatetime()
        default_start = max(min_d, (pd.Timestamp(max_d) - pd.DateOffset(years=5)).to_pydatetime())
        dates = st.slider("📅 Time filter:", min_value=min_d, max_value=max_d, value=(default_start, max_d), format="YYYY-MM", key=f"slider_{selected_db}_{friendly_metric}")
        df_filtered = df_plot.loc[dates[0]:dates[1]]

val_fmt = m_cfg.get("fmt", ".2f")
tab_chart, tab_bar, tab_change, tab_table = st.tabs(["📈 Chart", "📊 Bar Chart", "📉 Change", "🧮 Data Table"])

with tab_chart:
    if not selected_countries:
        st.warning("👈 Please select at least one country.")
    elif df_filtered.empty:
        st.warning("No data for the selected range.")
    else:
        fig = px.line(df_filtered, x=df_filtered.index, y=df_filtered.columns,
                      color_discrete_sequence=TENAC_COLORS)
        fig.update_traces(hovertemplate=f"%{{fullData.name}}<br>%{{x}}: %{{y:{val_fmt}}}<extra></extra>")
        fig.update_layout(
            xaxis_title="", yaxis_title="",
            legend_title="Country",
            hovermode="closest",
            shapes=[dict(
                type='line', yref='y', y0=0, y1=0,
                xref='paper', x0=0, x1=1,
                line=dict(color="white", width=3, dash="dash")
            )]
        )
        fig.update_yaxes(gridcolor='rgba(255, 255, 255, 0.1)')
        st.plotly_chart(fig, use_container_width=True)

with tab_bar:
    if not selected_countries:
        st.warning("👈 Please select at least one country.")
    elif df_filtered.empty:
        st.warning("No data for the selected range.")
    else:
        last_values = df_filtered.apply(lambda col: col.dropna().iloc[-1] if not col.dropna().empty else None)
        last_values = last_values.dropna().sort_values(ascending=False)
        last_date = df_filtered.apply(lambda col: col.dropna().index[-1] if not col.dropna().empty else None)
        hover = [f"{last_date[c].strftime('%Y-%m')}" for c in last_values.index]

        _hl_key = f"hl_bar_{selected_db}_{friendly_metric}"
        _ls_key = f"ls_bar_{selected_db}_{friendly_metric}"
        if _hl_key not in st.session_state:
            st.session_state[_hl_key] = set()
        if _ls_key not in st.session_state:
            st.session_state[_ls_key] = frozenset()

        _col_lbl, _col_clr = st.columns([3, 1])
        _show_labels = _col_lbl.checkbox("Show value labels", value=False,
                                         key=f"lbl_bar_{selected_db}_{friendly_metric}")
        if _col_clr.button("🗑️ Clear marks", key=f"clr_bar_{selected_db}_{friendly_metric}"):
            st.session_state[_hl_key] = set()
            st.session_state[_ls_key] = None

        _bar_colors = ["#F5A623" if c in st.session_state[_hl_key] else "#6BBC88"
                       for c in last_values.index]
        _text_vals = [f"{v:{val_fmt}}" for v in last_values.values] if _show_labels else None

        fig_bar = go.Figure(go.Bar(
            x=list(last_values.index),
            y=list(last_values.values),
            marker_color=_bar_colors,
            customdata=[[h] for h in hover],
            text=_text_vals,
            textposition="outside" if _show_labels else None,
            textfont=dict(size=13),
        ))
        fig_bar.update_traces(hovertemplate=f"%{{x}}<br>%{{y:{val_fmt}}}<br>%{{customdata[0]}}<extra></extra>")
        fig_bar.update_layout(xaxis_title="", yaxis_title="")
        fig_bar.update_yaxes(gridcolor='rgba(255, 255, 255, 0.1)')
        _ev_bar = st.plotly_chart(fig_bar, use_container_width=True, on_select="rerun",
                                  key=f"bc_{selected_db}_{friendly_metric}")

        try:
            _pts = _ev_bar.selection.points or []
        except (AttributeError, TypeError):
            _pts = []
        _cur_sel = frozenset(p.get("x") for p in _pts if p.get("x"))
        _last_sel = st.session_state[_ls_key]
        if _last_sel is None:
            st.session_state[_ls_key] = _cur_sel
        elif _cur_sel != _last_sel:
            for _c in (_cur_sel - _last_sel):
                if _c in st.session_state[_hl_key]:
                    st.session_state[_hl_key].discard(_c)
                else:
                    st.session_state[_hl_key].add(_c)
            st.session_state[_ls_key] = _cur_sel
            st.rerun()

with tab_change:
    if not selected_countries:
        st.warning("👈 Please select at least one country.")
    else:
        df_all = df[selected_countries].dropna(how="all")
        if df_all.empty:
            st.warning("No data available.")
        else:
            min_d = df_all.index.min().date()
            max_d = df_all.index.max().date()
            default_base = df_all.index.max().replace(month=1, day=1).date()
            base_date = st.date_input(
                "Base date:",
                value=default_base,
                min_value=min_d,
                max_value=max_d,
                key=f"chdate_{selected_db}_{friendly_metric}"
            )
            base_ts      = pd.Timestamp(base_date)
            change_type  = m_cfg.get("change", "abs")

            changes = {}
            for country in selected_countries:
                col  = df_all[country].dropna()
                if col.empty:
                    continue
                past = col[col.index <= base_ts]
                if past.empty:
                    continue
                base_val    = past.iloc[-1]
                current_val = col.iloc[-1]
                if change_type == "rel":
                    changes[country] = (current_val / base_val - 1) * 100 if base_val != 0 else None
                else:
                    changes[country] = current_val - base_val

            valid = {k: v for k, v in changes.items() if v is not None}
            if not valid:
                st.warning("No data available for the selected base date.")
            else:
                s      = pd.Series(valid).sort_values(ascending=False)
                colors = ["#6BBC88" if v >= 0 else "#ED483F" for v in s.values]
                y_label = "% change" if change_type == "rel" else friendly_metric

                _hl_ch_key = f"hl_ch_{selected_db}_{friendly_metric}"
                _ls_ch_key = f"ls_ch_{selected_db}_{friendly_metric}"
                if _hl_ch_key not in st.session_state:
                    st.session_state[_hl_ch_key] = set()
                if _ls_ch_key not in st.session_state:
                    st.session_state[_ls_ch_key] = frozenset()

                _col_lbl_ch, _col_clr_ch = st.columns([3, 1])
                _show_labels_ch = _col_lbl_ch.checkbox(
                    "Show value labels", value=False,
                    key=f"lbl_ch_{selected_db}_{friendly_metric}"
                )
                if _col_clr_ch.button("🗑️ Clear marks", key=f"clr_ch_{selected_db}_{friendly_metric}"):
                    st.session_state[_hl_ch_key] = set()
                    st.session_state[_ls_ch_key] = None

                _final_colors_ch = [
                    "#F5A623" if c in st.session_state[_hl_ch_key] else col
                    for c, col in zip(s.index, colors)
                ]
                _text_ch = [f"{v:{val_fmt}}" for v in s.values] if _show_labels_ch else None

                fig_ch = go.Figure(go.Bar(
                    x=list(s.index),
                    y=list(s.values),
                    marker_color=_final_colors_ch,
                    text=_text_ch,
                    textposition="outside" if _show_labels_ch else None,
                    textfont=dict(size=13),
                ))
                fig_ch.update_traces(hovertemplate=f"%{{x}}<br>%{{y:{val_fmt}}}<extra></extra>")
                fig_ch.update_layout(xaxis_title="", yaxis_title=y_label)
                fig_ch.update_yaxes(gridcolor="rgba(255,255,255,0.1)")
                fig_ch.add_hline(y=0, line=dict(color="white", width=1.5, dash="dash"))
                _ev_ch = st.plotly_chart(fig_ch, use_container_width=True, on_select="rerun",
                                         key=f"cc_{selected_db}_{friendly_metric}")
                st.caption(f"Change from {base_date.strftime('%d %b %Y')} to latest available value per country")

                try:
                    _pts_ch = _ev_ch.selection.points or []
                except (AttributeError, TypeError):
                    _pts_ch = []
                _cur_sel_ch = frozenset(p.get("x") for p in _pts_ch if p.get("x"))
                _last_sel_ch = st.session_state[_ls_ch_key]
                if _last_sel_ch is None:
                    st.session_state[_ls_ch_key] = _cur_sel_ch
                elif _cur_sel_ch != _last_sel_ch:
                    for _c in (_cur_sel_ch - _last_sel_ch):
                        if _c in st.session_state[_hl_ch_key]:
                            st.session_state[_hl_ch_key].discard(_c)
                        else:
                            st.session_state[_hl_ch_key].add(_c)
                    st.session_state[_ls_ch_key] = _cur_sel_ch
                    st.rerun()

with tab_table:
    display_df = df_filtered if not df_filtered.empty else (df[selected_countries] if selected_countries else df)
    st.dataframe(display_df, use_container_width=True)

st.divider()
if len(selected_countries) == 2 and not df_filtered.empty:
    country_a, country_b = selected_countries[0], selected_countries[1]
    spread = df_filtered[country_a] - df_filtered[country_b]
    spread.name = f"{country_a} − {country_b}"
    st.markdown(f"#### Spread: {country_a} − {country_b}")
    fig_spread = px.line(spread, x=spread.index, y=spread.name,
                         color_discrete_sequence=TENAC_COLORS)
    fig_spread.update_layout(
        xaxis_title="", yaxis_title="",
        showlegend=False,
        hovermode="x unified",
        shapes=[dict(
            type='line', yref='y', y0=0, y1=0,
            xref='paper', x0=0, x1=1,
            line=dict(color="white", width=3, dash="dash")
        )]
    )
    fig_spread.update_yaxes(gridcolor='rgba(255, 255, 255, 0.1)')
    st.plotly_chart(fig_spread, use_container_width=True)
elif len(selected_countries) != 2 and selected_countries:

    st.caption("📌 Select exactly 2 countries to see the spread.")

