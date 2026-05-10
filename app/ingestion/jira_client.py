import time
import requests
from requests.auth import HTTPBasicAuth

from app.utils.config import Settings


class JiraClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.auth = HTTPBasicAuth(settings.jira_email, settings.jira_api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get(
        self,
        path: str,
        params: dict | None = None,
        *,
        retries: int = 3,
        backoff_seconds: float = 1.0,
        timeout: int = 60,
    ) -> dict:
        url = f"{self.settings.jira_base_url}{path}"

        last_error: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    auth=self.auth,
                    params=params,
                    timeout=timeout,
                )

                response.raise_for_status()
                return response.json()

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError,
            ) as exc:
                last_error = exc

                if attempt >= retries:
                    raise

                sleep_seconds = backoff_seconds * attempt
                time.sleep(sleep_seconds)

            except requests.exceptions.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else None
                response_text = exc.response.text[:1000] if exc.response is not None else ""

                raise requests.exceptions.HTTPError(
                    f"Jira request failed: status={status_code}, "
                    f"path={path}, params={params}, body={response_text}"
                ) from exc

            except ValueError as exc:
                raise ValueError(
                    f"Jira response was not valid JSON. path={path}, params={params}"
                ) from exc

        raise RuntimeError(
            f"Jira request failed after {retries} attempts. "
            f"path={path}, params={params}, last_error={last_error}"
        )

    def _build_project_clause(self) -> str:
        if not self.settings.jira_project_keys:
            return ""

        quoted_keys = [f'"{key}"' for key in self.settings.jira_project_keys]
        keys = ", ".join(quoted_keys)

        return f"project in ({keys})"

    def _build_updated_window_clause(self, week_start: str, week_end: str) -> str:
        # This is only a candidate issue filter.
        # Actual comment date filtering still happens after fetching comments.
        return f'updated >= "{week_start}" AND updated <= "{week_end}"'

    def _build_candidate_issue_jql(self, week_start: str, week_end: str) -> str:
        clauses = []

        project_clause = self._build_project_clause()
        if project_clause:
            clauses.append(project_clause)

        clauses.append(self._build_updated_window_clause(week_start, week_end))

        return " AND ".join(clauses) + " ORDER BY updated DESC"

    def _search_issues_by_jql_page(
        self,
        jql: str,
        *,
        max_results: int = 100,
        fields: str = "key,summary,status,description,updated,issuetype,parent,labels,components",
        next_page_token: str | None = None,
    ) -> dict:
        params = {
            "jql": jql,
            "fields": fields,
            "maxResults": max_results,
        }

        if next_page_token:
            params["nextPageToken"] = next_page_token

        return self._get(
            "/rest/api/3/search/jql",
            params=params,
        )

    def search_issues(self, week_start: str, week_end: str, max_results: int = 100) -> list[dict]:
        """
        Search candidate Jira issues by project and updated window.
        Actual comment author/date filtering happens after fetching comments.
        """
        jql = self._build_candidate_issue_jql(week_start, week_end)

        all_issues: list[dict] = []
        next_page_token: str | None = None

        while True:
            result = self._search_issues_by_jql_page(
                jql,
                max_results=max_results,
                next_page_token=next_page_token,
            )

            issues = result.get("issues", [])
            all_issues.extend(issues)

            next_page_token = result.get("nextPageToken")

            if not next_page_token:
                break
        return all_issues

    def get_issue_comments(self, issue_key: str) -> list[dict]:
        """
        Fetch all comments for a Jira issue, including pagination.
        """
        all_comments: list[dict] = []
        start_at = 0
        max_results = 100

        while True:
            result = self._get(
                f"/rest/api/3/issue/{issue_key}/comment",
                params={
                    "startAt": start_at,
                    "maxResults": max_results,
                    "orderBy": "created",
                },
            )

            comments = result.get("comments", [])
            total = result.get("total", 0)
            returned = len(comments)

            all_comments.extend(comments)

            if returned == 0:
                break

            start_at += returned

            if start_at >= total:
                break

        return all_comments
