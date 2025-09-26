# streamlit run mindmap_html.py
import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Mindmap with Canvas Menu + Table Sync", layout="wide")
st.title("Mindmap MVP (Press & Hold Menu + Sidebar Persistence)")

# ----------------------------
# Toggle: use local Cytoscape later (Posit Connect)
# ----------------------------
USE_LOCAL = False  # set True when you bundle cytoscape.min.js in ./static/
CY_SRC = "static/cytoscape.min.js" if USE_LOCAL else "https://unpkg.com/cytoscape/dist/cytoscape.min.js"

# ----------------------------
# Sample dataset / editable table
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
# Sidebar: Import / Export
# ----------------------------
st.sidebar.header("Import / Export")
up = st.sidebar.file_uploader("Upload CSV", type=["csv"])
if up:
    st.session_state.df = pd.read_csv(up).fillna("")
    st.sidebar.success("CSV imported")

csv_bytes = st.session_state.df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("Export CSV", csv_bytes, "mindmap.csv", "text/csv")

# ----------------------------
# Sidebar: Add Child (persists to table/CSV)
# ----------------------------
st.sidebar.subheader("Add Child Issue (persists)")
parent_choices = [""] + st.session_state.df["ID"].tolist()
with st.sidebar.form("add_child_form"):
    parent_id = st.selectbox("Parent ID", options=parent_choices, help="Pick a parent issue")
    child_name = st.text_input("Child Summary")
    submit = st.form_submit_button("Add Child")

def infer_child_type(parent_level: str) -> str:
    if parent_level == "Use-Case":
        return "Epic"
    if parent_level == "Epic":
        return "Story"
    if parent_level == "Story":
        return "Task"
    if parent_level == "Task":
        return "Sub-task"
    return "Task"

if submit and parent_id and child_name:
    parent_row = st.session_state.df.loc[st.session_state.df["ID"] == parent_id]
    if not parent_row.empty:
        parent_level = parent_row.iloc[0]["Level"]
        child_type = infer_child_type(parent_level)
        new_id = child_type[:2].upper() + str(pd.Timestamp.now().value)
        new_row = {
            "ID": new_id,
            "Level": child_type,
            "Summary": child_name,
            "Parent ID": parent_id,
            "Blocks": ""
        }
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
        st.sidebar.success(f"Added {child_type}: {child_name} under {parent_id}")

# ----------------------------
# Issue Table (editable)
# ----------------------------
st.subheader("Issue Table")
edited = st.data_editor(st.session_state.df, num_rows="dynamic", use_container_width=True)
st.session_state.df = edited.fillna("")

# ----------------------------
# Build Cytoscape elements + stylesheet
# ----------------------------
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

# ----------------------------
# HTML embed (press & hold menu + hint bar)
# ----------------------------
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
      -webkit-touch-callout: none;
      -webkit-user-select: none;
      user-select: none;
      touch-action: none;
    }}
    /* Simple context menu */
    #ctx {{
      position: absolute;
      display: none;
      background: rgba(30,30,30,0.95);
      color: #fff;
      border-radius: 8px;
      padding: 8px;
      z-index: 9999;
      min-width: 160px;
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
    #ctx button:hover {{ background: rgba(255,255,255,0.12); }}

    /* Parent hint bar */
    #hint {{
      position: absolute;
      right: 12px;
      top: 12px;
      background: rgba(0,0,0,0.65);
      color: #fff;
      padding: 6px 10px;
      border-radius: 6px;
      font-family: sans-serif;
      font-size: 13px;
      z-index: 9998;
      display: none;
    }}

    .selected-parent {{
      outline: 4px solid #00c2ff;
      outline-offset: 4px;
    }}
  </style>
</head>
<body>
  <div id="cy"></div>

  <div id="ctx">
    <button id="ctx-mark">Mark as Parent (copy ID)</button>
    <button id="ctx-add">Add Child (visual)</button>
    <button id="ctx-del">Delete Node (visual)</button>
    <button id="ctx-cancel">Cancel</button>
  </div>

  <div id="hint">Selected parent: <span id="pid"></span></div>

  <script>
    var cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: {json.dumps(elements)},
      style: {json.dumps(stylesheet)},
      layout: {{ name: 'breadthfirst', directed: true, spacingFactor: 1.5 }},
      wheelSensitivity: 0.2
    }});

    var menu = document.getElementById('ctx');
    var btnMark = document.getElementById('ctx-mark');
    var btnAdd  = document.getElementById('ctx-add');
    var btnDel  = document.getElementById('ctx-del');
    var btnCancel = document.getElementById('ctx-cancel');
    var hint = document.getElementById('hint');
    var pidSpan = document.getElementById('pid');

    var lastNode = null;
    var selectedParent = null;

    function showMenu(node, px, py) {{
      lastNode = node;
      var rect = cy.container().getBoundingClientRect();
      menu.style.left = (rect.left + px) + 'px';
      menu.style.top  = (rect.top + py) + 'px';
      menu.style.display = 'block';
    }}
    function hideMenu() {{ menu.style.display = 'none'; }}

    function clearParentHighlight() {{
      if (selectedParent) {{
        selectedParent.removeClass('selected-parent');
        selectedParent = null;
        hint.style.display = 'none';
      }}
    }}

    // Right-click (desktop)
    cy.on('cxttap', 'node', function(e) {{
      var rp = e.renderedPosition || e.position;
      showMenu(e.target, rp.x, rp.y);
    }});
    // Long-press (mobile)
    cy.on('taphold', 'node', function(e) {{
      var rp = e.renderedPosition || e.position;
      showMenu(e.target, rp.x, rp.y);
    }});

    // Hide menu on background tap
    cy.on('tap', function(e) {{
      if (e.target === cy) hideMenu();
    }});
    // Prevent native context menu
    cy.container().addEventListener('contextmenu', function(e) {{ e.preventDefault(); }});
    document.addEventListener('scroll', hideMenu, true);

    // ---- Menu actions ----
    // 1) Mark as Parent (highlights + shows ID to copy into sidebar)
    btnMark.addEventListener('click', function() {{
      if (!lastNode) return;
      clearParentHighlight();
      selectedParent = lastNode;
      selectedParent.addClass('selected-parent');
      pidSpan.textContent = selectedParent.id();
      hint.style.display = 'inline-block';
      hideMenu();
    }});

    // 2) Add Child (visual-only, with prompt + correct type)
    function childTypeFor(parentType) {{
      if (parentType === 'Use-Case') return 'Epic';
      if (parentType === 'Epic') return 'Story';
      if (parentType === 'Story') return 'Task';
      if (parentType === 'Task') return 'Sub-task';
      return 'Task';
    }}

    btnAdd.addEventListener('click', function() {{
      if (!lastNode) return;
      var pType = (lastNode.classes() && lastNode.classes().length) ? lastNode.classes()[0] : 'Task';
      var cType = childTypeFor(pType);
      var name = prompt('Enter ' + cType + ' name:');
      if (name) {{
        var newId = cType.substring(0,2) + Date.now();
        var p = lastNode.position();
        cy.add({{
          data: {{ id: newId, label: cType + ': ' + name }},
          classes: cType,
          position: {{ x: p.x + 60, y: p.y + 60 }}
        }});
        cy.add({{
          data: {{ source: lastNode.id(), target: newId, relation: 'hierarchy' }}
        }});
      }}
      hideMenu();
    }});

    // 3) Delete Node (visual-only)
    btnDel.addEventListener('click', function() {{
      if (!lastNode) return;
      if (selectedParent && selectedParent.id() === lastNode.id()) {{
        clearParentHighlight();
      }}
      cy.remove(lastNode);
      hideMenu();
    }});

    btnCancel.addEventListener('click', hideMenu);
  </script>
</body>
</html>
"""

st.subheader("Mindmap Canvas (press & hold a node for menu)")
st.components.v1.html(html, height=720, scrolling=True)

# ----------------------------
# Export the HTML you see
# ----------------------------
st.download_button("Export Interactive HTML", html, file_name="mindmap.html", mime="text/html")