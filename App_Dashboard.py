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

# 3. MASTER DICTIONARY
DATABASES = {
    "Inflation (CPI)": {
        "file": "IMF/IMF_CPI_Global_iData.xlsx",
        "iso_format": "ISO3",
        "source": "IMF",
        "metrics": {
            "YoY":      {"sheet": "YoY",  "calc": None, "fmt": ".1f"},
            "MoM sa":   {"sheet": "MoM",  "calc": None, "fmt": ".1f"},
            "3m3m saar":{"sheet": "3m3m", "calc": None, "fmt": ".1f"}
        }
    },
    "Gross Domestic Product (GDP)": {
        "file": "IMF/IMF_GDP_Global_iData.xlsx",
        "iso_format": "ISO3",
        "source": "IMF",
        "metrics": {
            "GDP YoY (Year-over-Year)":    {"sheet": "GDP_NSA", "calc": "yoy_quarterly", "fmt": ".1f"},
            "GDP QoQ saar (Annualized)":   {"sheet": "GDP_SA",  "calc": "qoq_saar",      "fmt": ".1f"}
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
            "Policy Rate (%)": {"sheet": "Sheet1", "calc": None,       "fmt": ".2f"},
            "Real MPR (%)":    {"sheet": "Sheet1", "calc": "real_mpr", "fmt": ".2f"}
        }
    },
    "Real Effective Exchange Rate": {
        "file": "BIS/BIS_REER_Broad.xlsx",
        "iso_format": "ISO2",
        "source": "BIS",
        "metrics": {
            "REER Broad (10Y avg = 100)": {"sheet": 0, "calc": "reer_10y_avg", "fmt": ".1f", "change": "rel"},
            "REER Var YoY (%)":           {"sheet": 0, "calc": "yoy_monthly",  "fmt": ".1f"}
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
    }
}

# 4. Category grouping for the sidebar
CATEGORY_GROUPS = {
    "Macro":             ["Inflation (CPI)", "Gross Domestic Product (GDP)"],
    "Fiscal":            ["Fiscal Monitor (FM)"],
    "External Sector":   ["Balance of Payments (BOP)", "International Reserves", "Energy Net Exports", "Commodity Terms of Trade"],
    "Monetary Policy":   ["Monetary Policy Rate"],
    "Exchange Rates":    ["Real Effective Exchange Rate", "FX"],
    "Financial Markets": ["NDF Implied Depreciation (12M)", "Local Currency 10Y Yield", "EM Spreads (10Y)"],
}

# Tenac brand color sequence
TENAC_COLORS = ["#6BBC88", "#3245B9", "#ED483F", "#4EA72E", "#A02B93", "#0E2841", "#467886", "#96607D", "#E8E8E8", "#414042"]

COUNTRY_VIEW_METRICS = [
    ("Macro",    "GDP Growth YoY (%)",          "Gross Domestic Product (GDP)",   "GDP YoY (Year-over-Year)",                      ".1f"),
    ("Macro",    "Inflation YoY (%)",            "Inflation (CPI)",                "YoY",                                           ".1f"),
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
    df = pd.read_excel(get_file(route), sheet_name=sheet, index_col=0)
    
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
def load_real_mpr(mpr_route, cpi_route, iso2_mapping, iso3_mapping):
    df_mpr = pd.read_excel(get_file(mpr_route), sheet_name="Sheet1", index_col=0)
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

    df_cpi = pd.read_excel(get_file(cpi_route), sheet_name="YoY", index_col=0)
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

def load_df_for_metric(db_key, metric_key):
    db_cfg     = DATABASES[db_key]
    file_route = os.path.join(DB_BASE_PATH, db_cfg["file"]).replace("\\", "/")
    iso_format = db_cfg["iso_format"]
    loader     = db_cfg.get("loader", "default")
    m_cfg      = db_cfg["metrics"][metric_key]
    
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
        if m_cfg["calc"] == "real_mpr":
            cpi_route = os.path.join(DB_BASE_PATH, "IMF/IMF_CPI_Global_iData.xlsx").replace("\\", "/")
            return load_real_mpr(file_route, cpi_route, iso_dicts["ISO2"], iso_dicts["ISO3"])
        return load_and_transform_data(
            file_route, m_cfg["sheet"], iso_dicts[iso_format],
            iso_format, m_cfg.get("calc"), MACRO_MONITOR_PATH,
            m_cfg.get("drop_projections", False)
        )
    except Exception as e:
        return pd.DataFrame()


# 5. MAIN APP LOGIC
iso_dicts = load_iso_mapping(ISO_PATH)

try:
    if USE_DROPBOX_API:
        st.sidebar.image(get_file(LOGO_PATH), use_container_width=True)
    elif os.path.exists(LOGO_PATH):
        st.sidebar.image(LOGO_PATH, use_container_width=True)
except Exception:
    pass

st.sidebar.divider()
view_mode = st.sidebar.radio("", ["📊 Variable View", "🌍 Country View", "🔀 Cross Variable"],
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
    db_list = list(DATABASES.keys())

    st.sidebar.header("⚙️ Variables")
    st.sidebar.markdown("**Variable X (horizontal axis):**")
    xdb  = st.sidebar.selectbox("xdb",  db_list, label_visibility="collapsed", key="cvx_db")
    xmet = st.sidebar.selectbox("xmet", list(DATABASES[xdb]["metrics"].keys()), label_visibility="collapsed", key="cvx_met")
    st.sidebar.markdown("**Variable Y (vertical axis):**")
    ydb  = st.sidebar.selectbox("ydb",  db_list, label_visibility="collapsed", key="cvy_db", index=min(1, len(db_list)-1))
    ymet = st.sidebar.selectbox("ymet", list(DATABASES[ydb]["metrics"].keys()), label_visibility="collapsed", key="cvy_met")

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

    cv_group = st.sidebar.selectbox("", ["—"] + list(COUNTRY_GROUPS.keys()), label_visibility="collapsed", key="cv_grp")
    col_add, col_clear = st.sidebar.columns(2)
    if col_add.button("➕ Add", key="cv_add"):
        if cv_group != "—":
            names_to_add = common_countries if cv_group == "All" else [
                iso_dicts["ISO3"].get(code) for code in COUNTRY_GROUPS.get(cv_group, [])
            ]
            names_to_add = [n for n in names_to_add if n and n in common_countries]
            st.session_state[cv_sc_key] = sorted(
                set(st.session_state.get(cv_sc_key, [])) | set(names_to_add), key=str.casefold
            )
    if col_clear.button("🗑️ Clear", key="cv_clear"):
        st.session_state[cv_sc_key] = []

    cv_countries = st.sidebar.multiselect("Select countries:", options=common_countries, key=cv_sc_key)

    x_label = f"{xdb} · {xmet}"
    y_label = f"{ydb} · {ymet}"
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
                        textfont=dict(size=9, color="white"),
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
    elif m_cfg["calc"] == "real_mpr":
        cpi_route = os.path.join(DB_BASE_PATH, "IMF/IMF_CPI_Global_iData.xlsx").replace("\\", "/")
        df = load_real_mpr(file_route, cpi_route, iso_dicts["ISO2"], iso_dicts["ISO3"])
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
selected_group = st.sidebar.selectbox("", ["—"] + list(COUNTRY_GROUPS.keys()), label_visibility="collapsed", key=f"grp_{selected_db}")
col_add, col_clear = st.sidebar.columns(2)
if col_add.button("➕ Add", key=f"add_{selected_db}"):
    if selected_group != "—":
        if selected_group == "All":
            names_to_add = available_countries
        else:
            group_names = [iso_dicts["ISO3"].get(code) for code in COUNTRY_GROUPS.get(selected_group, [])]
            names_to_add = [n for n in group_names if n and n in available_countries]
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
        fig_bar = px.bar(
            x=last_values.index, y=last_values.values,
            labels={"x": "", "y": friendly_metric},
            custom_data=[hover],
            color_discrete_sequence=["#6BBC88"]
        )
        fig_bar.update_traces(hovertemplate=f"%{{x}}<br>%{{y:{val_fmt}}}<br>%{{customdata[0]}}<extra></extra>")
        fig_bar.update_layout(xaxis_title="", yaxis_title="")
        fig_bar.update_yaxes(gridcolor='rgba(255, 255, 255, 0.1)')
        st.plotly_chart(fig_bar, use_container_width=True)

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

                fig_ch = px.bar(x=s.index, y=s.values, labels={"x": "", "y": y_label})
                fig_ch.update_traces(marker_color=colors)
                fig_ch.update_traces(hovertemplate=f"%{{x}}<br>%{{y:{val_fmt}}}<extra></extra>")
                fig_ch.update_layout(xaxis_title="", yaxis_title=y_label)
                fig_ch.update_yaxes(gridcolor="rgba(255,255,255,0.1)")
                fig_ch.add_hline(y=0, line=dict(color="white", width=1.5, dash="dash"))
                st.plotly_chart(fig_ch, use_container_width=True)
                st.caption(f"Change from {base_date.strftime('%d %b %Y')} to latest available value per country")

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
