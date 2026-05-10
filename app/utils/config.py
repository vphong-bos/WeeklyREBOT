import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    jira_base_url: str
    jira_email: str
    jira_api_token: str
    jira_account_id: str
    jira_project_keys: list[str]
    report_output_path: str


def get_settings() -> Settings:
    project_keys = os.getenv("JIRA_PROJECT_KEYS", "").strip()

    return Settings(
        jira_base_url=os.environ["JIRA_BASE_URL"].rstrip("/"),
        jira_email=os.environ["JIRA_EMAIL"],
        jira_api_token=os.environ["JIRA_API_TOKEN"],
        jira_account_id=os.environ["JIRA_ACCOUNT_ID"],
        jira_project_keys=[key.strip() for key in project_keys.split(",") if key.strip()],
        report_output_path=os.getenv(
            "REPORT_OUTPUT_PATH",
            "data/processed/weekly_report.md",
        ),
    )