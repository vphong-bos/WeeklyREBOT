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
    hf_model: str
    hf_device: str
    hf_max_new_tokens: int
    hf_temperature: float


def get_settings() -> Settings:
    project_keys = os.getenv("JIRA_PROJECT_KEYS", "").strip()

    return Settings(
        jira_base_url=os.environ["JIRA_BASE_URL"].rstrip("/"),
        jira_email=os.environ["JIRA_EMAIL"],
        jira_api_token=os.environ["JIRA_API_TOKEN"],
        jira_account_id=os.environ["JIRA_ACCOUNT_ID"],
        jira_project_keys=[key.strip() for key in project_keys.split(",") if key.strip()],
        hf_model=os.getenv("HF_MODEL", "Qwen/Qwen2.5-0.5B-Instruct"),
        hf_device=os.getenv("HF_DEVICE", "auto"),
        hf_max_new_tokens=int(os.getenv("HF_MAX_NEW_TOKENS", "1200")),
        hf_temperature=float(os.getenv("HF_TEMPERATURE", "0.2")),
    )