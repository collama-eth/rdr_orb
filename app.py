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
def load_available_combinations():
    url = "https://raw.githubusercontent.com/TuckerArrants/rdr_orb/main/available_files.csv"
    return pd.read_csv(url)

@st.cache_data
def load_data_by_filename(filename):
    base = "https://raw.githubusercontent.com/TuckerArrants/rdr_orb/main"
    url = f"{base}/{filename}"
    try:
        return pd.read_csv(url)
    except Exception:
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

# ↓ in your sidebar:
instrument_options = ["ES", "NQ", "YM", "RTY", "CL", "GC"]
orb_end_time = ["09:30"]
range_end_time = ["10:25", "11:25", "12:25"]
bin_size_options = [0.5, 0.25, 0.1]

available = load_available_combinations()

# Select instrument
instrument_options = sorted(available['instrument'].unique())
selected_instrument = st.sidebar.selectbox("Instrument", instrument_options)

instrument_filtered = available[available['instrument'] == selected_instrument]

# Select ORB start time
valid_orb_start_times = sorted(instrument_filtered['orb_start_time'].unique())
selected_orb_start_time = st.sidebar.selectbox("ORB Start Time", valid_orb_start_times)

orb_start_filtered = instrument_filtered[
    instrument_filtered['orb_start_time'] == selected_orb_start_time
]

# Select ORB end time
valid_orb_end_times = sorted(orb_start_filtered['orb_end_time'].unique())
selected_orb_end_time = st.sidebar.selectbox("ORB End Time", valid_orb_end_times)

orb_end_filtered = orb_start_filtered[
    orb_start_filtered['orb_end_time'] == selected_orb_end_time
]

# Select Range end time
valid_range_end_times = sorted(orb_end_filtered['range_end_time'].unique())
selected_range_end_time = st.sidebar.selectbox("Range End Time", valid_range_end_times)

# Look up the filename from the filtered row
final_match = orb_end_filtered[
    orb_end_filtered['range_end_time'] == selected_range_end_time
]

if final_match.empty:
    st.error("No data available for the selected combination.")
    df = pd.DataFrame()
else:
    filename = final_match.iloc[0]['filename']
    df = load_data_by_filename(filename)
selected_bin_size = st.sidebar.selectbox("Graph Bucket Size", bin_size_options)

#########################################
### Data Loading and Processing
#########################################
df = load_data_for_instrument(selected_instrument, selected_orb_start_time, selected_orb_end_time, selected_range_end_time)

df['date'] = pd.to_datetime(df['date']).dt.date
df['day_of_week'] = pd.to_datetime(df['date']).dt.day_name()

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
    "orb_end_time_filter":          "09:30",
    "range_end_time_filter":          "10:25",
    "selected_bin_size" :           0.5,
    "orb_conf_direction_filter":    "All",
    "orb_conf_time_filter" :        "All",
    "orb_true_filter" :             "All",
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

row1_cols = st.columns([1, 1, 1, 1])

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

with row1_cols[3]:
    orb_true = st.selectbox(
        "ORB True/False",
        options=["All"] + [True, False],
        key="orb_true_filter"
    )


#########################################
### Filter Mapping
#########################################   

# map each filter to its column
inclusion_map = {
    "orb_conf_direction":       "orb_conf_direction_filter",
    "orb_conf_time":            "orb_conf_time_filter",
    "orb_range_direction" :     "orb_range_direction_filter",
    "orb_true" :                "orb_true_filter",

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
st.markdown("""
<small style='color:gray'>
    <span title='High and low times measured for duration the range spans, typically from 9:30 to 10:30. ORB open is typically 9:30 open and touch times are calculated after the confirmation (touches before confirmation are not considered).' style='cursor: help;'>❓</span>
</small>
""", unsafe_allow_html=True)

time_cols = [
    "range_high_time",
    "range_low_time",
    "orb_open_touch_time",
]

time_titles = [
    "Range High Time",
    "Range Low Time",
    "ORB Open Touch Time After Conf.",
]

time_col_layout = st.columns(len(time_cols))

# Generate time order from all relevant columns (not just one)
all_times = pd.concat([df_filtered[col] for col in time_cols]).dropna().unique()
order = sorted(all_times)
order = [t.strftime("%H:%M") if hasattr(t, "strftime") else str(t) for t in order]
order.append("Untouched")  # For missing values we fill with "Untouched"


for col_container, col_name, title in zip(time_col_layout, time_cols, time_titles):
    series = df_filtered[col_name].fillna("Untouched")

    # Convert times to string format for easier plotting (e.g. "10:30")
    series = series.apply(lambda t: t.strftime("%H:%M") if hasattr(t, "strftime") else str(t))

    counts = (
        series
        .value_counts(normalize=True)
        .reindex(order, fill_value=0)
    )
    
    perc = counts * 100
    perc = perc[perc>0]
 
    fig = px.bar(
        x=perc.index,
        y=perc.values,
        text=[f"{v:.1f}%" for v in perc.values],
        title=title,
        labels={"x": "", "y": ""},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis_tickangle=90,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(showticklabels=False),
    )

    col_container.plotly_chart(fig, use_container_width=True)

#########################################################
### Max Retracements
#########################################################
# Handle inf values
df_filtered = df_filtered.replace([np.inf, -np.inf], np.nan).dropna(subset=["max_ret_pct"])

bin_width = float(selected_bin_size) 

# Align bin edges to nearest multiples of bin_width
min_edge = np.floor(df_filtered['max_ret_pct'].min() / bin_width) * bin_width
max_edge = np.ceil(df_filtered['max_ret_pct'].max() / bin_width) * bin_width

# Construct bins
bins = np.arange(min_edge, max_edge + bin_width, bin_width)

# Optional: pretty bin labels
labels = [f"[{bins[i]:.1f}, {bins[i+1]:.1f})" for i in range(len(bins) - 1)]

# Bucket the data with left-closed bins
df_filtered["max_ret_bucket"] = pd.cut(
    df_filtered["max_ret_pct"],
    bins=bins,
    labels=labels,
    include_lowest=True,
    right=False
)

counts = df_filtered['max_ret_bucket'].value_counts(normalize=True).sort_index()
perc = counts * 100

st.markdown("""
<small style='color:gray'>
    <span title='Retracements and extensions easured from the wick high and low of the ORB range (5m or 15m). Percentage retracement after ORB confirmation.' style='cursor: help;'>❓</span>
</small>
""", unsafe_allow_html=True)

fig = px.bar(
    x=perc.index.astype(str),
    y=perc.values,
    text=[f"{v:.1f}%" for v in perc.values],
    title="ORB Max Retracements",
    labels={"x": "Retracement Bucket", "y": ""},
)
fig.update_traces(textposition="outside")
fig.update_layout(
    xaxis_tickangle=45,
    margin=dict(l=10, r=10, t=30, b=10),
    yaxis=dict(showticklabels=False),
)

st.plotly_chart(fig, use_container_width=True)

#########################################################
### Max Extensions
#########################################################
# Align bin edges to nearest multiples of bin_width
min_edge = np.floor(df_filtered['max_ext_pct'].min() / bin_width) * bin_width
max_edge = np.ceil(df_filtered['max_ext_pct'].max() / bin_width) * bin_width

# Construct bins
bins = np.arange(min_edge, max_edge + bin_width, bin_width)

# Optional: pretty bin labels
labels = [f"[{bins[i]:.1f}, {bins[i+1]:.1f})" for i in range(len(bins) - 1)]

# Bucket the data with left-closed bins
df_filtered["max_ext_bucket"] = pd.cut(
    df_filtered["max_ext_pct"],
    bins=bins,
    labels=labels,
    include_lowest=True,
    #right=False
)

counts = df_filtered['max_ext_bucket'].value_counts(normalize=True).sort_index()
perc = counts * 100

fig = px.bar(
    x=perc.index.astype(str),
    y=perc.values,
    text=[f"{v:.1f}%" for v in perc.values],
    title="ORB Max Extensions",
    labels={"x": "Extension Bucket", "y": ""},
)
fig.update_traces(textposition="outside")
fig.update_layout(
    xaxis_tickangle=45,
    margin=dict(l=10, r=10, t=30, b=10),
    yaxis=dict(showticklabels=False),
)

st.plotly_chart(fig, use_container_width=True)

#########################################################
### Max retracement/extension Time
#########################################################
time_cols2 = [
    "max_ret_time",
    "max_ext_time",]

time_titles2 = [
    "ORB Max Retracement Time",
    "ORB Max Extension Time",
]

time_col_layout2 = st.columns(len(time_cols2))

# Generate time order from all relevant columns (not just one)
all_times2 = pd.concat([df_filtered[col] for col in time_cols2]).dropna().unique()
order2 = sorted(all_times)
order2 = [t.strftime("%H:%M") if hasattr(t, "strftime") else str(t) for t in order2]

for col_container, col_name, title in zip(time_col_layout2, time_cols2, time_titles2):
    series = df_filtered[col_name].dropna()

    # Convert times to string format for easier plotting (e.g. "10:30")
    series = series.apply(lambda t: t.strftime("%H:%M") if hasattr(t, "strftime") else str(t))

    counts = (
        series
        .value_counts(normalize=True)
        .reindex(order, fill_value=0)
    )
    
    perc = counts * 100
    perc = perc[perc>0]

    fig = px.bar(
        x=perc.index,
        y=perc.values,
        text=[f"{v:.1f}%" for v in perc.values],
        title=title,
        labels={"x": "", "y": ""},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis_tickangle=90,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis=dict(showticklabels=False),
    )

    col_container.plotly_chart(fig, use_container_width=True)

st.caption(f"Sample size: {len(df_filtered):,} rows")
