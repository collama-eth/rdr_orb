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
        fname = f"{instrument}_09_30_09_30_10_25_data.csv"
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
instrument_options = ["ES", "NQ", "YM", "RTY"]
range_time_options = ["5m", "15m"]
selected_instrument = st.sidebar.selectbox("Instrument", instrument_options)
selected_range_time = st.sidebar.selectbox("Range Time Frame", range_time_options)

#########################################
### Data Loading and Processing
#########################################
df = load_data_for_instrument(selected_instrument, selected_range_time)

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

#########################################
### Resets
######################################### 
default_filters = {
    "selected_day":                       "All",
    "date_range":                 (min_date, max_date),
    "orb_conf_direction_filter":    "All",
    "orb_conf_time_filter" :        "All",
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

row1_cols = st.columns([1, 1, 1])

with row1_cols[0]:
    orb_conf_direction = st.selectbox(
        "ORB Confirmation Direction",
        options=["All"] + ["Long", "Short"],
        key="orb_conf_direction_filter"
    )
with row1_cols[1]:
    orb_conf_time = st.selectbox(
        "ORB Confirmation Time",
        options=["All"] + sorted(df["orb_conf_time"].dropna().unique()),
        key="orb_conf_time_filter"
    )

with row1_cols[2]:
    orb_range_direction = st.selectbox(
        "ORB Range Direction",
        options=["All"] + ["Long", "Short"],
        key="orb_range_direction_filter"
    )

#########################################
### Filter Mapping
#########################################   

# map each filter to its column
inclusion_map = {
    "orb_conf_direction":       "orb_conf_direction_filter",
    "orb_conf_time":            "orb_conf_time_filter",
    "orb_range_direction" :     "orb_range_direction_filter"

}

# Apply filters
df_filtered = df.copy()

sel_day = st.session_state["selected_day"]
if sel_day != "All":
    df_filtered = df_filtered[df_filtered["day_of_week"]  == sel_day]

# — Date range —
start_date, end_date = st.session_state["date_range"]
df_filtered = df_filtered[
    (df_filtered["date"] >= pd.to_datetime(start_date)) &
    (df_filtered["date"] <= pd.to_datetime(end_date))
]

for col, state_key in inclusion_map.items():
    sel = st.session_state[state_key]
    if isinstance(sel, list):
        if sel:  # non-empty list means “only these”
            df_filtered = df_filtered[df_filtered[col].isin(sel)]
    else:
        if sel != "All":
            df_filtered = df_filtered[df_filtered[col] == sel]

###########################################################
### True Rates, Box Color, and Conf. Direction Graphs
###########################################################
# Box Color and Confirmation Direction
true_rate_cols   = ["orb_true"]
true_rate_titles = ["ORB True Rate"]

box_color_cols   = ["box_color"]
box_color_titles = ["RDR Box Color"]

conf_direction_cols   = ["range_conf_direction"]
conf_direction_titles = ["RDR Confirmation Direction"]

plot_df = df_filtered.copy()

for col in true_rate_cols:
    plot_df[col] = plot_df[col].map({True: "True", False: "False"})

# color maps
box_color_map = {
    "Green":   "#2ecc71",
    "Red":     "#e74c3c",
    "Neutral": "#5d6d7e",
}
dir_color_map = {
    "Long":  "#2ecc71", 
    "Short": "#e74c3c",
    "None":  "#5d6d7e",
}

true_color_map = {
    "True":  "#2ecc71",
    "False": "#e74c3c",
}

# replace null/NaN with the string "None" for just those three cols
for col in conf_direction_cols:
    plot_df[col] = plot_df[col].fillna("None")
    
all_cols = st.columns(len(box_color_cols) + len(conf_direction_cols) + len(true_rate_cols))

# true rate donuts
for i, col in enumerate(true_rate_cols):
    fig = px.pie(
        plot_df,
        names=col,
        color=col,                        # tell px to color by that column
        color_discrete_map=true_color_map, # map labels → colors
        title=true_rate_titles[i],
        hole=0.5,
    )
    fig.update_traces(textinfo="percent+label", textposition="inside", showlegend=False)
    fig.update_layout(height=250,
                      width=250,
                      margin=dict(l=10, r=10, t=30, b=10))
    all_cols[i].plotly_chart(fig, use_container_width=True)

# box-color donuts
offset = len(true_rate_cols)
for i, col in enumerate(box_color_cols):
    fig = px.pie(
        plot_df,
        names=col,
        color=col,                        # tell px to color by that column
        color_discrete_map=box_color_map, # map labels → colors
        title=box_color_titles[i],
        hole=0.5,
    )
    fig.update_traces(textinfo="percent+label", textposition="inside", showlegend=False)
    fig.update_layout(height=250,
                      width=250,
                      margin=dict(l=10, r=10, t=30, b=10))
    all_cols[offset + i].plotly_chart(fig, use_container_width=True)

offset2 = len(box_color_cols) + len(true_rate_cols)
for j, col in enumerate(conf_direction_cols):
    fig = px.pie(
        plot_df,
        names=col,
        color=col,
        color_discrete_map=dir_color_map,
        title=conf_direction_titles[j],
        hole=0.5,
    )
    fig.update_traces(textinfo="percent+label", textposition="inside", showlegend=False)
    fig.update_layout(height=250,
                      width=250,
                      margin=dict(l=10, r=10, t=30, b=10))
    all_cols[offset2 + j].plotly_chart(fig, use_container_width=True)

#########################################################
### Box High/Low Time
#########################################################
time_cols = [
    "range_high_time",
    "range_low_time",
    "orb_open_touch_time",
]
time_col_layout = st.columns(len(time_cols))

# Generate time order from all relevant columns (not just one)
all_times = pd.concat([df_filtered[col] for col in time_cols]).dropna().unique()
order = sorted(all_times)
order = [t.strftime("%H:%M") if hasattr(t, "strftime") else str(t) for t in order]
order.append("Untouched")  # For missing values we fill with "Untouched"


for col_container, col_name in zip(time_col_layout, time_cols):
    series = df_filtered[col_name].fillna("Untouched")

    # Convert times to string format for easier plotting (e.g. "10:30")
    series = series.apply(lambda t: t.strftime("%H:%M") if hasattr(t, "strftime") else str(t))

    counts = (
        series
        .value_counts(normalize=True)
        .reindex(order, fill_value=0)
    )

    perc = counts * 100

    fig = px.bar(
        x=perc.index,
        y=perc.values,
        text=[f"{v:.1f}%" for v in perc.values],
        title=col_name.replace("_", " ").title(),
        labels={"x": "", "y": ""},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis_tickangle=90,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(showticklabels=False),
    )

    col_container.plotly_chart(fig, use_container_width=True)
