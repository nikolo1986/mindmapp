import os
import streamlit.components.v1 as components

# Point to built frontend
_component_func = components.declare_component(
    "mindmap",
    path=os.path.join(os.path.dirname(__file__), "../frontend/build")
)

def mindmap(elements, key=None):
    """
    Renders the Cytoscape mindmap component.
    elements: list of Cytoscape-style node/edge dicts
    Returns event dict (e.g., {"kind": "create", "level": "Epic", "summary": "foo", "parentId": "UC1"})
    """
    return _component_func(elements=elements, key=key, default=None)