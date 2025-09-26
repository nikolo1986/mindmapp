# streamlit run mindmap_mvp.py
import streamlit as st
import pandas as pd
from streamlit_cytoscapejs import cytoscape

st.set_page_config(page_title="Mindmap MVP", layout="wide")
st.title("Mindmap MVP (Canvas + Table)")

# -------------------------------
# Issue type styling
# -------------------------------
STYLEMAP = {
    "Use-Case": {"color": "#1f77b4", "shape": "ellipse", "size": 80},
    "Epic": {"color": "#2ca02c", "shape": "round-rectangle", "size": 70},
    "Story": {"color": "#ff7f0e", "shape": "diamond", "size": 60},
    "Task": {"color": "#7f7f7f", "shape": "triangle", "size": 50},
    "Sub-task": {"color": "#9467bd", "shape": "hexagon", "size": 40},
}

LEVELS = list(STYLEMAP.keys())
COLUMNS = ["ID", "Level", "Summary", "Parent ID", "Blocks"]

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame([
        {"ID": "UC1", "Level": "Use-Case", "Summary": "User Login", "Parent ID": "", "Blocks": ""},
        {"ID": "E1", "Level": "Epic", "Summary": "Authentication", "Parent ID": "UC1", "Blocks": ""},
        {"ID": "S1", "Level": "Story", "Summary": "As a user I want to log in", "Parent ID": "E1", "Blocks": ""},
        {"ID": "T1", "Level": "Task", "Summary": "Build login form", "Parent ID": "S1", "Blocks": ""},
        {"ID": "T2", "Level": "Task", "Summary": "Connect backend", "Parent ID": "S1", "Blocks": "T1"},
    ], columns=COLUMNS)

# -------------------------------
# Sidebar Import / Export
# -------------------------------
st.sidebar.header("Import / Export")

uploaded = st.sidebar.file_uploader("Upload CSV", type=["csv"])
if uploaded:
    st.session_state.df = pd.read_csv(uploaded).fillna("")
    st.sidebar.success("CSV imported.")

csv_bytes = st.session_state.df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("Export CSV", csv_bytes, file_name="mindmap.csv", mime="text/csv")

# -------------------------------
# Table Editor
# -------------------------------
st.subheader("Issue Table")
edited_df = st.data_editor(
    st.session_state.df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Level": st.column_config.SelectboxColumn(options=LEVELS),
        "Summary": st.column_config.TextColumn(),
        "Parent ID": st.column_config.TextColumn(),
        "Blocks": st.column_config.TextColumn(),
        "ID": st.column_config.TextColumn(),
    },
    key="editor"
)
st.session_state.df = edited_df.fillna("")

# -------------------------------
# Cytoscape Graph
# -------------------------------
st.subheader("Mindmap Canvas (drag & drop)")

elements = []
edges = []

for _, r in st.session_state.df.iterrows():
    style = STYLEMAP.get(r["Level"], {"color": "gray", "shape": "ellipse", "size": 50})
    elements.append({
        "data": {"id": r["ID"], "label": f"{r['Level']}: {r['Summary']}"},
        "classes": r["Level"],
    })
    # Parent-child hierarchy
    if r["Parent ID"].strip():
        edges.append({
            "data": {"source": r["Parent ID"], "target": r["ID"], "relation": "hierarchy"}
        })
    # Dependency (blocks)
    if r["Blocks"].strip():
        for tgt in str(r["Blocks"]).split(";"):
            tgt = tgt.strip()
            if tgt:
                edges.append({
                    "data": {"source": r["ID"], "target": tgt, "relation": "dependency"}
                })

elements.extend(edges)

stylesheet = [
    {
        "selector": "node",
        "style": {"label": "data(label)", "text-valign": "center", "text-halign": "center"}
    },
    {"selector": ".Use-Case", "style": {"background-color": "#1f77b4", "width": 80, "height": 80, "shape": "ellipse", "font-size": 16}},
    {"selector": ".Epic", "style": {"background-color": "#2ca02c", "width": 70, "height": 70, "shape": "round-rectangle", "font-size": 14}},
    {"selector": ".Story", "style": {"background-color": "#ff7f0e", "width": 60, "height": 60, "shape": "diamond", "font-size": 12}},
    {"selector": ".Task", "style": {"background-color": "#7f7f7f", "width": 50, "height": 50, "shape": "triangle", "font-size": 10}},
    {"selector": ".Sub-task", "style": {"background-color": "#9467bd", "width": 40, "height": 40, "shape": "hexagon", "font-size": 9}},
    {"selector": "edge[relation = 'hierarchy']", "style": {"curve-style": "bezier", "target-arrow-shape": "triangle", "line-color": "#999", "target-arrow-color": "#999"}},
    {"selector": "edge[relation = 'dependency']", "style": {"curve-style": "bezier", "target-arrow-shape": "vee", "line-color": "red", "target-arrow-color": "red", "line-style": "dashed"}},
]

cytoscape(
    elements=elements,
    layout={"name": "breadthfirst", "directed": True, "spacingFactor": 1.5},
    stylesheet=stylesheet,
    style={"width": "100%", "height": "700px"},
    key="cyto"
)

# -------------------------------
# HTML Export
# -------------------------------
import json

html_export = f"""
<html>
<head>
  <script src="https://unpkg.com/cytoscape/dist/cytoscape.min.js"></script>
</head>
<body>
  <div id="cy" style="width: 100%; height: 100vh;"></div>
  <script>
    var cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: {json.dumps(elements)},
      style: {json.dumps(stylesheet)},
      layout: {{ name: 'breadthfirst', directed: true, spacingFactor: 1.5 }},
      wheelSensitivity: 0.2
    }});
  </script>
</body>
</html>
"""

st.download_button("Export Interactive HTML", html_export, file_name="mindmap.html", mime="text/html")