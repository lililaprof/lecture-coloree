import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from streamlit_theme import st_theme
import streamlit.components.v1 as components
import os

# Set page config
st.set_page_config(
    page_title="Lecture Colorée",
    page_icon="🌈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Google Analytics tracking code
GA_ID = "G-XXXXXXXXXX"
gtag_script = f"""
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{GA_ID}');
</script>
"""

# Inject Google Analytics
components.html(gtag_script, height=0)

# Title and description
st.title("🌈 Lecture Colorée")
st.markdown("""
Bienvenue dans **Lecture Colorée**, une application interactive pour explorer les données et visualiser les tendances.
""")

# Create sample data
np.random.seed(42)
df = pd.DataFrame({
    'Date': pd.date_range('2024-01-01', periods=100),
    'Ventes': np.random.randint(100, 1000, 100),
    'Visiteurs': np.random.randint(500, 5000, 100),
    'Catégorie': np.random.choice(['A', 'B', 'C', 'D'], 100)
})

# Sidebar controls
st.sidebar.header("Paramètres")
selected_category = st.sidebar.multiselect(
    "Sélectionnez une catégorie:",
    df['Catégorie'].unique(),
    default=df['Catégorie'].unique()
)

date_range = st.sidebar.date_input(
    "Plage de dates:",
    value=(df['Date'].min().date(), df['Date'].max().date()),
    min_value=df['Date'].min().date(),
    max_value=df['Date'].max().date()
)

# Filter data
filtered_df = df[
    (df['Catégorie'].isin(selected_category)) &
    (df['Date'].dt.date >= date_range[0]) &
    (df['Date'].dt.date <= date_range[1])
]

# Main content area
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Ventes au fil du temps")
    fig_sales = px.line(
        filtered_df,
        x='Date',
        y='Ventes',
        color='Catégorie',
        title="Tendance des ventes"
    )
    st.plotly_chart(fig_sales, use_container_width=True)

with col2:
    st.subheader("👥 Visiteurs")
    fig_visitors = px.bar(
        filtered_df,
        x='Catégorie',
        y='Visiteurs',
        color='Catégorie',
        title="Visiteurs par catégorie"
    )
    st.plotly_chart(fig_visitors, use_container_width=True)

# Display data table
st.subheader("📋 Données brutes")
st.dataframe(filtered_df, use_container_width=True)

# Statistics section
st.subheader("📈 Statistiques")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Ventes", f"${filtered_df['Ventes'].sum():,.0f}")

with col2:
    st.metric("Total Visiteurs", f"{filtered_df['Visiteurs'].sum():,.0f}")

with col3:
    st.metric("Moyenne Ventes/Visiteur", f"${filtered_df['Ventes'].sum() / filtered_df['Visiteurs'].sum():.2f}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 12px;'>
        Créé avec ❤️ | Lecture Colorée © 2024
    </div>
    """,
    unsafe_allow_html=True
)
