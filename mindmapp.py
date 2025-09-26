# streamlit run mindmap_html.py
import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Mindmap with Table Sync", layout="wide")
st.title("Mindmap MVP (Canvas + Table + Add Child)")

# ------------------------------------------------
# Toggle: use local Cytoscape later (Posit Connect)
# ------------------------------------------------
USE_LOCAL = False  # set True when you bundle cytoscape.min.js in ./static/

CY_SRC = "static/cytoscape.min.js" if USE_LOCAL else "https://unpkg.com/cytoscape/dist/cytoscape.min.js"

# ------------------------------------------------
# Sample dataset / editable table
# ------------------------------------------------
DEFAULT_ROWS = [
    {"ID": "UC1", "Level": "Use-Case", "Summary": "User Login", "Parent ID": "", "Blocks": ""},
    {"ID": "E1",  "Level": "Epic",     "Summary": "Authentication", "Parent ID": "UC1", "Blocks": ""},
    {"ID": "S1",  "Level": "Story",    "Summary": "As a user I want to log in", "Parent ID": "E1", "Blocks": ""},
    {"ID": "T1",  "Level": "Task",     "Summary": "Build login form", "Parent ID": "S1", "Blocks": ""},
    {"ID": "T2",  "Level": "Task",     "Summary": "Connect backend",  "Parent ID": "S1", "Blocks": "T1"},
]

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(DEFAULT_ROWS)

# ------------------------------------------------
# Sidebar: Import/Export
# ------------------------------------------------
st.sidebar.header("Import / Export")
up = st.sidebar.file_uploader("Upload CSV", type=["csv"])
if up:
    st.session_state.df = pd.read_csv(up).fillna("")
    st.sidebar.success("CSV imported")

csv_bytes = st.session_state.df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("Export CSV", csv_bytes, "mindmap.csv", "text/csv")

# ------------------------------------------------
# Sidebar: Add Child Issue
# ------------------------------------------------
st.sidebar.subheader("Add Child Issue")

with st.sidebar.form("add_child_form"):
    parent_id = st.selectbox(
        "Select Parent ID",
        options=[""] + st.session_state.df["ID"].tolist(),
        help="Pick a parent issue from the table",
    )
    child_name = st.text_input("Child Summary")
    submit = st.form_submit_button("Add Child")

if submit and parent_id and child_name:
    parent_row = st.session_state.df.loc[st.session_state.df["ID"] == parent_id]
    if not parent_row.empty:
        parent_level = parent_row.iloc[0]["Level"]

        # infer child type
        if parent_level == "Use-Case":
            child_type = "Epic"
        elif parent_level == "Epic":
            child_type = "Story"
        elif parent_level == "Story":
            child_type = "Task"
        elif parent_level == "Task":
            child_type = "Sub-task"
        else:
            child_type = "Task"

        new_id = child_type[:2].upper() + str(pd.Timestamp.now().value)
        new_row = {
            "ID": new_id,
            "Level": child_type,
            "Summary": child_name,
            "Parent ID": parent_id,
            "Blocks": ""
        }
        st.session_state.df = pd.concat(
            [st.session_state.df, pd.DataFrame([new_row])], ignore_index=True
        )
        st.sidebar.success(f"Added {child_type}: {child_name} under {parent_id}")

# ------------------------------------------------
# Issue Table (editable)
# ------------------------------------------------
st.subheader("Issue Table")
edited = st.data_editor(st.session_state.df, num_rows="dynamic", use_container_width=True)
st.session_state.df = edited.fillna("")

# ------------------------------------------------
# Build Cytoscape elements + stylesheet
# ------------------------------------------------
elements = []
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
            "text-outline-color": "#000",
            "text-outline-width": 2,
            "text-valign": "center",
            "text-halign": "center"
        }
    },
    {"selector": ".Use-Case", "style": {"background-color": "#1f77b4", "width": 80, "height": 80, "shape": "ellipse", "font-size": 18}},
    {"selector": ".Epic",     "style": {"background-color": "#2ca02c", "width": 70, "height": 70, "shape": "round-rectangle", "font-size": 16}},
    {"selector": ".Story",    "style": {"background-color": "#ff7f0e", "width": 60, "height": 60, "shape": "diamond", "font-size": 14}},
    {"selector": ".Task",     "style": {"background-color": "#7f7f7f", "width": 50, "height": 50, "shape": "triangle", "font-size": 12}},
    {"selector": ".Sub-task", "style": {"background-color": "#9467bd", "width": 40, "height": 40, "shape": "hexagon", "font-size": 11}},
    {"selector": "edge[relation = 'hierarchy']",
     "style": {"curve-style": "bezier", "target-arrow-shape": "triangle", "line-color": "#999", "target-arrow-color": "#999"}},
    {"selector": "edge[relation = 'dependency']",
     "style": {"curve-style": "bezier", "target-arrow-shape": "vee", "line-color": "red", "target-arrow-color": "red", "line-style": "dashed"}},
]

# ------------------------------------------------
# HTML embed (render graph only; add child via sidebar)
# ------------------------------------------------
html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script src="{CY_SRC}"></script>
  <style>
    #cy {{
      width: 100%;
      height: 700px;
      background: #ffffff;
    }}
  </style>
</head>
<body>
  <div id="cy"></div>
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

st.subheader("Mindmap Canvas (auto-updates from table)")
st.components.v1.html(html, height=720, scrolling=True)

# ------------------------------------------------
# Export the HTML
# ------------------------------------------------
st.download_button("Export Interactive HTML", html, file_name="mindmap.html", mime="text/html")