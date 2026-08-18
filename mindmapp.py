import io
import json
import pandas as pd
import streamlit as st

from jira_client import JiraClient, JiraError

st.set_page_config(page_title="Mindmapp MVP", layout="wide")
st.title("Mindmapp MVP")

if "connection_mode" not in st.session_state:
    st.session_state.connection_mode = "CSV / Excel only (no Jira account needed)"

st.session_state.connection_mode = st.sidebar.radio(
    "Connection Mode",
    ["CSV / Excel only (no Jira account needed)", "Live Jira connection"],
    index=["CSV / Excel only (no Jira account needed)", "Live Jira connection"].index(st.session_state.connection_mode),
)
JIRA_MODE = st.session_state.connection_mode == "Live Jira connection"

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

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure consistent formatting of dataframe."""
    df = df.copy().fillna("")
    if "Jira Key" not in df.columns:
        df["Jira Key"] = ""
    df["ID"] = df["ID"].astype(str).str.strip()
    df["Parent ID"] = df["Parent ID"].astype(str).str.strip()
    df["Blocks"] = df["Blocks"].astype(str).str.strip()
    df["Jira Key"] = df["Jira Key"].astype(str).str.strip()
    df = df[df["ID"] != ""].drop_duplicates(subset=["ID"])
    return df

# ----------------------------
# Defaults
# ----------------------------
DEFAULT_ROWS = [
    {"ID": "UC1", "Level": "Use-Case", "Summary": "User Login", "Epic Name": "", "Parent ID": "", "Blocks": "", "Jira Key": ""},
    {"ID": "E1",  "Level": "Epic",     "Summary": "Authentication Epic", "Epic Name": "Auth Epic", "Parent ID": "UC1", "Blocks": "", "Jira Key": ""},
    {"ID": "S1",  "Level": "Story",    "Summary": "As a user, I can log in", "Epic Name": "", "Parent ID": "E1", "Blocks": "", "Jira Key": ""},
]

# ----------------------------
# Jira sync helpers
# ----------------------------
def jira_client_from_config(cfg):
    if not cfg or not cfg.get("base_url") or not cfg.get("api_token"):
        return None
    return JiraClient(
        base_url=cfg["base_url"],
        api_token=cfg["api_token"],
        email=cfg.get("email"),
        auth_mode=cfg["auth_mode"],
        api_version=cfg.get("api_version", "3"),
    )

def pull_from_jira(client, jql, type_map, schema):
    reverse_type_map = {v: k for k, v in type_map.items()}
    issues = client.search_issues(jql)
    rows = []
    for issue in issues:
        key = issue["key"]
        fields = issue["fields"]
        jira_type_name = fields["issuetype"]["name"]
        level = reverse_type_map.get(jira_type_name, jira_type_name)

        epic_name = ""
        if schema.get("epic_name_field"):
            epic_name = fields.get(schema["epic_name_field"]) or ""

        parent_id = ""
        if fields.get("parent"):
            parent_id = fields["parent"]["key"]
        elif schema.get("epic_link_field") and fields.get(schema["epic_link_field"]):
            parent_id = fields[schema["epic_link_field"]]

        blocks = []
        for link in fields.get("issuelinks", []) or []:
            if link.get("type", {}).get("name", "").lower() != "blocks":
                continue
            outward = link.get("outwardIssue")
            if outward:
                blocks.append(outward["key"])

        rows.append({
            "ID": key,
            "Level": level,
            "Summary": fields.get("summary", "") or "",
            "Epic Name": epic_name,
            "Parent ID": parent_id,
            "Blocks": ",".join(blocks),
            "Jira Key": key,
        })
    return pd.DataFrame(rows, columns=["ID", "Level", "Summary", "Epic Name", "Parent ID", "Blocks", "Jira Key"])

def push_to_jira(client, project_key, df, type_map, schema):
    df = df.copy()
    id_map = {r["ID"]: r["Jira Key"] for _, r in df.iterrows() if r["Jira Key"]}

    remaining = list(df[df["Jira Key"] == ""].index)
    order = []
    resolved = set(id_map.keys())
    while remaining:
        progressed = False
        for idx in list(remaining):
            parent = df.at[idx, "Parent ID"]
            if not parent or parent in resolved:
                order.append(idx)
                resolved.add(df.at[idx, "ID"])
                remaining.remove(idx)
                progressed = True
        if not progressed:
            order.extend(remaining)
            remaining = []

    created, updated, errors = 0, 0, []
    for idx in order:
        row = df.loc[idx]
        level = row["Level"]
        jira_type = type_map.get(level, level)
        parent_key = id_map.get(row["Parent ID"], row["Parent ID"] or None)

        extra_fields = {}
        if level == "Epic" and schema.get("epic_name_field") and row["Epic Name"]:
            extra_fields[schema["epic_name_field"]] = row["Epic Name"]
        if parent_key:
            if level == "Sub-task":
                extra_fields["parent"] = {"key": parent_key}
            elif schema.get("epic_link_field"):
                extra_fields[schema["epic_link_field"]] = parent_key
            else:
                extra_fields["parent"] = {"key": parent_key}

        try:
            new_key = client.create_issue(project_key, jira_type, row["Summary"], extra_fields)
            id_map[row["ID"]] = new_key
            df.at[idx, "ID"] = new_key
            df.at[idx, "Jira Key"] = new_key
            created += 1
        except JiraError as e:
            errors.append(f"{row['ID']} ({row['Summary']}): {e}")

    df["Parent ID"] = df["Parent ID"].map(lambda x: id_map.get(x, x))
    df["Blocks"] = df["Blocks"].apply(
        lambda s: ",".join(id_map.get(b.strip(), b.strip()) for b in str(s).split(",") if b.strip())
    )

    already_synced_idx = [i for i in df.index if i not in order and df.at[i, "Jira Key"]]
    for idx in already_synced_idx:
        row = df.loc[idx]
        try:
            client.update_issue_summary(row["Jira Key"], row["Summary"])
            updated += 1
        except JiraError as e:
            errors.append(f"{row['Jira Key']} update: {e}")

    if schema.get("blocks_link_type"):
        for _, row in df.iterrows():
            if not row["Jira Key"]:
                continue
            for blocked in [b.strip() for b in str(row["Blocks"]).split(",") if b.strip()]:
                try:
                    client.create_link(row["Jira Key"], blocked, schema["blocks_link_type"])
                except JiraError:
                    pass

    return normalize_df(df), created, updated, errors

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(DEFAULT_ROWS)

st.session_state.df = normalize_df(st.session_state.df)

# ----------------------------
# Sidebar Controls
# ----------------------------
st.sidebar.header("Controls")

col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("Reset to Defaults"):
        st.session_state.df = pd.DataFrame(DEFAULT_ROWS)
        st.rerun()

with col2:
    if st.button("Clear All Issues", type="primary", key="clear_all"):
        st.session_state.show_clear_confirm = True

# Confirmation for Clear All
if st.session_state.get("show_clear_confirm", False):
    st.sidebar.error("⚠️ This will delete ALL issues!")
    if st.sidebar.button("Yes, Clear Everything", key="confirm_clear"):
        st.session_state.df = pd.DataFrame(columns=["ID","Level","Summary","Epic Name","Parent ID","Blocks","Jira Key"])
        st.session_state.show_clear_confirm = False
        st.rerun()
    if st.sidebar.button("Cancel", key="cancel_clear"):
        st.session_state.show_clear_confirm = False
        st.rerun()

# ----------------------------
# Jira Connection
# ----------------------------
if "jira_config" not in st.session_state:
    st.session_state.jira_config = {}
if "jira_type_map" not in st.session_state:
    st.session_state.jira_type_map = {lvl: lvl for lvl in ISSUE_TYPES}
if "jira_schema" not in st.session_state:
    st.session_state.jira_schema = {}

if JIRA_MODE:
    st.sidebar.header("Jira Connection")

    with st.sidebar.expander("Site & Credentials", expanded=not st.session_state.jira_config.get("base_url")):
        base_url = st.text_input("Jira Base URL", value=st.session_state.jira_config.get("base_url", ""),
                                  placeholder="https://yourcompany.atlassian.net")
        auth_label = st.selectbox("Auth Type", ["Jira Cloud (email + API token)", "Jira Server / Data Center (PAT)"])
        auth_mode = "cloud" if auth_label.startswith("Jira Cloud") else "server"

        email = st.session_state.jira_config.get("email", "")
        if auth_mode == "cloud":
            email = st.text_input("Email", value=email)
            token_label = "API Token"
        else:
            token_label = "Personal Access Token"
        api_token = st.text_input(token_label, value=st.session_state.jira_config.get("api_token", ""), type="password")

        project_key = st.text_input("Project Key", value=st.session_state.jira_config.get("project_key", ""),
                                     placeholder="e.g. MMP")

        if st.button("Save & Test Connection"):
            cfg = {
                "base_url": base_url.strip(),
                "auth_mode": auth_mode,
                "email": email.strip(),
                "api_token": api_token,
                "project_key": project_key.strip(),
            }
            st.session_state.jira_config = cfg
            try:
                client = jira_client_from_config(cfg)
                if client is None:
                    st.error("Base URL and API token/PAT are required.")
                else:
                    me = client.test_connection()
                    st.session_state.jira_schema = client.discover_schema()
                    st.success(f"Connected as {me.get('displayName', me.get('emailAddress', 'unknown user'))}")
            except JiraError as e:
                st.error(str(e))

    with st.sidebar.expander("Issue Type Mapping"):
        st.caption("Map each Mindmapp level to the matching Jira issue type name in your project.")
        for lvl in ISSUE_TYPES:
            st.session_state.jira_type_map[lvl] = st.text_input(
                lvl, value=st.session_state.jira_type_map.get(lvl, lvl), key=f"type_map_{lvl}"
            )

    st.sidebar.subheader("Jira Sync")
    jql_default = f"project = {st.session_state.jira_config.get('project_key', '')} ORDER BY created ASC"
    pull_jql = st.sidebar.text_area("Pull JQL", value=jql_default, height=70)

    pcol1, pcol2 = st.sidebar.columns(2)
    with pcol1:
        if st.button("Pull from Jira"):
            client = jira_client_from_config(st.session_state.jira_config)
            if client is None:
                st.sidebar.error("Configure and test the Jira connection first.")
            else:
                try:
                    pulled = pull_from_jira(client, pull_jql, st.session_state.jira_type_map, st.session_state.jira_schema)
                    st.session_state.df = normalize_df(pulled)
                    st.sidebar.success(f"Pulled {len(pulled)} issues from Jira")
                    st.rerun()
                except JiraError as e:
                    st.sidebar.error(str(e))

    with pcol2:
        if st.button("Push to Jira", type="primary"):
            client = jira_client_from_config(st.session_state.jira_config)
            project_key = st.session_state.jira_config.get("project_key")
            if client is None or not project_key:
                st.sidebar.error("Configure and test the Jira connection first.")
            else:
                new_df, created, updated, errors = push_to_jira(
                    client, project_key, st.session_state.df,
                    st.session_state.jira_type_map, st.session_state.jira_schema
                )
                st.session_state.df = new_df
                if created or updated:
                    st.sidebar.success(f"Created {created}, updated {updated} issue(s) in Jira")
                for err in errors:
                    st.sidebar.error(err)
                st.rerun()

# ----------------------------
# Add Issue
# ----------------------------
st.sidebar.subheader("Add Issue")

level = st.sidebar.selectbox("Issue Type", options=ISSUE_TYPES, index=2, key="add_level")

with st.sidebar.form("add_issue_form", clear_on_submit=True):
    summary = st.text_input("Summary", key="add_summary")

    epic_name = ""
    if level == "Epic":
        epic_name = st.text_input("Epic Name (for Jira)", key="epic_name_input")
    else:
        if "epic_name_input" in st.session_state:
            del st.session_state["epic_name_input"]

    parent_choices = [""] + st.session_state.df["ID"].astype(str).tolist()
    parent_id = st.selectbox("Parent ID", options=parent_choices, key="add_parent")

    blocks = st.text_input("Blocks (comma-separated IDs)", key="add_blocks")

    submit_add = st.form_submit_button("Add")

if submit_add and summary.strip():
    new_id = id_prefix(level) + str(pd.Timestamp.utcnow().value)
    new_row = {
        "ID": new_id,
        "Level": level,
        "Summary": summary.strip(),
        "Epic Name": epic_name.strip() if level == "Epic" else "",
        "Parent ID": parent_id,
        "Blocks": blocks.strip(),
        "Jira Key": ""
    }
    st.session_state.df = normalize_df(
        pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
    )
    st.sidebar.success(f"Added {level}: {summary.strip()}")
    st.rerun()

# ----------------------------
# Edit Issue
# ----------------------------
st.sidebar.subheader("Edit Issue")
id_options = [""] + st.session_state.df["ID"].astype(str).tolist()
edit_id = st.sidebar.selectbox("Select ID to Edit", options=id_options)

if edit_id:
    row = st.session_state.df.loc[st.session_state.df["ID"] == edit_id]
    if not row.empty:
        idx = row.index[0]
        new_summary = st.sidebar.text_area("Summary", value=row.iloc[0]["Summary"], height=80)
        if row.iloc[0]["Level"] == "Epic":
            new_epic = st.sidebar.text_input("Epic Name", value=row.iloc[0]["Epic Name"], key="edit_epic")
        else:
            new_epic = row.iloc[0]["Epic Name"]

        new_blocks = st.sidebar.text_input("Blocks (comma-separated IDs)", value=row.iloc[0]["Blocks"], key="edit_blocks")

        if st.sidebar.button("Save Changes"):
            st.session_state.df.at[idx, "Summary"] = new_summary
            st.session_state.df.at[idx, "Epic Name"] = new_epic
            st.session_state.df.at[idx, "Blocks"] = new_blocks
            st.sidebar.success("Updated")
            st.rerun()

# ----------------------------
# Delete Issue (with cascade option + confirm)
# ----------------------------
st.sidebar.subheader("Delete Issue")
delete_id = st.sidebar.selectbox(
    "Select ID to Delete",
    options=[""] + st.session_state.df["ID"].astype(str).tolist()
)

delete_mode = st.sidebar.radio(
    "Delete Mode",
    ["Just this issue (children remain)", "Cascade (delete children too)"],
    index=0
)

if delete_id and st.sidebar.button("Delete Selected Issue", type="primary"):
    if delete_mode == "Cascade (delete children too)":
        st.session_state.pending_delete = {"id": delete_id, "mode": "cascade"}
    else:
        st.session_state.pending_delete = {"id": delete_id, "mode": "single"}

# Handle confirm delete
if st.session_state.get("pending_delete"):
    mode = st.session_state.pending_delete["mode"]
    did = st.session_state.pending_delete["id"]

    st.sidebar.error(
        f"⚠️ Confirm delete: {did} ({'and all descendants' if mode=='cascade' else 'only'})"
    )
    if st.sidebar.button("Yes, Delete", key="confirm_delete"):
        df = st.session_state.df.copy()
        if mode == "cascade":
            to_delete = set([did])
            found = True
            while found:
                found = False
                children = df[df["Parent ID"].isin(to_delete)]["ID"].tolist()
                new = [c for c in children if c not in to_delete]
                if new:
                    to_delete.update(new)
                    found = True
            df = df[~df["ID"].isin(to_delete)].reset_index(drop=True)
            st.sidebar.success(f"Deleted {len(to_delete)} issues (cascade)")
        else:
            df = df[df["ID"] != did].reset_index(drop=True)
            df.loc[df["Parent ID"] == did, "Parent ID"] = ""
            st.sidebar.success(f"Deleted issue {did}")

        st.session_state.df = normalize_df(df)
        st.session_state.pending_delete = None
        st.rerun()

    if st.sidebar.button("Cancel Delete", key="cancel_delete"):
        st.session_state.pending_delete = None
        st.rerun()

# ----------------------------
# Issue Table
# ----------------------------
st.subheader("Issue Table (editable)")
edited = st.data_editor(
    st.session_state.df,
    num_rows="dynamic",
    use_container_width=True,
    key="editor",
    column_config={
        "Level": st.column_config.SelectboxColumn("Level", options=ISSUE_TYPES),
        "Parent ID": st.column_config.SelectboxColumn("Parent ID", options=[""] + st.session_state.df["ID"].astype(str).tolist()),
        "Jira Key": st.column_config.TextColumn("Jira Key", disabled=True, help="Set automatically after a Push to Jira"),
    }
)
st.session_state.df = normalize_df(edited)

# ----------------------------
# Build Cytoscape Elements
# ----------------------------
elements = []
valid_ids = set(st.session_state.df["ID"])

for _, r in st.session_state.df.iterrows():
    node_id = r["ID"]
    label_prefix = r["Jira Key"] if r["Jira Key"] else r["Level"]
    elements.append({
        "data": {"id": node_id, "label": f"{label_prefix}: {r['Summary']}"},
        "classes": r["Level"],
    })

    # Parent/child
    parent_id = r["Parent ID"].strip()
    if parent_id and parent_id in valid_ids:
        elements.append({"data": {"source": parent_id, "target": node_id, "relation": "hierarchy"}})

    # Blocks edges
    blocks = str(r["Blocks"]).strip()
    if blocks:
        for blocked in [b.strip() for b in blocks.split(",") if b.strip()]:
            if blocked in valid_ids:
                elements.append({"data": {"source": node_id, "target": blocked, "relation": "blocks"}})

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
stylesheet.append({
    "selector": "edge[relation = 'blocks']",
    "style": {
        "line-style": "dashed",
        "line-color": "red",
        "curve-style": "bezier",            # ensures arrows display properly
        "target-arrow-shape": "triangle",
        "target-arrow-color": "red",
        "arrow-scale": 1.5,
        "label": "blocks",
        "font-size": 10,
        "color": "red",
        "text-rotation": "autorotate",
        "text-background-color": "white",
        "text-background-opacity": 1,
        "text-background-padding": "2px"
    }
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
# Legend
# ----------------------------
st.markdown("### Legend")
legend_md = """
- **Shapes / Colors**
  - 🟦 Ellipse (blue) = Use-Case  
  - 🟩 Round-rectangle (green) = Epic  
  - 🟧 Diamond (orange) = Story  
  - ⚪ Triangle (gray) = Task  
  - 🟪 Hexagon (purple) = Sub-task  

- **Edges**
  - ➡️ **Solid gray arrow** = hierarchy (Parent → Child)  
  - ➡️ **Dashed red arrow labeled 'blocks'** = blocking relationship (Issue → Blocked Issue)  
"""
st.markdown(legend_md)

# ----------------------------
# Export/Import CSV & Excel
# ----------------------------
st.sidebar.subheader("Export / Import")

csv_bytes = st.session_state.df.to_csv(index=False).encode("utf-8")
xlsx_buf = io.BytesIO()
st.session_state.df.to_excel(xlsx_buf, index=False, sheet_name="Issues")

ecol1, ecol2 = st.sidebar.columns(2)
with ecol1:
    st.download_button("Download CSV", csv_bytes, "mindmap.csv", "text/csv")
with ecol2:
    st.download_button(
        "Download Excel", xlsx_buf.getvalue(), "mindmap.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

file = st.sidebar.file_uploader("Upload CSV or Excel to replace table", type=["csv", "xlsx"])
if file is not None:
    if file.name.lower().endswith(".xlsx"):
        uploaded = pd.read_excel(file, dtype=str)
    else:
        uploaded = pd.read_csv(file, dtype=str)
    st.session_state.df = normalize_df(uploaded)
    st.sidebar.success(f"Table replaced from {file.name}.")
    st.rerun()