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
4. **Push to Jira** creates any local issues that don't yet have a Jira key, updates summaries on ones that do, and (re)creates "blocks" issue links.

Credentials are kept only in the browser session's memory, not written to disk.
