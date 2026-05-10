from app.utils.adf import adf_to_text


def short_context_from_description(
    description_adf: dict | None,
    max_chars: int = 280,
) -> str:
    text = adf_to_text(description_adf).strip()

    if not text:
        return "No description context."

    if len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip() + "..."


def _format_issue_header(item: dict) -> str:
    issue_key = item.get("issue_key", "UNKNOWN")
    summary = item.get("summary", "No summary")

    category = item.get("category") or item.get("component") or "AI Model"
    subcategory = item.get("subcategory") or item.get("team") or "Quantization Pipeline"
    topic = item.get("topic") or item.get("epic") or "Quantization Pipeline"

    return f"[{category}][{subcategory}][{topic}] {issue_key}: {summary}"


def _format_linked_issue_header(item: dict) -> str:
    """
    Used by the template fallback only.

    The LLM prompt should keep retrieved Jira data plain and provide
    Issue link separately, so the LLM can create the Markdown link in
    the final generated report.
    """
    issue_key = item.get("issue_key", "UNKNOWN")
    summary = item.get("summary", "No summary")
    issue_link = item.get("issue_link")

    category = item.get("category") or item.get("component") or "AI Model"
    subcategory = item.get("subcategory") or item.get("team") or "Quantization Pipeline"
    topic = item.get("topic") or item.get("epic") or "Quantization Pipeline"

    issue_name = f"{issue_key}: {summary}"

    if issue_link:
        issue_name = f"[{issue_name}]({issue_link})"

    return f"[{category}][{subcategory}][{topic}] {issue_name}"


def _format_issue_period(item: dict, week_start: str, week_end: str) -> str:
    start_time = item.get("start_time") or week_start
    due_time = item.get("due_time") or week_end
    return f"[{start_time} ~ {due_time}]"


def _format_comment_lines(comment_text: str) -> list[str]:
    lines: list[str] = []

    for raw_line in comment_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        lines.append(line)

    return lines


def generate_template_report(
    week_start: str,
    week_end: str,
    report_items: list[dict],
) -> str:
    """
    Rule-based fallback report generator.

    Output format:
    - Executive summary
    - Suggestion/Request
    - Weekly Report: Progress Update
    """

    lines: list[str] = [
        "## Executive summary",
        "",
    ]

    if not report_items:
        lines.extend(
            [
                "No Jira comments found for this week.",
                "",
                "## Suggestion/Request",
                "",
                "None",
                "",
                "## Weekly Report: Progress Update",
                "",
                "No Jira comments found for this week.",
                "",
            ]
        )
        return "\n".join(lines)

    for item in report_items:
        header = _format_linked_issue_header(item)
        status = item.get("status", "Unknown")

        lines.extend(
            [
                f"- {header}",
                f"  - Status: {status}",
            ]
        )

        for comment in item.get("comments", []):
            comment_text = comment.get("body_text", "").strip()
            for line in _format_comment_lines(comment_text):
                lines.append(f"  - {line}")

        lines.append("")

    lines.extend(
        [
            "## Suggestion/Request",
            "",
            "None",
            "",
            "## Weekly Report: Progress Update",
            "",
        ]
    )

    for item in report_items:
        header = _format_linked_issue_header(item)
        status = item.get("status", "Unknown")
        period = _format_issue_period(item, week_start, week_end)

        lines.extend(
            [
                header,
                status,
                f" {period}",
                "",
            ]
        )

        context = item.get("context")
        if context and context != "No description context.":
            lines.extend(
                [
                    "Context:",
                    context,
                    "",
                ]
            )

        comments = item.get("comments", [])
        if not comments:
            lines.extend(
                [
                    "No updates found.",
                    "",
                ]
            )
            continue

        lines.append("Progress:")

        for comment in comments:
            comment_text = comment.get("body_text", "").strip()
            for line in _format_comment_lines(comment_text):
                lines.append(line)

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def generate_weekly_prompt(
    week_start: str,
    week_end: str,
    report_items: list[dict],
) -> str:
    """
    Prompt-only generator.

    This does not summarize by itself. It packages retrieved Jira data
    and instructs the LLM to output the required weekly report format.
    """

    lines: list[str] = [
        "You are WeeklyREBOT, a weekly report assistant.",
        "",
        "Goal:",
        "Generate a clear weekly report from the Jira task information below.",
        "",
        "STRICT OUTPUT REQUIREMENTS:",
        "- Return ONLY the final weekly report in Markdown format.",
        "- Do not explain your reasoning.",
        "- Do not include any preface such as 'Here is the report'.",
        "- Do not wrap the report in a Markdown code block.",
        "- Do not output JSON, YAML, HTML, or plain text notes.",
        "- The first line of your response must be: ## Executive summary",
        "- Use Markdown headings, bullet points, tables, and links where appropriate.",
        "- In the final report, attach the Jira ticket link directly to the issue name using Markdown link syntax.",
        "- Do not print Jira ticket links as separate `Issue link:` or `Link:` lines in the final report.",
        "",
        "Required final report Markdown structure:",
        "",
        "## Executive summary",
        "<Summarize key progress across all tasks. Group related work together.>",
        "",
        "## Suggestion/Request",
        "None",
        "",
        "## Weekly Report: Progress Update",
        "",
        "[CATEGORY][SUBCATEGORY][TOPIC] [ISSUE_KEY: Task summary](JIRA_TICKET_LINK)",
        "Status",
        " [START_DATE ~ DUE_DATE]",
        "<Detailed progress update based on comments>",
        "",
        "Rules:",
        "- Use the user's Jira comments as the main source of truth.",
        "- Use Jira task descriptions only as lightweight context.",
        "- Do not invent work that is not supported by comments.",
        "- Keep the report professional and suitable for Confluence.",
        "- Preserve technical details, metrics, experiment results, handoff notes, and Markdown links found in comments.",
        "- If there are no suggestions or requests, write exactly: None.",
        "- Use the retrieved `Issue link` field only to create the Markdown link on the issue name.",
        "- If an `Issue link` is provided, format the issue name exactly as: [ISSUE_KEY: Task summary](Issue link).",
        "- If an `Issue link` is missing, use plain text: ISSUE_KEY: Task summary.",
        "- Do not include a separate `Issue link:` or `Link:` line in the final report.",
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
        return "\n".join(lines)

    for item in report_items:
        # Keep retrieved data plain. The LLM should create the Markdown
        # issue-name link only in the final report.
        header = _format_issue_header(item)
        period = _format_issue_period(item, week_start, week_end)

        lines.extend(
            [
                header,
                f"Status: {item.get('status', 'Unknown')}",
                f"Period: {period}",
            ]
        )

        issue_link = item.get("issue_link")
        if issue_link:
            lines.append(f"Issue link: {issue_link}")

        confluence_links = item.get("confluence_links") or []
        if confluence_links:
            lines.append("Attached Confluence pages:")
            for page in confluence_links:
                title = page.get("title") or "Confluence page"
                url = page.get("url")
                if url:
                    lines.append(f"- [{title}]({url})")
                else:
                    lines.append(f"- {title}")

        lines.extend(
            [
                f"Short context: {item.get('context', 'No description context.')}",
                "Description context:",
                item.get("description_text") or "No description provided.",
                "",
                "User comments this week:",
            ]
        )

        for comment in item.get("comments", []):
            comment_text = comment.get("body_text", "").strip()
            created = comment.get("created", "unknown time")

            if comment_text:
                lines.append(f"- [{created}] {comment_text}")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"