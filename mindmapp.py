# streamlit run mindmap.py
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Mindmapp MVP", layout="wide")
st.title("Mindmapp MVP")

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
    {"ID": "S1",  "Level": "Story",    "Summary": "As a user, I can log in", "Epic Name": "", "Parent ID": "E1", "Blocks": ""},
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
# Sidebar: Add Issue
# ----------------------------
st.sidebar.header("Add Issue")

with st.sidebar.form("add_issue_form"):
    level = st.selectbox("Issue Type", options=ISSUE_TYPES, index=2)
    summary = st.text_input("Summary")
    epic_name = ""
    if level == "Epic":
        epic_name = st.text_input("Epic Name (for Jira)")
    parent_choices = [""] + st.session_state.df["ID"].astype(str).tolist()
    parent_id = st.selectbox("Parent ID", options=parent_choices)
    submit = st.form_submit_button("Add")

if submit and summary:
    new_id = id_prefix(level) + str(pd.Timestamp.now().value)
    new_row = {
        "ID": new_id,
        "Level": level,
        "Summary": summary,
        "Epic Name": epic_name if level == "Epic" else "",
        "Parent ID": parent_id,
        "Blocks": ""
    }
    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
    st.sidebar.success(f"Added {level}: {summary}")

# ----------------------------
# Sidebar: Edit Issue
# ----------------------------
st.sidebar.header("Edit Issue")

id_options = [""] + st.session_state.df["ID"].astype(str).tolist()
edit_id = st.sidebar.selectbox("Select ID", options=id_options)

if edit_id:
    row = st.session_state.df.loc[st.session_state.df["ID"].astype(str) == edit_id]
    if not row.empty:
        idx = row.index[0]
        new_summary = st.sidebar.text_area("Summary", value=row.iloc[0]["Summary"], height=80)
        if row.iloc[0]["Level"] == "Epic":
            new_epic = st.sidebar.text_input("Epic Name", value=row.iloc[0]["Epic Name"])
        else:
            new_epic = row.iloc[0]["Epic Name"]

        if st.sidebar.button("Save Changes"):
            st.session_state.df.at[idx, "Summary"] = new_summary
            st.session_state.df.at[idx, "Epic Name"] = new_epic
            st.sidebar.success("Updated")

# ----------------------------
# Issue Table
# ----------------------------
st.subheader("Issue Table (structure edits)")
edited = st.data_editor(
    st.session_state.df,
    num_rows="dynamic",
    use_container_width=True
)
st.session_state.df = edited.fillna("")

# ----------------------------
# Build Cytoscape elements
# ----------------------------
elements = []
valid_ids = set(st.session_state.df["ID"])

for _, r in st.session_state.df.iterrows():
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
# Render Cytoscape
# ----------------------------
CY_SRC = "https://unpkg.com/cytoscape/dist/cytoscape.min.js"

html = f"""
<!doctype html>
<html>
<head>
  <script src="{CY_SRC}"></script>
  <style>#cy {{ width:100%; height:450px; background:#fff; }}</style>
</head>
<body>
  <div id="cy"></div>
  <script>
    cytoscape({{
      container: document.getElementById('cy'),
      elements: {json.dumps(elements)},
      style: {json.dumps(stylesheet)},
      layout: {{ name: 'breadthfirst', directed: true, spacingFactor: 1.5 }}
    }});
  </script>
</body>
</html>
"""

st.subheader("Mindmap Canvas")
st.components.v1.html(html, height=500, scrolling=True)

# ----------------------------
# Export CSV
# ----------------------------
csv_bytes = st.session_state.df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("Download CSV", csv_bytes, "mindmap.csv", "text/csv")