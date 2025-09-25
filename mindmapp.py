# streamlit run mindmap_builder.py
import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
from io import BytesIO

st.set_page_config(page_title="Mindmap Builder → CSV/HTML/Jira", layout="wide")
st.title("Mindmap Builder (create, import, export)")

# ------------------------------------------------------------
# Session-state initialization
# ------------------------------------------------------------
DEFAULT_ROWS = [
    {"ID": "UC1", "Level": "Use-Case", "Summary": "User Login", "Parent ID": "", "Blocks": ""},
    {"ID": "E1",  "Level": "Epic",     "Summary": "Authentication", "Parent ID": "UC1", "Blocks": ""},
    {"ID": "S1",  "Level": "Story",    "Summary": "As a user I want to log in", "Parent ID": "E1", "Blocks": ""},
    {"ID": "T1",  "Level": "Task",     "Summary": "Build login form", "Parent ID": "S1", "Blocks": ""},
    {"ID": "T2",  "Level": "Task",     "Summary": "Connect backend",  "Parent ID": "S1", "Blocks": "T1"},
]

REQUIRED_COLS = ["ID", "Level", "Summary", "Parent ID", "Blocks"]
LEVEL_OPTIONS = ["Use-Case", "Epic", "Story", "Task", "Sub-task"]

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(DEFAULT_ROWS, columns=REQUIRED_COLS)

# ------------------------------------------------------------
# Sidebar: Import / Export
# ------------------------------------------------------------
st.sidebar.header("Import / Export")

uploaded = st.sidebar.file_uploader("Import CSV (ID, Level, Summary, Parent ID, Blocks)", type=["csv"])
if uploaded is not None:
    try:
        imp = pd.read_csv(uploaded, dtype=str).fillna("")
        missing = [c for c in REQUIRED_COLS if c not in imp.columns]
        if missing:
            st.sidebar.error(f"Missing columns: {missing}")
        else:
            # Normalize levels that don't match exactly
            imp["Level"] = imp["Level"].apply(lambda x: x if x in LEVEL_OPTIONS else x.strip().title())
            st.session_state.df = imp[REQUIRED_COLS].copy()
            st.sidebar.success("CSV imported.")
    except Exception as e:
        st.sidebar.error(f"Failed to import: {e}")

def export_current_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def build_jira_excel(df: pd.DataFrame) -> bytes:
    """
    Creates an Excel with two sheets:
      - Issues: Summary, Issue Type, Parent, Description, Priority, Assignee, Reporter, Labels, Fix Version/s
      - Issue Links: Source ID, Target ID, Link Type
    """
    # Map Level -> Issue Type
    level_to_type = {
        "Use-Case": "Use Case",
        "Epic": "Epic",
        "Story": "Story",
        "Task": "Task",
        "Sub-task": "Sub-task",
    }
    # Issues
    issues_rows = []
    for _, r in df.iterrows():
        issues_rows.append({
            "Summary": r["Summary"],
            "Issue Type": level_to_type.get(r["Level"], "Task"),
            "Parent": r["Parent ID"],          # rename to "Epic Link" in Jira if needed
            "Description": "",
            "Priority": "Medium",
            "Assignee": "unassigned",
            "Reporter": "system",
            "Labels": "",
            "Fix Version/s": ""
        })
    issues_df = pd.DataFrame(issues_rows)

    # Links (Blocks -> dependency)
    links_rows = []
    for _, r in df.iterrows():
        if r["Blocks"].strip():
            for tgt in [x.strip() for x in str(r["Blocks"]).split(";") if x.strip()]:
                links_rows.append({
                    "Source ID": r["ID"],
                    "Target ID": tgt,
                    "Link Type": "Blocks",
                })
    links_df = pd.DataFrame(links_rows) if links_rows else pd.DataFrame(columns=["Source ID", "Target ID", "Link Type"])

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        issues_df.to_excel(w, sheet_name="Issues", index=False)
        links_df.to_excel(w, sheet_name="Issue Links", index=False)
    return buf.getvalue()

# ------------------------------------------------------------
# Data editor (create / edit in-app)
# ------------------------------------------------------------
st.subheader("Edit Items")
st.caption("Add rows directly in the table. Columns: ID, Level, Summary, Parent ID, Blocks (semicolon-separated).")

edited_df = st.data_editor(
    st.session_state.df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Level": st.column_config.SelectboxColumn(options=LEVEL_OPTIONS),
        "Summary": st.column_config.TextColumn(),
        "Parent ID": st.column_config.TextColumn(help="ID of parent issue (empty for root)"),
        "Blocks": st.column_config.TextColumn(help="IDs this item blocks; separate with ';'"),
        "ID": st.column_config.TextColumn(help="Unique identifier you choose (e.g., UC1, E1, S1, T1)"),
    },
    key="editor",
)
# Persist edits
st.session_state.df = edited_df.fillna("")

# ------------------------------------------------------------
# Build graph with NetworkX + PyVis (no temp files)
# ------------------------------------------------------------
def build_graph(df: pd.DataFrame) -> Network:
    G = nx.DiGraph()
    # Add nodes
    for _, r in df.iterrows():
        label = f"{r['Level']}: {r['Summary']}"
        G.add_node(r["ID"], label=label, level=r["Level"], summary=r["Summary"])

    # Parent -> child edges
    for _, r in df.iterrows():
        pid = r["Parent ID"].strip()
        if pid:
            if pid in G and r["ID"] in G:
                G.add_edge(pid, r["ID"])

    # Dependency edges (red)
    for _, r in df.iterrows():
        if r["Blocks"].strip():
            for tgt in [x.strip() for x in str(r["Blocks"]).split(";") if x.strip()]:
                if r["ID"] in G and tgt in G:
                    G.add_edge(r["ID"], tgt, color="red")

    net = Network(height="700px", width="100%", directed=True, notebook=False)
    net.from_nx(G)
    # Physics/spacing
    net.repulsion(node_distance=220, spring_length=220, spring_strength=0.05, damping=0.85)
    return net

st.subheader("Mindmap Preview")
graph = build_graph(st.session_state.df)
html_str = graph.generate_html()  # no filesystem writes; safe on Streamlit Cloud
st.components.v1.html(html_str, height=720, scrolling=True)

# ------------------------------------------------------------
# Export buttons
# ------------------------------------------------------------
st.subheader("Export")
col1, col2, col3 = st.columns([1,1,1])

with col1:
    csv_bytes = export_current_csv(st.session_state.df)
    st.download_button("Download CSV (current table)", csv_bytes, file_name="mindmap.csv", mime="text/csv")

with col2:
    jira_xlsx = build_jira_excel(st.session_state.df)
    st.download_button(
        "Download Excel (Jira Issues + Links)",
        jira_xlsx,
        file_name="jira_issues_and_links.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with col3:
    # give the same HTML used in the preview
    st.download_button(
        "Download Interactive HTML",
        html_str,
        file_name="mindmap.html",
        mime="text/html",
    )

# ------------------------------------------------------------
# Lightweight validation / tips
# ------------------------------------------------------------
with st.expander("Validation Tips"):
    # Missing IDs
    missing_ids = st.session_state.df[st.session_state.df["ID"].str.strip() == ""]
    if not missing_ids.empty:
        st.warning("Some rows have empty ID values. Give each item a unique ID (e.g., UC1, E1, S1, T1).")

    # Parent ID that doesn't exist
    bad_parents = []
    ids = set(st.session_state.df["ID"].tolist())
    for _, r in st.session_state.df.iterrows():
        pid = r["Parent ID"].strip()
        if pid and pid not in ids:
            bad_parents.append((r["ID"], pid))
    if bad_parents:
        st.warning(f"Parent IDs not found: {bad_parents}")

    # Blocks pointing to missing IDs
    bad_blocks = []
    for _, r in st.session_state.df.iterrows():
        if r["Blocks"].strip():
            for tgt in [x.strip() for x in str(r["Blocks"]).split(";") if x.strip()]:
                if tgt not in ids:
                    bad_blocks.append((r["ID"], tgt))
    if bad_blocks:
        st.warning(f"Dependency targets not found: {bad_blocks}")

st.caption("Tip: For Jira import, you may need to rename the 'Parent' column to 'Epic Link' depending on your Jira configuration.")