from datetime import date
from pathlib import Path
from typing import Any

from app.ingestion.jira_client import JiraClient
from app.llm.hf_client import HuggingFaceLLMClient
from app.llm.generator import (
    generate_template_report,
    generate_weekly_prompt,
    short_context_from_description,
)
from app.retrieval.comment_filter import retrieve_comments
from app.utils.adf import adf_to_text
from app.utils.config import Settings


class WeeklyReportBot:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jira = JiraClient(settings)

    def _issue_url(self, issue_key: str) -> str:
        base_url = self.settings.jira_base_url.rstrip("/")
        return f"{base_url}/browse/{issue_key}"

    def _extract_issue_time_fields(self, fields: dict[str, Any]) -> dict[str, str | None]:
        """
        Extract start/due fields from Jira issue fields.

        Jira usually stores custom fields as customfield_XXXXX.
        So we use Jira field metadata from JiraClient.get_field_name_by_id()
        to map customfield IDs back to readable names.

        Built-in Jira due date is usually fields["duedate"].
        Start date is usually a custom field, depending on your Jira setup.
        """

        field_name_by_id = self.jira.get_field_name_by_id()

        start_time = self._get_configured_field_value(
            fields,
            setting_names=(
                "jira_start_field_id",
                "jira_start_date_field_id",
            ),
        )

        due_time = self._get_configured_field_value(
            fields,
            setting_names=(
                "jira_due_field_id",
                "jira_due_date_field_id",
            ),
        )

        if not due_time:
            due_time = fields.get("duedate")

        if not start_time or not due_time:
            detected = self._detect_time_fields_by_field_name(
                fields=fields,
                field_name_by_id=field_name_by_id,
            )

            if not start_time:
                start_time = detected.get("start_time")

            if not due_time:
                due_time = detected.get("due_time")

        return {
            "start_time": self._normalize_jira_field_value(start_time),
            "due_time": self._normalize_jira_field_value(due_time),
        }

    def _get_configured_field_value(
        self,
        fields: dict[str, Any],
        setting_names: tuple[str, ...],
    ) -> Any:
        """
        Optional support for explicit field IDs in Settings.

        Example:
            JIRA_START_FIELD_ID=customfield_10015
            JIRA_DUE_FIELD_ID=duedate
        """

        for setting_name in setting_names:
            field_id = getattr(self.settings, setting_name, None)

            if field_id and fields.get(field_id) not in (None, "", []):
                return fields.get(field_id)

        return None

    def _detect_time_fields_by_field_name(
        self,
        fields: dict[str, Any],
        field_name_by_id: dict[str, str],
    ) -> dict[str, Any]:
        start_time = None
        due_time = None

        start_keywords = (
            "start",
            "start date",
            "start time",
            "target start",
            "planned start",
        )

        due_keywords = (
            "due",
            "due date",
            "due time",
            "target end",
            "target due",
            "planned end",
            "end date",
        )

        for field_id, value in fields.items():
            if value in (None, "", []):
                continue

            field_name = field_name_by_id.get(field_id, "").strip().lower()

            if not field_name:
                continue

            if not start_time and self._field_name_matches(field_name, start_keywords):
                start_time = value

            if not due_time and self._field_name_matches(field_name, due_keywords):
                due_time = value

            if start_time and due_time:
                break

        return {
            "start_time": start_time,
            "due_time": due_time,
        }

    def _field_name_matches(self, field_name: str, candidates: tuple[str, ...]) -> bool:
        if field_name in candidates:
            return True

        return any(candidate in field_name for candidate in candidates)

    def _normalize_jira_field_value(self, value: Any) -> str | None:
        """
        Jira field values can be strings, dicts, lists, or option objects.
        Convert them into readable text for report output.
        """

        if value in (None, "", []):
            return None

        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            for key in (
                "value",
                "name",
                "displayName",
                "start",
                "end",
                "date",
                "from",
                "to",
            ):
                if value.get(key):
                    return str(value[key])

            return str(value)

        if isinstance(value, list):
            values = [
                self._normalize_jira_field_value(item)
                for item in value
            ]
            values = [item for item in values if item]
            return ", ".join(values) if values else None

        return str(value)

    def debug_print_issue_time_candidates(self, fields: dict[str, Any]) -> None:
        """
        Temporary helper.

        Use this once to discover the real Jira custom field IDs for
        start/due fields, then remove or stop calling it.
        """

        field_name_by_id = self.jira.get_field_name_by_id()

        for field_id, value in fields.items():
            if value in (None, "", []):
                continue

            field_name = field_name_by_id.get(field_id, field_id)

            lowered = field_name.lower()
            if (
                "start" in lowered
                or "due" in lowered
                or "end" in lowered
                or "target" in lowered
                or "planned" in lowered
            ):
                print("=" * 80)
                print(f"{field_id}: {field_name}")
                print(value)

    def collect_report_items(self, week_start: date, week_end: date) -> list[dict]:
        issues = self.jira.search_issues(str(week_start), str(week_end))
        report_items = []

        for issue in issues:
            issue_key = issue["key"]
            fields = issue.get("fields", {})

            comments = self.jira.get_issue_comments(issue_key)
            my_comments = retrieve_comments(
                comments=comments,
                jira_account_id=self.settings.jira_account_id,
                week_start=week_start,
                week_end=week_end,
            )

            if not my_comments:
                continue

            description_adf = fields.get("description")
            description_text = adf_to_text(description_adf).strip()
            time_fields = self._extract_issue_time_fields(fields)

            report_items.append(
                {
                    "issue_key": issue_key,
                    "issue_link": self._issue_url(issue_key),
                    "summary": fields.get("summary", "No summary"),
                    "status": fields.get("status", {}).get("name", "Unknown"),
                    "start_time": time_fields["start_time"],
                    "due_time": time_fields["due_time"],
                    "context": short_context_from_description(description_adf),
                    "description_text": description_text,
                    "comments": my_comments,
                }
            )

        return report_items

    def collect_retrieved_comments(self, week_start: date, week_end: date) -> list[dict]:
        report_items = self.collect_report_items(week_start, week_end)
        retrieved_comments: list[dict] = []

        for item in report_items:
            for comment in item["comments"]:
                retrieved_comments.append(
                    {
                        "issue_key": item["issue_key"],
                        "issue_link": item["issue_link"],
                        "summary": item["summary"],
                        "status": item["status"],
                        "start_time": item.get("start_time"),
                        "due_time": item.get("due_time"),
                        "comment_id": comment.get("id"),
                        "created": comment.get("created"),
                        "body_text": comment.get("body_text", ""),
                    }
                )

        return retrieved_comments

    def generate_prompt_from_items(
        self,
        week_start: date,
        week_end: date,
        report_items: list[dict],
    ) -> str:
        return generate_weekly_prompt(
            week_start=str(week_start),
            week_end=str(week_end),
            report_items=report_items,
        )

    def generate_template_from_items(
        self,
        week_start: date,
        week_end: date,
        report_items: list[dict],
    ) -> str:
        return generate_template_report(
            week_start=str(week_start),
            week_end=str(week_end),
            report_items=report_items,
        )

    def generate_prompt(self, week_start: date, week_end: date) -> str:
        report_items = self.collect_report_items(week_start, week_end)
        return self.generate_prompt_from_items(week_start, week_end, report_items)

    def generate_template(self, week_start: date, week_end: date) -> str:
        report_items = self.collect_report_items(week_start, week_end)
        return self.generate_template_from_items(week_start, week_end, report_items)

    def generate_with_huggingface(
        self,
        week_start: date,
        week_end: date,
        model: str | None = None,
    ) -> str:
        report_items = self.collect_report_items(week_start, week_end)
        return self.generate_with_huggingface_from_items(
            week_start,
            week_end,
            report_items,
            model=model,
        )

    def generate_with_huggingface_from_items(
        self,
        week_start: date,
        week_end: date,
        report_items: list[dict],
        model: str | None = None,
    ) -> str:
        prompt = self.generate_prompt_from_items(week_start, week_end, report_items)
        client = HuggingFaceLLMClient(
            model=model or self.settings.hf_model,
            max_new_tokens=self.settings.hf_max_new_tokens,
            temperature=self.settings.hf_temperature,
            device=self.settings.hf_device,
        )
        return client.generate(prompt)

    def generate(
        self,
        week_start: date,
        week_end: date,
        *,
        llm_provider: str = "huggingface",
        model: str | None = None,
    ) -> str:
        if llm_provider == "huggingface":
            return self.generate_with_huggingface(
                week_start=week_start,
                week_end=week_end,
                model=model,
            )

        if llm_provider == "template":
            return self.generate_template(week_start, week_end)

        raise ValueError(f"Unsupported llm_provider: {llm_provider}")

    def save_report(self, markdown: str) -> Path:
        output_path = Path(self.settings.report_output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        return output_path