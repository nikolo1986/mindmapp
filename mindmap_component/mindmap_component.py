import os
import streamlit.components.v1 as components

_component_func = components.declare_component(
    "mindmap_canvas",
    path=os.path.join(os.path.dirname(__file__), "frontend"),
)

def mindmap_canvas(elements, stylesheet, issue_types, color_shape, positions=None, height=520, key=None):
    """
    Interactive Cytoscape canvas. Returns the latest interaction event as a
    dict (or None if nothing has happened yet), one of:
      {"kind": "select", "id": ..., "event_id": ...}
      {"kind": "create", "level": ..., "x": ..., "y": ..., "event_id": ...}
      {"kind": "reparent", "sourceId": ..., "targetId": ..., "event_id": ...}
      {"kind": "relate", "sourceId": ..., "targetId": ..., "event_id": ...}
      {"kind": "layout", "positions": {id: {"x":..., "y":...}}, "event_id": ...}
    """
    return _component_func(
        elements=elements,
        stylesheet=stylesheet,
        issue_types=issue_types,
        color_shape=color_shape,
        positions=positions or {},
        height=height,
        key=key,
        default=None,
    )
