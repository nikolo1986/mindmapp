# streamlit run mindmap.py
import json
import pandas as pd
import streamlit as st
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(page_title="Mindmap MVP (Palette + Table Sync)", layout="wide")
st.title("Mindmap MVP — Palette Create → Table Sync → Canvas")

# ----------------------------
# Helpers / Config
# ----------------------------
ISSUE_TYPES = ["Use-Case", "Epic", "Story", "Task", "Sub-task"]

COLOR_SHAPE = {
    "Use-Case": {"color": "#1f77b4", "shape": "ellipse",         "w": 80, "h": 80},
    "Epic":     {"color": "#2ca02c", "shape": "round-rectangle", "w": 70, "h": 70},
    "Story":    {"color": "#ff7f0e", "shape": "diamond",         "w": 60, "h": 60},
    "Task":     {"color": "#7f7f7f", "shape": "triangle",        "w": 50, "h": 50},
    "Sub-task": {"color": "#9467bd", "shape": "hexagon",         "w": 40, "h": 40},
}

def id_prefix(level: str) -> str:
    return {
        "Use-Case": "UC",
        "Epic": "EP",
        "Story": "ST",
        "Task": "TS",
        "Sub-task": "SB",
    }.get(level, "ND")

def infer_child_type(parent_level: str) -> str:
    if parent_level == "Use-Case": return "Epic"
    if parent_level == "Epic":     return "Story"
    if parent_level == "Story":    return "Task"
    if parent_level == "Task":     return "Sub-task"
    return "Task"

# ----------------------------
# Session State & Defaults
# ----------------------------
DEFAULT_ROWS = [
    {"ID": "UC1", "Level": "Use-Case", "Summary": "User Login",                     "Epic Name": "",            "Parent ID": "",   "Blocks": ""},
    {"ID": "E1",  "Level": "Epic",     "Summary": "Authentication Epic",            "Epic Name": "Auth Epic",   "Parent ID": "UC1","Blocks": ""},
    {"ID": "S1",  "Level": "Story",    "Summary": "As a user, I can log in",        "Epic Name": "",            "Parent ID": "E1", "Blocks": ""},
    {"ID": "T1",  "Level": "Task",     "Summary": "Build login form",               "Epic Name": "",            "Parent ID": "S1", "Blocks": ""},
    {"ID": "T2",  "Level": "Task",     "Summary": "Connect backend to auth",        "Epic Name": "",            "Parent ID": "S1", "Blocks": "T1"},
]

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(DEFAULT_ROWS)

if "selected_edit_id" not in st.session_state:
    st.session_state.selected_edit_id = ""

# ----------------------------
# Import / Export
# ----------------------------
st.sidebar.header("Import / Export")
up = st.sidebar.file_uploader("Upload CSV", type=["csv"])
if up:
    st.session_state.df = pd.read_csv(up).fillna("")
    st.sidebar.success("CSV imported")

# Ensure expected columns exist
for col in ["ID", "Level", "Summary", "Epic Name", "Parent ID", "Blocks"]:
    if col not in st.session_state.df.columns:
        st.session_state.df[col] = ""

# ----------------------------
# Sidebar: Clean Editors (Summary / Epic Name)
# ----------------------------
st.sidebar.header("Edit Selected Issue")
id_options = [""] + st.session_state.df["ID"].astype(str).tolist()
st.session_state.selected_edit_id = st.sidebar.selectbox("Select Issue ID", options=id_options, index=0)

if st.session_state.selected_edit_id:
    row = st.session_state.df.loc[st.session_state.df["ID"].astype(str) == st.session_state.selected_edit_id]
    if not row.empty:
        level = row.iloc[0]["Level"]
        # Summary editor
        new_summary = st.sidebar.text_area("Summary", value=str(row.iloc[0]["Summary"]), height=80)
        # Epic Name editor if Epic
        new_epic_name = ""
        if level == "Epic":
            new_epic_name = st.sidebar.text_input("Epic Name (Jira field)", value=str(row.iloc[0].get("Epic Name", "")))
        if st.sidebar.button("Save Changes"):
            idx = row.index[0]
            st.session_state.df.at[idx, "Summary"] = new_summary
            if level == "Epic":
                st.session_state.df.at[idx, "Epic Name"] = new_epic_name
            st.sidebar.success("Saved")

# ----------------------------
# Sidebar: Add Child (form fallback)
# ----------------------------
st.sidebar.header("Add Child (Form)")
with st.sidebar.form("add_child_form"):
    parent_id_form = st.selectbox("Parent ID", options=id_options, help="Pick a parent")
    child_level_form = st.selectbox("Child Level", options=ISSUE_TYPES, index=ISSUE_TYPES.index("Story"))
    child_summary_form = st.text_input("Child Summary")
    submit_child = st.form_submit_button("Add Child")
if submit_child and parent_id_form and child_summary_form:
    parent_row = st.session_state.df.loc[st.session_state.df["ID"].astype(str) == parent_id_form]
    if not parent_row.empty:
        new_id = id_prefix(child_level_form) + str(pd.Timestamp.now().value)
        new_row = {
            "ID": new_id,
            "Level": child_level_form,
            "Summary": child_summary_form,
            "Epic Name": child_summary_form if child_level_form == "Epic" else "",
            "Parent ID": parent_id_form,
            "Blocks": ""
        }
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
        st.sidebar.success(f"Added {child_level_form} under {parent_id_form}")

# ----------------------------
# Safety: sanitize DF before render
# ----------------------------
df = st.session_state.df.copy()
df = df.fillna("")
df["ID"] = df["ID"].astype(str).str.strip()
df = df[df["ID"] != ""]
df = df.drop_duplicates(subset=["ID"])
st.session_state.df = df

# ----------------------------
# Issue Table (structure edits; text edits use sidebar)
# ----------------------------
st.subheader("Issue Table (edit structure here; use sidebar to edit Summary/Epic Name)")
edited = st.data_editor(
    st.session_state.df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Epic Name": st.column_config.TextColumn(help="Only used for Epics. Blank okay."),
        "Blocks": st.column_config.TextColumn(help="Semicolon-separated IDs")
    }
)
st.session_state.df = edited.fillna("")

# ----------------------------
# Build Cytoscape elements (safe)
# ----------------------------
elements = []
valid_ids = set(st.session_state.df["ID"].astype(str))

for _, r in st.session_state.df.iterrows():
    node_id = str(r["ID"]).strip()
    if not node_id:
        continue
    label = f"{r['Level']}: {r['Summary']}"
    elements.append({
        "data": {"id": node_id, "label": label},
        "classes": str(r["Level"])
    })

    parent_id = str(r["Parent ID"]).strip()
    if parent_id and parent_id in valid_ids:
        elements.append({
            "data": {"source": parent_id, "target": node_id, "relation": "hierarchy"}
        })

    # Optional: dependency edges (dashed red)
    if "Blocks" in r and str(r["Blocks"]).strip():
        for tgt in str(r["Blocks"]).split(";"):
            t = tgt.strip()
            if t and t in valid_ids:
                elements.append({
                    "data": {"source": node_id, "target": t, "relation": "dependency"}
                })

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
]
for lvl, spec in COLOR_SHAPE.items():
    stylesheet.append({
        "selector": f".{lvl}",
        "style": {
            "background-color": spec["color"],
            "width": spec["w"], "height": spec["h"],
            "shape": spec["shape"]
        }
    })
stylesheet += [
    {"selector": "edge[relation = 'hierarchy']",
     "style": {"curve-style": "bezier", "target-arrow-shape": "triangle",
               "line-color": "#999", "target-arrow-color": "#999"}},
    {"selector": "edge[relation = 'dependency']",
     "style": {"curve-style": "bezier", "target-arrow-shape": "vee",
               "line-color": "red", "target-arrow-color": "red", "line-style": "dashed"}},
]

# ----------------------------
# Palette + Canvas HTML
#   - Palette buttons "arm" a type
#   - Tap background => create root of that type
#   - Tap node => create child of that type under node
#   - JS stores an event in localStorage; Python reads & applies
# ----------------------------
CY_SRC = "https://unpkg.com/cytoscape/dist/cytoscape.min.js"

palette_html = "".join(
    f'<button class="pill" data-type="{lvl}">{lvl}</button>'
    for lvl in ISSUE_TYPES
)

html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <script src="{CY_SRC}"></script>
  <style>
    body {{ margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; }}
    .bar {{
      display:flex; gap:8px; padding:10px; background:#f7f7f7; border-bottom:1px solid #e6e6e6;
      position: sticky; top: 0; z-index: 2;
    }}
    .pill {{
      border:1px solid #ccc; border-radius:999px; padding:6px 12px; background:#fff; cursor:pointer;
    }}
    .pill.active {{ border-color:#000; }}
    #cy {{ width:100%; height:700px; background:#fff; }}
    .hint {{ padding:8px 12px; background:#fafafa; border-bottom:1px solid #eee; color:#666; font-size:13px; }}
  </style>
</head>
<body>
  <div class="bar">{palette_html}</div>
  <div class="hint">Tip: Click a type above to arm it. Tap the canvas to create a root, or tap a node to create a child.</div>
  <div id="cy"></div>

  <script>
    var cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: {json.dumps(elements)},
      style: {json.dumps(stylesheet)},
      layout: {{ name: 'breadthfirst', directed: true, spacingFactor: 1.5 }},
      wheelSensitivity: 0.2
    }});

    var armedType = null;
    document.querySelectorAll('.pill').forEach(function(btn){{
      btn.addEventListener('click', function(){{
        document.querySelectorAll('.pill').forEach(b=>b.classList.remove('active'));
        if(armedType === btn.dataset.type) {{
          armedType = null; // unarm
        }} else {{
          armedType = btn.dataset.type;
          btn.classList.add('active');
        }}
      }});
    }});

    function promptName(level){{
      return window.prompt('Enter ' + level + ' name:');
    }}

    function recordEvent(obj){{
      // store as one-shot event for Streamlit to read
      try {{
        window.localStorage.setItem('mm_event', JSON.stringify(obj));
      }} catch(e) {{
        console.error('localStorage set failed', e);
      }}
    }}

    // Tap background => create root when armed
    cy.on('tap', function(evt){{
      if(!armedType) return;
      if (evt.target === cy) {{
        var name = promptName(armedType);
        if(name) {{
          recordEvent({{ kind:'create', level: armedType, summary: name, parentId: '' }});
        }}
      }}
    }});

    // Tap a node => create child when armed
    cy.on('tap', 'node', function(evt){{
      if(!armedType) return;
      var parentId = evt.target.id();
      var name = promptName(armedType);
      if(name) {{
        recordEvent({{ kind:'create', level: armedType, summary: name, parentId: parentId }});
      }}
    }});
  </script>
</body>
</html>
"""

st.subheader("Palette + Canvas")
st.components.v1.html(html, height=780, scrolling=True)

# ----------------------------
# Read palette/canvas events from localStorage
#   We poll once per run; if an event is present, consume and apply
# ----------------------------
raw_evt = streamlit_js_eval(js_expressions="window.localStorage.getItem('mm_event')", key="evt_read")
if raw_evt:
    try:
        evt = json.loads(raw_evt)
    except Exception:
        evt = None
    # Clear it so we don't reapply next run
    _ = streamlit_js_eval(js_expressions="window.localStorage.removeItem('mm_event')", key="evt_clear")

    if evt and evt.get("kind") == "create":
        level = evt.get("level", "Task")
        summary = (evt.get("summary") or "").strip()
        parent_id = (evt.get("parentId") or "").strip()

        if summary:
            # Validate parent (if provided)
            parent_ok = (parent_id == "") or (parent_id in st.session_state.df["ID"].astype(str).values)
            if parent_ok:
                new_id = id_prefix(level) + str(pd.Timestamp.now().value)
                new_row = {
                    "ID": new_id,
                    "Level": level,
                    "Summary": summary,
                    "Epic Name": summary if level == "Epic" else "",
                    "Parent ID": parent_id,
                    "Blocks": ""
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                st.success(f"Added {level}: {summary}" + (f" under {parent_id}" if parent_id else ""))
            else:
                st.warning(f"Parent '{parent_id}' was not found; node created without a parent.")
                new_id = id_prefix(level) + str(pd.Timestamp.now().value)
                new_row = {
                    "ID": new_id,
                    "Level": level,
                    "Summary": summary,
                    "Epic Name": summary if level == "Epic" else "",
                    "Parent ID": "",
                    "Blocks": ""
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)

# ----------------------------
# Export CSV (includes Epic Name)
# ----------------------------
csv_bytes = st.session_state.df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("Download CSV", csv_bytes, "mindmap.csv", "text/csv")