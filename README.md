# mindmapp

Basic Mindmap app for building Jira-style issue hierarchies (Use-Case → Epic → Story → Task → Sub-task), with CSV/Excel export and optional direct Jira sync.

## Connection Mode

At the top of the sidebar, choose:

- **CSV / Excel only** (default) — no Jira account needed. Build the hierarchy in the app and download it as `.csv` or `.xlsx`, or upload a file to load one back in.
- **Live Jira connection** — sync directly with a Jira site you configure.

## Jira sync

Switch to **Live Jira connection** mode to reveal the **Jira Connection** section in the sidebar:

1. Enter your Jira base URL (e.g. `https://yourcompany.atlassian.net`), choose Cloud (email + API token) or Server/Data Center (username + password) auth, your credentials, and a project key, then click **Save & Test Connection**. The URL and credentials are whatever you type in — nothing is hardcoded to a particular Jira site.
2. Adjust **Issue Type Mapping** if your project's issue type names differ from `Use-Case` / `Epic` / `Story` / `Task` / `Sub-task`.
3. **Pull from Jira** loads issues matching the JQL query into the table (tracked by their Jira key).
4. **Push to Jira** creates any local issues that don't yet have a Jira key, updates summaries on ones that do, and (re)creates "blocks" and "relates to" issue links.

Each issue has a **Relates To** field (comma-separated IDs) alongside **Blocks**, synced via Jira's built-in "Relates" link type — e.g. use it to mark that a Task satisfies a Story in the same Epic.

Credentials are kept only in the browser session's memory, not written to disk.

## Interactive canvas

The mindmap canvas (`mindmap_component/`) is a real drag-and-drop Streamlit component, not just a static diagram:

- Drag an issue-type chip from the palette on the left onto empty canvas to create a new issue there.
- Drag one node onto another to set the dragged node's Parent ID.
- Hold **Shift** while dragging one node onto another to add a "relates to" link instead of reparenting.
- Click a node to select it in the Edit/Delete Issue sidebar controls.
- Dragging a node onto empty space just repositions it; positions are remembered between reruns.

It's plain Cytoscape.js + hand-written JS implementing Streamlit's component protocol — no npm/build step, so `pip install -r requirements.txt` is still all you need.

Data issues (dangling Parent ID / Blocks / Relates To references, or parent cycles) are flagged in a warning panel above the canvas.

## Focusing on a subtree

Above the canvas, **Focus on an issue** filters the canvas down to one issue and all of its descendants — handy once the tree gets big. In **Live Jira connection** mode, focusing on an issue that has a Jira Key also offers **Pull subtree from Jira**, which fetches just that issue and its descendants (via `parent`/Epic Link, walked breadth-first since JQL has no recursive descendant query) instead of the whole project.
