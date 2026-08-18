import requests


class JiraError(Exception):
    pass


class JiraClient:
    """Thin wrapper around the Jira REST API for a user-supplied site."""

    def __init__(self, base_url, auth_mode="cloud", email=None, api_token=None,
                 username=None, password=None, api_version="3", timeout=20):
        if not base_url:
            raise JiraError("Jira base URL is required")
        self.base_url = base_url.rstrip("/")
        self.rest = f"{self.base_url}/rest/api/{api_version}"
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        if auth_mode == "cloud":
            if not email or not api_token:
                raise JiraError("Email and API token are required for Jira Cloud auth")
            self.session.auth = (email, api_token)
        elif auth_mode == "server":
            if not username or not password:
                raise JiraError("Username and password are required for Jira Server/Data Center auth")
            self.session.auth = (username, password)
        else:
            raise JiraError(f"Unknown auth_mode: {auth_mode}")

    def _request(self, method, path, **kwargs):
        url = f"{self.rest}/{path.lstrip('/')}"
        try:
            r = self.session.request(method, url, timeout=self.timeout, **kwargs)
        except requests.RequestException as e:
            raise JiraError(f"Could not reach {url}: {e}") from e
        if r.status_code >= 400:
            raise JiraError(f"{method} {path} failed ({r.status_code}): {r.text[:500]}")
        return r

    def test_connection(self):
        return self._request("GET", "myself").json()

    def field_id_by_name(self, name):
        for f in self._request("GET", "field").json():
            if f.get("name", "").lower() == name.lower():
                return f["id"]
        return None

    def blocks_link_type_name(self):
        types = self._request("GET", "issueLinkType").json().get("issueLinkTypes", [])
        for lt in types:
            if lt.get("name", "").lower() == "blocks":
                return lt["name"]
        return types[0]["name"] if types else None

    def discover_schema(self):
        return {
            "epic_name_field": self.field_id_by_name("Epic Name"),
            "epic_link_field": self.field_id_by_name("Epic Link"),
            "blocks_link_type": self.blocks_link_type_name(),
        }

    def search_issues(self, jql, max_results=500, page_size=100):
        fields = "summary,issuetype,parent,issuelinks"
        issues = []
        start_at = 0
        while len(issues) < max_results:
            params = {"jql": jql, "startAt": start_at, "maxResults": page_size, "fields": fields}
            data = self._request("GET", "search", params=params).json()
            batch = data.get("issues", [])
            issues.extend(batch)
            start_at += len(batch)
            if not batch or start_at >= data.get("total", 0):
                break
        return issues[:max_results]

    def create_issue(self, project_key, issue_type, summary, extra_fields=None):
        fields = {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "summary": summary,
        }
        if extra_fields:
            fields.update(extra_fields)
        return self._request("POST", "issue", json={"fields": fields}).json()["key"]

    def update_issue_summary(self, key, summary):
        self._request("PUT", f"issue/{key}", json={"fields": {"summary": summary}})

    def create_link(self, outward_key, inward_key, link_type_name):
        payload = {
            "type": {"name": link_type_name},
            "outwardIssue": {"key": outward_key},
            "inwardIssue": {"key": inward_key},
        }
        self._request("POST", "issueLink", json=payload)
