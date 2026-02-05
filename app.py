import os
import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================================
# Configuration
# ============================================================================
BASE_DIR = os.path.dirname(__file__)
CO2_PATH = os.path.join("data", "CO2_per_capita.csv")
GEO_PATH = os.path.join("data", "geo_data.csv")

st.set_page_config(page_title="CO2 per Country", layout="wide", initial_sidebar_state="expanded")


# ============================================================================
# Data Loading & Processing
# ============================================================================
@st.cache_data
def load_co2_data(path: str) -> pd.DataFrame:
    """Load CO2 data with error handling."""
    try:
        return pd.read_csv(path, delimiter=";")
    except FileNotFoundError:
        st.error(f"Data file not found: {path}")
        return pd.DataFrame()


@st.cache_data
def load_geo_data(path: str) -> pd.DataFrame:
    """Load and deduplicate geographic data."""
    try:
        countries = pd.read_csv(path)
        return countries[["Continent_Name", "Three_Letter_Country_Code"]].drop_duplicates()
    except FileNotFoundError:
        st.error(f"Geography file not found: {path}")
        return pd.DataFrame()


@st.cache_data
def merge_datasets(df: pd.DataFrame, geo: pd.DataFrame) -> pd.DataFrame:
    """Merge CO2 and geographic data once."""
    return df.merge(
        geo, 
        left_on="Country Code", 
        right_on="Three_Letter_Country_Code", 
        how="left"
    )


# ============================================================================
# Data Aggregation Functions
# ============================================================================
def get_top_emitters(
    df: pd.DataFrame, start_year: int, end_year: int, n: int
) -> pd.DataFrame:
    """Get top n CO2 emitters by average."""
    return (
        df[(df["Year"] >= start_year) & (df["Year"] <= end_year)]
        .groupby("Country Name", as_index=False)["CO2 Per Capita (metric tons)"]
        .mean()
        .sort_values("CO2 Per Capita (metric tons)", ascending=False)
        .head(n)
    )


def get_top_emitters_with_geo(
    df: pd.DataFrame, start_year: int, end_year: int, n: int
) -> pd.DataFrame:
    """Get top n emitters with geographic data."""
    return (
        df[(df["Year"] >= start_year) & (df["Year"] <= end_year)]
        .groupby(
            ["Country Name", "Country Code", "Continent_Name"], 
            as_index=False
        )["CO2 Per Capita (metric tons)"]
        .mean()
        .sort_values("CO2 Per Capita (metric tons)", ascending=False)
        .head(n)
    )


# ============================================================================
# Visualization Functions
# ============================================================================
def create_bar_chart(df: pd.DataFrame, color_col: str = None, title: str = "Top Emitters") -> px.bar:
    """Create styled bar chart."""
    fig = px.bar(
        df,
        x="Country Name",
        y="CO2 Per Capita (metric tons)",
        color=color_col,
        title=title,
        labels={"CO2 Per Capita (metric tons)": "CO2 per Capita (metric tons)"},
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        height=500,
        showlegend=True if color_col else False,
    )
    return fig


def create_map_chart(df: pd.DataFrame, title: str = "Top Emitters on Map") -> px.scatter_geo:
    """Create geo scatter chart."""
    fig = px.scatter_geo(
        df,
        locations="Country Code",
        size="CO2 Per Capita (metric tons)",
        hover_name="Country Name",
        title=title,
        projection="natural earth",
    )
    fig.update_layout(height=500, geo=dict(showland=True, landcolor="rgb(243, 243, 243)"))
    return fig


def create_choropleth(df: pd.DataFrame, title: str = "CO2 per Capita") -> px.choropleth:
    """Create choropleth map."""
    fig = px.choropleth(
        df,
        locations="Country Code",
        color="CO2 Per Capita (metric tons)",
        hover_name="Country Name",
        color_continuous_scale="Reds",
        title=title,
    )
    fig.update_layout(height=500, geo=dict(showland=True, landcolor="rgb(243, 243, 243)"))
    return fig


# ============================================================================
# Main App
# ============================================================================
def main():
    st.title("🌍 CO2 per Country Investigation")
    
    # Load data
    df = load_co2_data(CO2_PATH)
    geo = load_geo_data(GEO_PATH)
    
    if df.empty or geo.empty:
        st.error("Failed to load required data files.")
        return
    
    merged_df = merge_datasets(df, geo)
    
    # Sidebar controls
    with st.sidebar:
        st.header("Filters")
        year_range = st.slider(
            "Year range", 
            min_value=int(df["Year"].min()), 
            max_value=int(df["Year"].max()), 
            value=(2008, 2011)
        )
        nb_countries = st.selectbox(
            "Number of countries", 
            options=[3, 5, 10, 20, 30],
            index=2
        )
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Years Selected", f"{year_range[0]} - {year_range[1]}")
    with col2:
        st.metric("Top Countries", nb_countries)
    with col3:
        st.metric("Data Points", f"{len(df):,}")
    
    st.divider()
    
    # Charts
    st.subheader("📊 Top CO2 Emitters")
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        top_df = get_top_emitters(df, year_range[0], year_range[1], nb_countries)
        st.plotly_chart(
            create_bar_chart(top_df, title="Top Emitters by Average CO2 per Capita"),
            use_container_width=True
        )
    
    with col2:
        st.info("📌 Shows average CO2 emissions per capita for selected period")
    
    st.divider()
    
    st.subheader("🗺️ Geographic Distribution")
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        geo_df = get_top_emitters_with_geo(merged_df, year_range[0], year_range[1], nb_countries)
        st.plotly_chart(
            create_map_chart(geo_df),
            use_container_width=True
        )
    
    with col2:
        st.info("🌐 Interactive map showing top emitter locations")
    
    st.divider()
    
    st.subheader("🌐 Emissions by Continent")
    continent_df = get_top_emitters_with_geo(merged_df, year_range[0], year_range[1], nb_countries)
    st.plotly_chart(
        create_bar_chart(
            continent_df, 
            color_col="Continent_Name",
            title="Top Emitters Colored by Continent"
        ),
        use_container_width=True
    )
    
    st.divider()
    
    st.subheader("🔥 Choropleth Map")
    choropleth_df = get_top_emitters_with_geo(merged_df, year_range[0], year_range[1], nb_countries)
    st.plotly_chart(
        create_choropleth(choropleth_df),
        use_container_width=True
    )
    
    st.divider()
    
    # Data explorer
    if st.checkbox("📋 Show raw data"):
        st.subheader("Raw Data")
        st.dataframe(
            get_top_emitters_with_geo(merged_df, year_range[0], year_range[1], nb_countries),
            use_container_width=True
        )


if __name__ == "__main__":
    main()