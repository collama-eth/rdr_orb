import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, time
import plotly.express as px

st.set_page_config(layout='wide')

#########################################
### Functions
#########################################
@st.cache_data
def load_data_for_instrument(instrument: str, period: str = "5m") -> pd.DataFrame:
    """
    Load the 1-minute quartal file for a single instrument.
    period must be "5m" or "15m".
    """ 
    base = "https://raw.githubusercontent.com/TuckerArrants/rdr_orb/main"
    if period == "5m":
        fname = f"{instrument}_9_30_9_35_10_30_data.csv"
    else:
        raise ValueError("period must be '5m' or '15m'")
    url = f"{base}/{fname}"
    try:
        return pd.read_csv(url)
    except Exception:
        # fallback to empty DF if file not found or network hiccup
        return pd.DataFrame() 

# ✅ Store username-password pairs
USER_CREDENTIALS = {
    "badboyz": "bangbang",
    "dreamteam" : "strike",
}

#########################################
### Log In
#########################################
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None

if not st.session_state["authenticated"]:
    st.title("Login to Database")

    # Username and password fields
    username = st.text_input("Username:")
    password = st.text_input("Password:", type="password")

    # Submit button
    if st.button("Login"):
        if username in USER_CREDENTIALS and password == USER_CREDENTIALS[username]:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username  # Store the username
            # ← Clear *all* @st.cache_data caches here:
            st.cache_data.clear()

            st.success(f"Welcome, {username}! Loading fresh data…")
            st.rerun()
        else:
            st.error("Incorrect username or password. Please try again.")

    # Stop execution if user is not authenticated
    st.stop()

# ✅ If authenticated, show the full app
st.title("Opening Range Breakouts")

# ↓ in your sidebar:
instrument_options = ["ES", "NQ", "YM", "RTY", "CL", "GC"]
selected_instrument = st.sidebar.selectbox("Instrument", instrument_options)

#########################################
### Data Loading and Processing
#########################################
df = load_data_for_instrument(selected_instrument)

df['date'] = pd.to_datetime(df['date']).dt.date

# 1) Make sure 'date' is a datetime column
if "date" in df.columns:
    df["date"] = pd.to_datetime(df["date"])
else:
    st.sidebar.warning("No 'date' column found in your data!")

#########################################
### Sidebar
#########################################
day_options = ['All'] + ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
selected_day = st.sidebar.selectbox("Day of Week", day_options, key="selected_day")

min_date = df["date"].min().date()
max_date = df["date"].max().date()
start_date, end_date = st.sidebar.date_input(
    "Select date range:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
    key="date_range"
)

st.sidebar.markdown("### Daily Open Position") 

#########################################
### Resets
#########################################
default_filters = {
    "selected_day":                       "All",
    "date_range":                 (min_date, max_date),
}

  # 2) Reset button with callback
def reset_all_filters():
    for key, default in default_filters.items():
        # only touch keys that actually exist
        if key in st.session_state:
            st.session_state[key] = default

st.sidebar.button("Reset all filters", on_click=reset_all_filters)

if isinstance(start_date, tuple):
    # sometimes date_input returns a single date if you pass a single default
    start_date, end_date = start_date

st.markdown("### Dropdown Filters")
with st.expander("Range Filters", expanded=False):
    row1_cols = st.columns([1, 1,])

    with row1_cols[0]:
        orb_conf_direction = st.selectbox(
            "ORB Confirmation Direction",
            options=["All"] + ["Long", "Short"],
            key="orb_conf_direction"
        )
    with row1_cols[1]:
        orb_conf_time = st.selectbox(
            "ORB Confirmation Time",
            options=["All"] + sorted(df["orb_conf_time"].dropna().unique()),
            key="orb_conf_direction"
        )
