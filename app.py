import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import plotly.graph_objects as go
import plotly.express as px
from scipy.spatial.distance import cdist
import streamlit.components.v1 as components

# Configuration for Google Analytics
google_analytics_code = """
<script async src="https://www.googletagmanager.com/gtag/js?id=G-S9KYKX4DZV"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-S9KYKX4DZV');
</script>
"""

components.html(google_analytics_code, height=0)

st.set_page_config(
    page_title="LecturEColorée",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
        .main {
            padding-top: 2rem;
        }
        .stTabs [data-baseweb="tab-list"] button {
            font-size: 18px;
            padding: 10px 20px;
        }
        h1, h2, h3 {
            color: #2c3e50;
            font-weight: 700;
        }
        .streamlit-expanderHeader {
            background-color: #f0f2f6;
            padding: 10px;
            border-radius: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'selected_columns' not in st.session_state:
    st.session_state.selected_columns = []

def load_data(file):
    """Load data from uploaded file"""
    try:
        if file.name.endswith('.csv'):
            return pd.read_csv(file)
        elif file.name.endswith('.xlsx'):
            return pd.read_excel(file)
        else:
            st.error("Please upload a CSV or Excel file")
            return None
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

def calculate_statistics(data):
    """Calculate basic statistics for numerical columns"""
    return data.describe()

def perform_pca(data, n_components=2):
    """Perform PCA on the data"""
    try:
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data)
        pca = PCA(n_components=n_components)
        principal_components = pca.fit_transform(scaled_data)
        return principal_components, pca.explained_variance_ratio_
    except Exception as e:
        st.error(f"Error performing PCA: {e}")
        return None, None

def perform_kmeans(data, n_clusters=3):
    """Perform K-means clustering"""
    try:
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(scaled_data)
        return clusters, kmeans
    except Exception as e:
        st.error(f"Error performing K-means: {e}")
        return None, None

def plot_distribution(data, column):
    """Plot distribution of a column"""
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(data=data, x=column, kde=True, ax=ax, color='steelblue')
    ax.set_title(f'Distribution of {column}', fontsize=16, fontweight='bold')
    ax.set_xlabel(column)
    ax.set_ylabel('Frequency')
    return fig

def plot_correlation_heatmap(data):
    """Plot correlation heatmap"""
    fig, ax = plt.subplots(figsize=(12, 10))
    correlation_matrix = data.corr()
    sns.heatmap(correlation_matrix, annot=True, fmt='.2f', cmap='coolwarm', ax=ax, square=True)
    ax.set_title('Correlation Heatmap', fontsize=16, fontweight='bold')
    return fig

def plot_pca(principal_components, labels=None):
    """Plot PCA results"""
    fig = go.Figure()
    
    scatter_kwargs = {
        'x': principal_components[:, 0],
        'y': principal_components[:, 1],
        'mode': 'markers',
        'marker': dict(size=8, opacity=0.7),
    }
    
    if labels is not None:
        scatter_kwargs['marker']['color'] = labels
        scatter_kwargs['marker']['colorscale'] = 'Viridis'
        scatter_kwargs['marker']['showscale'] = True
    
    fig.add_trace(go.Scatter(**scatter_kwargs))
    fig.update_layout(
        title='PCA Visualization',
        xaxis_title='First Principal Component',
        yaxis_title='Second Principal Component',
        hovermode='closest'
    )
    return fig

def plot_boxplot(data):
    """Plot boxplot for all numerical columns"""
    fig = go.Figure()
    for column in data.columns:
        fig.add_trace(go.Box(y=data[column], name=column))
    fig.update_layout(title='Boxplot of Variables', yaxis_title='Value')
    return fig

# Main app
st.title("🎨 LecturEColorée - Data Visualization & Analysis")
st.write("An interactive application for data exploration, clustering, and dimensionality reduction")

# File upload
with st.sidebar:
    st.header("📂 Upload Data")
    uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=['csv', 'xlsx'])
    
    if uploaded_file is not None:
        st.session_state.df = load_data(uploaded_file)
        if st.session_state.df is not None:
            st.success(f"File loaded successfully! Shape: {st.session_state.df.shape}")

# Main content
if st.session_state.df is not None:
    df = st.session_state.df
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Data Overview", "📈 Distributions", "🔗 Correlation", "🎯 Clustering", "📉 PCA"])
    
    # Tab 1: Data Overview
    with tab1:
        st.subheader("Dataset Overview")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rows", df.shape[0])
        with col2:
            st.metric("Columns", df.shape[1])
        with col3:
            st.metric("Missing Values", df.isnull().sum().sum())
        
        st.subheader("First Few Rows")
        st.dataframe(df.head(10), use_container_width=True)
        
        st.subheader("Data Types & Info")
        st.dataframe(df.dtypes, use_container_width=True)
        
        st.subheader("Statistical Summary")
        st.dataframe(calculate_statistics(df), use_container_width=True)
    
    # Tab 2: Distributions
    with tab2:
        st.subheader("Distribution Analysis")
        numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if numerical_cols:
            selected_col = st.selectbox("Select a column to visualize", numerical_cols)
            fig = plot_distribution(df, selected_col)
            st.pyplot(fig)
        else:
            st.warning("No numerical columns found in the dataset")
    
    # Tab 3: Correlation
    with tab3:
        st.subheader("Correlation Analysis")
        numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numerical_cols) > 1:
            fig = plot_correlation_heatmap(df[numerical_cols])
            st.pyplot(fig)
        else:
            st.warning("Need at least 2 numerical columns for correlation analysis")
    
    # Tab 4: Clustering
    with tab4:
        st.subheader("K-Means Clustering")
        numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if numerical_cols:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write("Select features for clustering:")
                selected_features = st.multiselect("Features", numerical_cols, default=numerical_cols[:2] if len(numerical_cols) >= 2 else numerical_cols)
            with col2:
                n_clusters = st.number_input("Number of clusters", min_value=2, max_value=10, value=3)
            
            if selected_features:
                clusters, kmeans = perform_kmeans(df[selected_features], n_clusters=n_clusters)
                if clusters is not None:
                    st.success("Clustering completed!")
                    
                    # Visualization
                    if len(selected_features) == 2:
                        fig = px.scatter(x=df[selected_features[0]], y=df[selected_features[1]], 
                                       color=clusters, labels={'x': selected_features[0], 'y': selected_features[1]},
                                       title='K-Means Clustering Results')
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Perform PCA first for visualization with more than 2 features")
                    
                    # Cluster statistics
                    st.subheader("Cluster Statistics")
                    df['Cluster'] = clusters
                    st.dataframe(df.groupby('Cluster')[selected_features].mean(), use_container_width=True)
        else:
            st.warning("No numerical columns found in the dataset")
    
    # Tab 5: PCA
    with tab5:
        st.subheader("Principal Component Analysis (PCA)")
        numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numerical_cols) > 1:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write("Select features for PCA:")
                selected_features = st.multiselect("Features for PCA", numerical_cols, default=numerical_cols[:2] if len(numerical_cols) >= 2 else numerical_cols)
            with col2:
                n_components = st.number_input("Number of components", min_value=2, max_value=min(len(selected_features), 10), value=2)
            
            if selected_features and len(selected_features) > 0:
                principal_components, variance_ratio = perform_pca(df[selected_features], n_components=n_components)
                if principal_components is not None:
                    st.success("PCA completed!")
                    
                    # Explained variance
                    st.subheader("Explained Variance Ratio")
                    fig_variance = go.Figure()
                    fig_variance.add_trace(go.Bar(x=[f'PC{i+1}' for i in range(len(variance_ratio))], 
                                                   y=variance_ratio, name='Variance Ratio'))
                    fig_variance.update_layout(title='Explained Variance by Component', 
                                             xaxis_title='Principal Component', 
                                             yaxis_title='Variance Ratio')
                    st.plotly_chart(fig_variance, use_container_width=True)
                    
                    # PCA visualization
                    st.subheader("PCA Visualization")
                    fig_pca = plot_pca(principal_components)
                    st.plotly_chart(fig_pca, use_container_width=True)
        else:
            st.warning("Need at least 2 numerical columns for PCA")

else:
    st.info("👈 Please upload a data file to get started")
