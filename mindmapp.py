import pandas as pd
import streamlit as st
from mindmap_component import mindmap

st.set_page_config(layout="wide")
st.title("Interactive Mindmap MVP")

# ---------------------------
# Initialize DataFrame
# ---------------------------
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame([
        {"ID": "UC1", "Level": "Use-Case", "Summary": "User Login", "Parent ID": ""}
    ])

# ---------------------------
# Build Cytoscape elements
# ---------------------------
elements = []
for _, r in st.session_state.df.iterrows():
    elements.append({"data": {"id": r["ID"], "label": f"{r['Level']}: {r['Summary']}"}, "classes": r["Level"]})
    if r["Parent ID"]:
        elements.append({"data": {"source": r["Parent ID"], "target": r["ID"], "relation": "hierarchy"}})

# ---------------------------
# Render Mindmap Component
# ---------------------------
event = mindmap(elements, key="map")

# ---------------------------
# Handle Events from Component
# ---------------------------
if event and event.get("kind") == "create":
    new_id = event["level"][:2].upper() + str(pd.Timestamp.now().value)
    new_row = {
        "ID": new_id,
        "Level": event["level"],
        "Summary": event["summary"],
        "Parent ID": event["parentId"]
    }
    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
    st.success(f"Added {event['level']}: {event['summary']}")

# ---------------------------
# Table + Export
# ---------------------------
st.subheader("Issue Table")
st.dataframe(st.session_state.df, use_container_width=True)

csv_bytes = st.session_state.df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button("Download CSV", csv_bytes, "mindmap.csv", "text/csv")