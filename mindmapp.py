# streamlit run mindmap_html.py
import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Mindmap (Context Menu Long-Press)", layout="wide")
st.title("Mindmap MVP (Cytoscape + Context Menu)")

# ------------------------------------------------
# Toggle: use local static files later (Posit)
# ------------------------------------------------
USE_LOCAL = False  # set True when you place cytoscape.min.js in ./static/

CY_SRC = "static/cytoscape.min.js" if USE_LOCAL else "https://unpkg.com/cytoscape/dist/cytoscape.min.js"

# ------------------------------------------------
# Sample data / table editing
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

st.sidebar.header("Import / Export")
up = st.sidebar.file_uploader("Upload CSV", type=["csv"])
if up:
    st.session_state.df = pd.read_csv(up).fillna("")
    st.sidebar.success("CSV imported")

csv_bytes = st.session_state.df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("Export CSV", csv_bytes, "mindmap.csv", "text/csv")

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
# HTML embed with a custom context menu that works
# on right-click (desktop) and long-press (mobile).
# ------------------------------------------------
html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script src="{CY_SRC}"></script>
  <style>
    /* Make sure the canvas captures touch; avoid iOS callouts */
    #cy {{
      width: 100%;
      height: 700px;
      -webkit-touch-callout: none;
      -webkit-user-select: none;
      user-select: none;
      touch-action: none; /* improves long-press reliability */
      background: #ffffff;
    }}
    /* Simple custom context menu */
    #ctx {{
      position: absolute;
      display: none;
      background: rgba(30, 30, 30, 0.95);
      color: #fff;
      border-radius: 8px;
      padding: 8px;
      z-index: 9999;
      min-width: 140px;
      box-shadow: 0 6px 16px rgba(0,0,0,0.35);
      font-family: sans-serif;
      font-size: 14px;
    }}
    #ctx button {{
      width: 100%;
      display: block;
      background: transparent;
      border: none;
      color: #fff;
      text-align: left;
      padding: 6px 8px;
      cursor: pointer;
    }}
    #ctx button:hover {{
      background: rgba(255,255,255,0.12);
    }}
  </style>
</head>
<body>
  <div id="cy"></div>
  <div id="ctx">
    <button id="ctx-add">Add Child</button>
    <button id="ctx-del">Delete Node</button>
    <button id="ctx-cancel">Cancel</button>
  </div>

  <script>
    var cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: {json.dumps(elements)},
      style: {json.dumps(stylesheet)},
      layout: {{ name: 'breadthfirst', directed: true, spacingFactor: 1.5 }},
      wheelSensitivity: 0.2
    }});

    var menu = document.getElementById('ctx');
    var addBtn = document.getElementById('ctx-add');
    var delBtn = document.getElementById('ctx-del');
    var cancelBtn = document.getElementById('ctx-cancel');
    var lastNode = null;

    function showMenu(node, px, py) {{
      lastNode = node;
      var rect = cy.container().getBoundingClientRect();
      menu.style.left = (rect.left + px) + 'px';
      menu.style.top  = (rect.top + py) + 'px';
      menu.style.display = 'block';
    }}

    function hideMenu() {{
      menu.style.display = 'none';
      lastNode = null;
    }}

    // Right-click (desktop) -> 'cxttap'
    cy.on('cxttap', 'node', function(e) {{
      var rp = e.renderedPosition || e.position;
      showMenu(e.target, rp.x, rp.y);
    }});

    // Long-press (mobile) -> 'taphold'
    cy.on('taphold', 'node', function(e) {{
      var rp = e.renderedPosition || e.position;
      showMenu(e.target, rp.x, rp.y);
    }});

    // Hide when clicking elsewhere
    cy.on('tap', function(e) {{
      if (e.target === cy) hideMenu();
    }});
    document.addEventListener('scroll', hideMenu, true);

    // Menu actions
    addBtn.addEventListener('click', function() {{
      if (!lastNode) return;
      var newId = 'N' + Date.now();
      var p = lastNode.position();
      cy.add({{ data: {{ id: newId, label: 'New Child' }}, position: {{ x: p.x + 60, y: p.y + 60 }} }});
      cy.add({{ data: {{ source: lastNode.id(), target: newId, relation: 'hierarchy' }} }});
      hideMenu();
    }});

    delBtn.addEventListener('click', function() {{
      if (!lastNode) return;
      cy.remove(lastNode);
      hideMenu();
    }});

    cancelBtn.addEventListener('click', hideMenu);

    // Prevent browser native context menu on the canvas
    cy.container().addEventListener('contextmenu', function(e) {{ e.preventDefault(); }});
  </script>
</body>
</html>
"""

st.subheader("Mindmap Canvas (right-click or long-press a node)")
st.components.v1.html(html, height=720, scrolling=True)

# Export the exact same HTML you see
st.download_button("Export Interactive HTML", html, file_name="mindmap.html", mime="text/html")