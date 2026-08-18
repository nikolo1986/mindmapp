# Mindmapp User Guide

Mindmapp is a Streamlit app for building a Use-Case → Epic → Story → Task → Sub-task issue tree, visualizing it, and — optionally — syncing it directly to a Jira project you connect yourself.

## Connection modes

A toggle at the top of the sidebar controls how much of the app you see:

- **CSV / Excel only** (default) — no Jira account needed. Build the tree by hand and download/upload it as a spreadsheet. The Jira Connection section is hidden entirely.
- **Live Jira connection** — reveals the Jira Connection section: connect to a real Jira site, pull existing issues in, and push local changes back out.

## Building the tree

Every issue has a level, a summary, a parent, and two optional relationships.

### Issue levels

| Level | Shape on canvas |
|---|---|
| Use-Case | Ellipse (blue) |
| Epic | Round rectangle (green) |
| Story | Diamond (orange) |
| Task | Triangle (gray) |
| Sub-task | Hexagon (purple) |

### Three ways to change the tree

- **Add Issue** — pick a level, fill in a summary, optionally set Parent ID / Blocks / Relates To, then **Add**. Epics get an extra "Epic Name" field for Jira.
- **Edit Issue** — pick an existing ID, edit its fields, then **Save Changes**.
- **Issue Table (editable)** — edit any cell directly, or add/remove rows with the table's own controls.

All three write to the same data, so a change in one place shows up everywhere else — including the canvas — immediately.

### Relationships

- **Parent ID** — the tree structure itself; solid gray arrow.
- **Blocks** (comma-separated IDs) — dashed red arrow; becomes a real Jira "Blocks" link on sync.
- **Relates To** (comma-separated IDs) — dotted blue line; e.g. a Task that satisfies a Story. Syncs to Jira's built-in "Relates" link.

### Deleting an issue

**Delete Issue** has a **Delete Mode**:

- **Just this issue** — children lose their parent but stay in the tree.
- **Cascade** — the issue and every descendant underneath it are removed.

Either way, a confirmation step stands before the deletion happens.

## Reading the canvas

The mindmap canvas is a **read-only diagram** — it renders whatever is in the table. To change the tree, use the sidebar forms or edit the table; the canvas catches up automatically.

- Shape and color = issue level.
- A **dashed amber border** means the issue hasn't been pushed to Jira yet.
- Edge style (solid / dashed / dotted) = relationship type, as above.

If the canvas ever looks blank where you expect nodes, it's almost always a network/content-blocker issue loading the graphing library, not a problem with your data — the table above it is unaffected.

## Focusing on a subtree

**Focus on an issue** (above the canvas) narrows the diagram to one issue plus everything underneath it — useful once the tree gets large. **Clear Focus** returns to showing everything. In Live Jira mode, focusing on an issue with a Jira Key also offers a one-click subtree pull for just that branch.

## Jira sync

Everything here lives under **Jira Connection** in the sidebar, visible only in Live Jira connection mode.

### Connect

1. **Jira Base URL** — e.g. `https://yourcompany.atlassian.net`
2. **Auth Type** — Jira Cloud (email + API token) or Server/Data Center (username + password)
3. **Project Key** — e.g. `MMP`
4. **Save & Test Connection**

### Issue Type Mapping

If your Jira project's issue types aren't literally named `Use-Case` / `Epic` / `Story` / `Task` / `Sub-task`, remap each one to the real type name in your project before pulling or pushing.

### Getting issues in

- **Pull from Jira** — runs the JQL query shown above it (defaults to your whole project) and loads every matching issue.
- **Pull Subtree from Root** — type one issue's key directly (e.g. `MMP-1`) into **Root Issue Key** and pull just that issue plus every child, grandchild, etc. beneath it. The issue doesn't need to already be loaded — this is the way to start from one known parent in a large project without listing everything first.

Both merge into the existing table rather than replacing it.

### Sending issues back

**Push to Jira** creates any local issue without a Jira Key yet, updates summaries on ones that already have one, and (re)creates Blocks/Relates To links. Parents are always pushed before their children.

## Import & export

**Download CSV** / **Download Excel** save the current table. **Upload CSV or Excel to replace table** loads one back in — the primary workflow in CSV/Excel-only mode, and usable alongside Jira sync too.

## Clearing & resetting

- **Reset to Defaults** — replaces the table with the small built-in example tree.
- **Clear All Issues** — empties the table, after a confirmation step.

**Neither ever touches real Jira** — both only affect the local table. If you clear by mistake, bring issues back with Pull from Jira or Upload CSV/Excel.

## Tips & troubleshooting

- **Don't see Jira Connection?** Connection Mode is probably still CSV / Excel only — switch it at the top of the sidebar.
- **Pull or Push fails immediately?** Click Save & Test Connection first.
- **Parent field silently ignored on push?** Check Issue Type Mapping — a level mapped to a type name that doesn't exist in your project fails on create.
- **Dashed amber border won't clear?** That issue hasn't been pushed to Jira yet, or the last push for it failed — check for an error message after Push to Jira.
- **A data-issue warning appeared?** It's flagging a Parent ID / Blocks / Relates To value that doesn't match any real ID — usually a typo in a comma-separated list.
