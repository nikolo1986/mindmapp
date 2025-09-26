# streamlit run mindmap_html.py
import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Mindmap MVP (Cytoscape Toggle)", layout="wide")
st.title("Mindmap MVP (Cytoscape.js with Toggle for CDN/Local)")

# ----------------------------
# Config: toggle between CDN and local static file
# ----------------------------
USE_LOCAL = False  # set True when cytoscape.min.js is downloaded to static/

cytoscape_src = (
    "static/cytoscape.min.js"
    if USE_LOCAL
    else "https://unpkg.com/cytoscape/dist/cytoscape.min.js"
)

# ----------------------------
# Default dataset
# ----------------------------
DEFAULT_ROWS = [
    {"ID": "UC1", "Level": "Use-Case", "Summary": "User Login", "Parent ID": "", "Blocks": ""},
    {"ID": "E1",  "Level": "Epic",     "Summary": "Authentication", "Parent ID": "UC1", "Blocks": ""},
    {"ID": "S1",  "Level": "Story",    "Summary": "As a user I want to log in", "Parent ID": "E1", "Blocks": ""},
    {"ID": "T1",  "Level": "Task",     "Summary": "Build login form", "Parent ID": "S1", "Blocks": ""},
    {"ID": "T2",  "Level": "Task",     "Summary": "Connect backend",  "Parent ID": "S1", "Blocks": "T1"},
]

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(DEFAULT_ROWS)

# ----------------------------
# Sidebar: CSV import/export
# ----------------------------
st.sidebar.header("Import / Export")
uploaded = st.sidebar.file_uploader("Upload CSV", type=["csv"])
if uploaded:
    st.session_state.df = pd.read_csv(uploaded).fillna("")
    st.sidebar.success("CSV imported.")

csv_bytes = st.session_state.df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("Export CSV", csv_bytes, file_name="mindmap.csv", mime="text/csv")

# ----------------------------
# Table editor
# ----------------------------
st.subheader("Issue Table")
edited_df = st.data_editor(
    st.session_state.df,
    num_rows="dynamic",
    use_container_width=True,
)
st.session_state.df = edited_df.fillna("")

# ----------------------------
# Build Cytoscape elements
# ----------------------------
elements = []
STYLEMAP = {
    "Use-Case": {"color": "#1f77b4", "shape": "ellipse", "size": 80, "font": 18},
    "Epic": {"color": "#2ca02c", "shape": "round-rectangle", "size": 70, "font": 16},
    "Story": {"color": "#ff7f0e", "shape": "diamond", "size": 60, "font": 14},
    "Task": {"color": "#7f7f7f", "shape": "triangle", "size": 50, "font": 12},
    "Sub-task": {"color": "#9467bd", "shape": "hexagon", "size": 40, "font": 11},
}

for _, r in st.session_state.df.iterrows():
    elements.append({
        "data": {"id": r["ID"], "label": f"{r['Level']}: {r['Summary']}"},
        "classes": r["Level"],
    })
    if r["Parent ID"].strip():
        elements.append({"data": {"source": r["Parent ID"], "target": r["ID"], "relation": "hierarchy"}})
    if r["Blocks"].strip():
        for tgt in str(r["Blocks"]).split(";"):
            tgt = tgt.strip()
            if tgt:
                elements.append({"data": {"source": r["ID"], "target": tgt, "relation": "dependency"}})

stylesheet = [
    {
        "selector": "node",
        "style": {
            "label": "data(label)",
            "color": "white",
            "text-outline-color": "#000000",
            "text-outline-width": 2,
            "text-valign": "center",
            "text-halign": "center"
        }
    },
    {"selector": ".Use-Case", "style": {"background-color": "#1f77b4", "width": 80, "height": 80, "shape": "ellipse", "font-size": 18}},
    {"selector": ".Epic", "style": {"background-color": "#2ca02c", "width": 70, "height": 70, "shape": "round-rectangle", "font-size": 16}},
    {"selector": ".Story", "style": {"background-color": "#ff7f0e", "width": 60, "height": 60, "shape": "diamond", "font-size": 14}},
    {"selector": ".Task", "style": {"background-color": "#7f7f7f", "width": 50, "height": 50, "shape": "triangle", "font-size": 12}},
    {"selector": ".Sub-task", "style": {"background-color": "#9467bd", "width": 40, "height": 40, "shape": "hexagon", "font-size": 11}},
    {"selector": "edge[relation = 'hierarchy']", "style": {"curve-style": "bezier", "target-arrow-shape": "triangle", "line-color": "#999", "target-arrow-color": "#999"}},
    {"selector": "edge[relation = 'dependency']", "style": {"curve-style": "bezier", "target-arrow-shape": "vee", "line-color": "red", "target-arrow-color": "red", "line-style": "dashed"}},
]

# ----------------------------
# HTML with toggle for Cytoscape source
# ----------------------------
html_str = f"""
<html>
<head>
  <script src="{cytoscape_src}"></script>
</head>
<body>
  <div id="cy" style="width: 100%; height: 700px;"></div>
  <script>
    var cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: {json.dumps(elements)},
      style: {json.dumps(stylesheet)},
      layout: {{ name: 'breadthfirst', directed: true, spacingFactor: 1.5 }},
      wheelSensitivity: 0.2
    }});

    // Add child node on right-click/long-press
    cy.on('cxttap', 'node', function(evt){{
      var node = evt.target;
      var newId = "N" + Date.now();
      cy.add({{
        data: {{ id: newId, label: "New Child" }},
        position: {{ x: node.position('x') + 60, y: node.position('y') + 60 }}
      }});
      cy.add({{
        data: {{ source: node.id(), target: newId, relation: "hierarchy" }}
      }});
    }});
  </script>
</body>
</html>
"""

st.subheader("Mindmap Canvas (Interactive)")
st.components.v1.html(html_str, height=720, scrolling=True)

# ----------------------------
# Export HTML
# ----------------------------
st.download_button("Export Interactive HTML", html_str, file_name="mindmap.html", mime="text/html")