from datetime import date

from app.retrieval.comment_filter import filter_user_comments_for_week

def test_filter_user_comments_for_week_returns_matching_comments_with_plain_text():
    comments = [
        {
            "id": "1001",
            "created": "2026-05-08T10:20:30.123+0700",
            "author": {"accountId": "user-123"},
            "body": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Finished ETL checks"}],
                    }
                ],
            },
        }
    ]

    matched_comments = filter_user_comments_for_week(
        comments=comments,
        jira_account_id="user-123",
        week_start=date(2026, 5, 5),
        week_end=date(2026, 5, 10),
    )

    assert matched_comments == [
        {
            "id": "1001",
            "created": "2026-05-08T10:20:30.123+0700",
            "body_text": "Finished ETL checks",
        }
    ]


def test_filter_user_comments_for_week_excludes_non_matching_comments():
    comments = [
        {
            "id": "1001",
            "created": "2026-05-08T10:20:30.123+0700",
            "author": {"accountId": "other-user"},
            "body": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Wrong author"}],
                    }
                ],
            },
        },
        {
            "id": "1002",
            "created": "2026-05-01T10:20:30.123+0700",
            "author": {"accountId": "user-123"},
            "body": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Outside week"}],
                    }
                ],
            },
        },
        {
            "id": "1003",
            "author": {"accountId": "user-123"},
            "body": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Missing date"}],
                    }
                ],
            },
        },
    ]

    matched_comments = filter_user_comments_for_week(
        comments=comments,
        jira_account_id="user-123",
        week_start=date(2026, 5, 5),
        week_end=date(2026, 5, 10),
    )

    assert matched_comments == []
