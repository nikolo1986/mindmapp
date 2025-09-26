# streamlit run mindmap.py
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Mindmap MVP (Textarea Bridge)", layout="wide")
st.title("Mindmap MVP — Canvas Create → DataFrame Sync")

# ----------------------------
# Helpers
# ----------------------------
ISSUE_TYPES = ["Use-Case", "Epic", "Story", "Task", "Sub-task"]

def id_prefix(level: str) -> str:
    return {
        "Use-Case": "UC",
        "Epic": "EP",
        "Story": "ST",
        "Task": "TS",
        "Sub-task": "SB",
    }.get(level, "ND")

COLOR_SHAPE = {
    "Use-Case": {"color": "#1f77b4", "shape": "ellipse",         "w": 80, "h": 80},
    "Epic":     {"color": "#2ca02c", "shape": "round-rectangle", "w": 70, "h": 70},
    "Story":    {"color": "#ff7f0e", "shape": "diamond",         "w": 60, "h": 60},
    "Task":     {"color": "#7f7f7f", "shape": "triangle",        "w": 50, "h": 50},
    "Sub-task": {"color": "#9467bd", "shape": "hexagon",         "w": 40, "h": 40},
}

# ----------------------------
# Defaults
# ----------------------------
DEFAULT_ROWS = [
    {"ID": "UC1", "Level": "Use-Case", "Summary": "User Login", "Epic Name": "", "Parent ID": "", "Blocks": ""},
    {"ID": "E1",  "Level": "Epic",     "Summary": "Authentication Epic", "Epic Name": "Auth Epic", "Parent ID": "UC1", "Blocks": ""},
]

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(DEFAULT_ROWS)

# ----------------------------
# Clean DF
# ----------------------------
df = st.session_state.df.copy().fillna("")
df["ID"] = df["ID"].astype(str).str.strip()
df = df[df["ID"] != ""].drop_duplicates(subset=["ID"])
st.session_state.df = df

# ----------------------------
# Build Cytoscape elements
# ----------------------------
elements = []
valid_ids = set(df["ID"])

for _, r in df.iterrows():
    node_id = str(r["ID"])
    elements.append({
        "data": {"id": node_id, "label": f"{r['Level']}: {r['Summary']}"},
        "classes": r["Level"],
    })
    parent_id = str(r["Parent ID"]).strip()
    if parent_id and parent_id in valid_ids:
        elements.append({"data": {"source": parent_id, "target": node_id, "relation": "hierarchy"}})

stylesheet = [
    {"selector": "node", "style": {"label": "data(label)", "color": "white",
                                   "text-outline-color": "#000", "text-outline-width": 2,
                                   "text-valign": "center", "text-halign": "center"}},
]
for lvl, spec in COLOR_SHAPE.items():
    stylesheet.append({
        "selector": f".{lvl}",
        "style": {"background-color": spec["color"], "shape": spec["shape"],
                  "width": spec["w"], "height": spec["h"]}
    })
stylesheet.append({
    "selector": "edge[relation = 'hierarchy']",
    "style": {"curve-style": "bezier", "target-arrow-shape": "triangle",
              "line-color": "#999", "target-arrow-color": "#999"}
})

# ----------------------------
# Cytoscape HTML with hidden textarea bridge
# ----------------------------
CY_SRC = "https://unpkg.com/cytoscape/dist/cytoscape.min.js"

html = f"""
<!doctype html>
<html>
<head>
  <script src="{CY_SRC}"></script>
  <style>
    #cy {{ width: 100%; height: 450px; background: #fff; }}
    .pill {{ margin: 4px; padding: 4px 8px; border: 1px solid #ccc; border-radius: 6px; cursor:pointer; }}
    .pill.active {{ border: 2px solid #000; }}
  </style>
</head>
<body>
  <div>
    {"".join(f'<button class="pill" data-type="{t}">{t}</button>' for t in ISSUE_TYPES)}
  </div>
  <textarea id="bridge" style="display:none;"></textarea>
  <div id="cy"></div>
  <script>
    var cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: {json.dumps(elements)},
      style: {json.dumps(stylesheet)},
      layout: {{ name: 'breadthfirst', directed: true, spacingFactor: 1.5 }}
    }});

    var armedType = null;
    document.querySelectorAll('.pill').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.pill').forEach(b=>b.classList.remove('active'));
        if(armedType === btn.dataset.type) {{
          armedType = null;
        }} else {{
          armedType = btn.dataset.type;
          btn.classList.add('active');
        }}
      }});
    }});

    function recordEvent(obj){{
      const el = document.getElementById("bridge");
      el.value = JSON.stringify(obj);
      el.dispatchEvent(new Event("input"));
    }}

    function promptName(level){{
      return window.prompt("Enter " + level + " name:");
    }}

    cy.on('tap', function(evt){{
      if(!armedType) return;
      if(evt.target === cy) {{
        var name = promptName(armedType);
        if(name) {{
          recordEvent({{kind:"create", level: armedType, summary: name, parentId:""}});
        }}
      }}
    }});

    cy.on('tap', 'node', function(evt){{
      if(!armedType) return;
      var pid = evt.target.id();
      var name = promptName(armedType);
      if(name) {{
        recordEvent({{kind:"create", level: armedType, summary: name, parentId: pid}});
      }}
    }});
  </script>
</body>
</html>
"""

# ----------------------------
# Render Canvas + Read Events
# ----------------------------
st.subheader("Mindmap Canvas (450px)")
event_json = st.text_area("bridge", key="bridge", label_visibility="collapsed")

st.components.v1.html(html, height=520, scrolling=True)

# ----------------------------
# Process Events
# ----------------------------
if event_json:
    try:
        evt = json.loads(event_json)
    except Exception:
        evt = None
    if evt and evt.get("kind") == "create":
        new_id = id_prefix(evt["level"]) + str(pd.Timestamp.now().value)
        new_row = {
            "ID": new_id,
            "Level": evt["level"],
            "Summary": evt["summary"],
            "Epic Name": evt["summary"] if evt["level"] == "Epic" else "",
            "Parent ID": evt["parentId"],
            "Blocks": ""
        }
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
        st.success(f"Added {evt['level']}: {evt['summary']}")
        st.rerun()

# ----------------------------
# Table + Export
# ----------------------------
st.subheader("Issue Table")
st.dataframe(st.session_state.df, use_container_width=True)

csv_bytes = st.session_state.df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("Download CSV", csv_bytes, "mindmap.csv", "text/csv")