import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
from io import StringIO

# Helper functions
def create_network(df):
    G = nx.DiGraph()
    for _, row in df.iterrows():
        node_id = row['ID']
        label = f"{row['Level']}: {row['Summary']}"
        G.add_node(node_id, label=label, level=row['Level'], summary=row['Summary'])
        if pd.notna(row['Parent ID']):
            G.add_edge(row['Parent ID'], node_id)
        if pd.notna(row.get('Blocks')):
            for blocker in str(row['Blocks']).split(';'):
                if blocker.strip():
                    G.add_edge(node_id, blocker.strip(), color='red')
    return G

def display_network(G, height="750px", width="100%"):
    net = Network(height=height, width=width, directed=True)
    net.from_nx(G)
    net.repulsion(node_distance=200, spring_length=200)
    return net

def export_csv(df):
    return df.to_csv(index=False)

def export_html(G):
    net = display_network(G)
    return net.generate_html()

# Streamlit UI
st.set_page_config(page_title="Mindmap to Jira", layout="wide")
st.title("Mindmap to Jira Export Tool")

st.sidebar.header("Import/Export")
uploaded_file = st.sidebar.file_uploader("Upload CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
else:
    st.sidebar.write("No file uploaded. Using sample data.")
    df = pd.DataFrame([
        {"ID": "UC1", "Level": "Use-Case", "Summary": "User Login", "Parent ID": "", "Blocks": ""},
        {"ID": "E1", "Level": "Epic", "Summary": "Authentication", "Parent ID": "UC1", "Blocks": ""},
        {"ID": "S1", "Level": "Story", "Summary": "As a user I want to login", "Parent ID": "E1", "Blocks": ""},
        {"ID": "T1", "Level": "Task", "Summary": "Build login form", "Parent ID": "S1", "Blocks": ""},
        {"ID": "T2", "Level": "Task", "Summary": "Connect backend", "Parent ID": "S1", "Blocks": "T1"}
    ])

# Show data
st.subheader("Current Items")
st.dataframe(df)

# Create and display network
G = create_network(df)
st.subheader("Mindmap")
net = display_network(G)
html_str = net.generate_html()
st.components.v1.html(html_str, height=750, scrolling=True)

# Export options
st.sidebar.subheader("Export")
csv_data = export_csv(df)
st.sidebar.download_button("Export CSV", csv_data, file_name="jira_export.csv", mime="text/csv")

html_data = export_html(G)
st.sidebar.download_button("Export HTML", html_data, file_name="mindmap.html", mime="text/html")