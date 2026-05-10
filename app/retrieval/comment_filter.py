from datetime import date

from app.utils.adf import adf_to_text
from app.utils.dates import date_in_range, parse_jira_datetime


def filter_user_comments_for_week(
    comments: list[dict],
    jira_account_id: str,
    week_start: date,
    week_end: date,
) -> list[dict]:
    matched_comments: list[dict] = []

    for comment in comments:
        author = comment.get("author", {})
        created_raw = comment.get("created")

        if not created_raw:
            continue

        created_at = parse_jira_datetime(created_raw)

        if author.get("accountId") != jira_account_id:
            continue

        if not date_in_range(created_at, week_start, week_end):
            continue

        body_text = adf_to_text(comment.get("body", {})).strip()
        matched_comments.append(
            {
                "id": comment.get("id"),
                "created": created_raw,
                "body_text": body_text,
            }
        )

    return matched_comments
