from datetime import date
from enum import Enum
from typing import Any

from app.utils.adf import adf_to_text
from app.utils.dates import date_in_range, parse_jira_datetime


class CommentRetrievalMode(str, Enum):
    MEMBER = "member"
    LEADER = "leader"


class JiraCommentFilter:
    def __init__(
        self,
        jira_account_id: str,
        week_start: date,
        week_end: date,
        mode: CommentRetrievalMode = CommentRetrievalMode.MEMBER,
        exclude_replies: bool = True,
    ) -> None:
        self.jira_account_id = jira_account_id
        self.week_start = week_start
        self.week_end = week_end
        self.mode = mode
        self.exclude_replies = exclude_replies

    def filter(self, comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        matched_comments: list[dict[str, Any]] = []

        for comment in comments:
            if not self._is_in_week(comment):
                continue

            if self.exclude_replies and self._is_reply_comment(comment):
                continue

            if not self._matches_mode(comment):
                continue

            body = comment.get("body", {})
            body_text = adf_to_text(body).strip()

            if not body_text:
                continue

            matched_comments.append(
                {
                    "id": comment.get("id"),
                    "created": comment.get("created"),
                    "author_account_id": comment.get("author", {}).get("accountId"),
                    "body_text": body_text,
                    "mode": self.mode.value,
                }
            )

        return matched_comments

    def _is_in_week(self, comment: dict[str, Any]) -> bool:
        created_raw = comment.get("created")

        if not created_raw:
            return False

        created_at = parse_jira_datetime(created_raw)
        return date_in_range(created_at, self.week_start, self.week_end)

    def _matches_mode(self, comment: dict[str, Any]) -> bool:
        if self.mode == CommentRetrievalMode.MEMBER:
            return self._is_own_comment(comment)

        if self.mode == CommentRetrievalMode.LEADER:
            return self._mentions_account(comment.get("body", {}), self.jira_account_id)

        return False

    def _is_own_comment(self, comment: dict[str, Any]) -> bool:
        author = comment.get("author", {})
        return author.get("accountId") == self.jira_account_id

    def _is_reply_comment(self, comment: dict[str, Any]) -> bool:
        reply_markers = (
            "parent",
            "parentId",
            "parent_id",
            "inReplyTo",
            "replyTo",
        )

        return any(comment.get(field) for field in reply_markers)

    def _mentions_account(self, body: Any, account_id: str) -> bool:
        if isinstance(body, dict):
            if body.get("type") == "mention":
                attrs = body.get("attrs", {})
                return attrs.get("id") == account_id

            return any(
                self._mentions_account(value, account_id)
                for value in body.values()
            )

        if isinstance(body, list):
            return any(
                self._mentions_account(item, account_id)
                for item in body
            )

        return False


def retrieve_comments(
    comments: list[dict[str, Any]],
    jira_account_id: str,
    week_start: date,
    week_end: date,
    mode: str = "member",
) -> list[dict[str, Any]]:
    comment_filter = JiraCommentFilter(
        jira_account_id=jira_account_id,
        week_start=week_start,
        week_end=week_end,
        mode=CommentRetrievalMode(mode),
    )

    return comment_filter.filter(comments)