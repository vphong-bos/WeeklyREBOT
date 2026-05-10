from app.utils.adf import adf_to_text


def short_context_from_description(description_adf: dict | None, max_chars: int = 280) -> str:
    text = adf_to_text(description_adf).strip().replace("", " ")

    if not text:
        return "No description context."

    if len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip() + "..."


def generate_template_report(
    week_start: str,
    week_end: str,
    report_items: list[dict],
) -> str:
    """
    Rule-based fallback report generator.
    Use this when no external LLM is available.
    """
    lines = [
        f"# Weekly Report: {week_start} to {week_end}",
        "",
        "## Summary",
        f"Worked on {len(report_items)} Jira task(s) this week based on my Jira comments.",
        "",
        "## Task Updates",
        "",
    ]

    if not report_items:
        lines.extend(
            [
                "No Jira comments found for this week.",
                "",
            ]
        )
        return "".join(lines)

    for item in report_items:
        lines.extend(
            [
                f"### {item['issue_key']} — {item['summary']}",
                f"- Status: {item['status']}",
                f"- Context: {item['context']}",
                "- My updates:",
            ]
        )

        for comment in item["comments"]:
            comment_text = comment["body_text"].strip()
            if comment_text:
                for line in comment_text.splitlines():
                    if line.strip():
                        lines.append(f"  - {line.strip()}")

        lines.append("")

    lines.extend(
        [
            "## Blockers",
            "- TBD",
            "",
            "## Plan for Next Week",
            "- TBD",
            "",
        ]
    )

    return "".join(lines)


def generate_weekly_prompt(
    week_start: str,
    week_end: str,
    report_items: list[dict],
) -> str:
    """
    Prompt-only generator.

    This should not summarize by itself. It only packages retrieved Jira data
    into a clear prompt for an LLM or human review.
    """
    lines = [
        "You are WeeklyREBOT, a weekly report assistant.",
        "",
        "Goal:",
        "Generate a clear weekly report from the Jira task information below.",
        "",
        "Rules:",
        "- Use the user's Jira comments as the main source of truth.",
        "- Use Jira task descriptions only as lightweight context.",
        "- Do not invent work that is not supported by the comments.",
        "- Keep the report professional, concise, and suitable for Confluence.",
        "- If there are no blockers in the comments, write: No major blockers mentioned.",
        "- If there are no next-week plans in the comments, write: TBD.",
        "",
        "Output format:",
        f"# Weekly Report: {week_start} to {week_end}",
        "",
        "## Summary",
        "- 2 to 5 bullet points summarizing the week.",
        "",
        "## Task Updates",
        "For each task:",
        "### ISSUE_KEY — Task summary",
        "- Context: one short sentence",
        "- Progress: bullet points based on user comments",
        "- Status: Jira status",
        "",
        "## Blockers",
        "- Mention only blockers supported by comments.",
        "",
        "## Plan for Next Week",
        "- Mention only next steps supported by comments.",
        "",
        "Retrieved Jira data:",
        "",
    ]

    if not report_items:
        lines.extend(
            [
                "No Jira comments were found for this week.",
                "",
            ]
        )
        return "".join(lines)

    for item in report_items:
        lines.extend(
            [
                f"## {item['issue_key']} — {item['summary']}",
                f"Status: {item['status']}",
                f"Short context: {item['context']}",
                "Description context:",
                item.get("description_text") or "No description provided.",
                "",
                "User comments this week:",
            ]
        )

        for comment in item["comments"]:
            comment_text = comment["body_text"].strip()
            created = comment.get("created", "unknown time")
            if comment_text:
                lines.append(f"- [{created}] {comment_text}")

        lines.append("")

    return "".join(lines)
