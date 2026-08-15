# mindmapp

Basic Mindmap app for building Jira-style issue hierarchies (Use-Case → Epic → Story → Task → Sub-task), with CSV export and direct Jira sync.

## Jira sync

In the sidebar, open **Jira Connection**:

1. Enter your Jira base URL (e.g. `https://yourcompany.atlassian.net`), choose Cloud (email + API token) or Server/Data Center (personal access token) auth, your credentials, and a project key, then click **Save & Test Connection**.
2. Adjust **Issue Type Mapping** if your project's issue type names differ from `Use-Case` / `Epic` / `Story` / `Task` / `Sub-task`.
3. **Pull from Jira** loads issues matching the JQL query into the table (tracked by their Jira key).
4. **Push to Jira** creates any local issues that don't yet have a Jira key, updates summaries on ones that do, and (re)creates "blocks" issue links.

Credentials are kept only in the browser session's memory, not written to disk.
