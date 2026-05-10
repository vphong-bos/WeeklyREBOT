from datetime import date
from pathlib import Path

from app.ingestion.jira_client import JiraClient
from app.llm.hf_client import HuggingFaceLLMClient
from app.llm.generator import (
    generate_template_report,
    generate_weekly_prompt,
    short_context_from_description,
)
from app.retrieval.comment_filter import filter_user_comments_for_week
from app.utils.adf import adf_to_text
from app.utils.config import Settings


class WeeklyReportBot:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jira = JiraClient(settings)

    def collect_report_items(self, week_start: date, week_end: date) -> list[dict]:
        issues = self.jira.search_issues(str(week_start), str(week_end))
        report_items = []

        for issue in issues:
            issue_key = issue["key"]
            fields = issue.get("fields", {})

            comments = self.jira.get_issue_comments(issue_key)
            my_comments = filter_user_comments_for_week(
                comments=comments,
                jira_account_id=self.settings.jira_account_id,
                week_start=week_start,
                week_end=week_end,
            )

            if not my_comments:
                continue

            description_adf = fields.get("description")
            description_text = adf_to_text(description_adf).strip()

            report_items.append(
                {
                    "issue_key": issue_key,
                    "summary": fields.get("summary", "No summary"),
                    "status": fields.get("status", {}).get("name", "Unknown"),
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
                        "summary": item["summary"],
                        "status": item["status"],
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
