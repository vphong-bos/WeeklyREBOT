from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ADFTextConverter:
    """
    Convert Atlassian Document Format JSON into readable plain text.

    This converter handles ADF content text, including links inside comments
    and descriptions.

    Jira issue metadata such as issue link, start time, and due time should be
    extracted from Jira issue fields, not from ADF attrs.
    """

    def __init__(
        self,
        *,
        include_urls: bool = True,
        include_media_placeholders: bool = True,
        include_status: bool = True,
        table_cell_separator: str = " | ",
    ) -> None:
        self.include_urls = include_urls
        self.include_media_placeholders = include_media_placeholders
        self.include_status = include_status
        self.table_cell_separator = table_cell_separator

    def convert(self, node: Any) -> str:
        return self._normalize(self._walk(node))

    def _normalize(self, text: str) -> str:
        lines = [line.rstrip() for line in text.splitlines()]
        return "\n".join(lines).strip()

    def _join_blocks(self, parts: list[str]) -> str:
        cleaned = [part.strip("\n") for part in parts if part and part.strip()]
        return "\n".join(cleaned)

    def _walk(
        self,
        value: Any,
        *,
        list_depth: int = 0,
        ordered_index: int | None = None,
    ) -> str:
        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, list):
            return "".join(
                self._walk(
                    child,
                    list_depth=list_depth,
                    ordered_index=ordered_index,
                )
                for child in value
            )

        if not isinstance(value, dict):
            return ""

        node_type = value.get("type")
        attrs = value.get("attrs") or {}
        content = value.get("content") or []
        marks = value.get("marks") or []

        # -------------------------
        # Root / generic containers
        # -------------------------
        if node_type == "doc":
            return self._join_blocks([self._walk(child) for child in content]) + "\n"

        if node_type in {
            "layoutSection",
            "layoutColumn",
            "bodiedExtension",
            "extension",
            "nestedExpand",
            "expand",
        }:
            title = attrs.get("title") or attrs.get("text")
            body = self._join_blocks([self._walk(child) for child in content])

            parts = []
            if title:
                parts.append(str(title))
            if body:
                parts.append(body)

            return "\n".join(parts) + ("\n" if parts else "")

        # -------------------------
        # Text and inline nodes
        # -------------------------
        if node_type == "text":
            return self._format_text_node(
                text=value.get("text", ""),
                marks=marks,
            )

        if node_type == "hardBreak":
            return "\n"

        if node_type == "mention":
            return attrs.get("text") or attrs.get("displayName") or attrs.get("id") or ""

        if node_type == "emoji":
            return attrs.get("shortName") or attrs.get("text") or attrs.get("id") or ""

        if node_type == "date":
            return self._format_adf_date(attrs)

        if node_type == "status":
            if not self.include_status:
                return ""
            text = attrs.get("text") or ""
            color = attrs.get("color")
            return f"[{text}]" if text else (f"[status: {color}]" if color else "")

        if node_type == "inlineCard":
            return self._format_card(attrs)

        if node_type == "blockCard":
            card = self._format_card(attrs)
            return card + ("\n" if card else "")

        if node_type == "embedCard":
            card = self._format_card(attrs)
            return card + ("\n" if card else "")

        if node_type == "placeholder":
            return attrs.get("text", "")

        # -------------------------
        # Blocks
        # -------------------------
        if node_type == "paragraph":
            text = self._walk(content, list_depth=list_depth)
            return text + ("\n" if text else "")

        if node_type == "heading":
            level = attrs.get("level", 1)
            text = self._walk(content, list_depth=list_depth).strip()
            if not text:
                return ""
            return f"{'#' * max(1, min(int(level), 6))} {text}\n"

        if node_type == "blockquote":
            text = self._normalize(self._walk(content, list_depth=list_depth))
            if not text:
                return ""
            return "\n".join(
                f"> {line}" if line else ">"
                for line in text.splitlines()
            ) + "\n"

        if node_type == "codeBlock":
            language = attrs.get("language")
            code = self._walk(content, list_depth=list_depth).rstrip("\n")
            if language:
                return f"```{language}\n{code}\n```\n"
            return f"```\n{code}\n```\n"

        if node_type == "rule":
            return "---\n"

        if node_type == "panel":
            panel_type = attrs.get("panelType")
            text = self._normalize(self._walk(content, list_depth=list_depth))
            if not text:
                return ""

            prefix = f"[{panel_type}] " if panel_type else ""
            return f"{prefix}{text}\n"

        # -------------------------
        # Lists
        # -------------------------
        if node_type == "bulletList":
            return "".join(
                self._walk(child, list_depth=list_depth + 1)
                for child in content
            )

        if node_type == "orderedList":
            start = attrs.get("order", attrs.get("start", 1))
            try:
                start = int(start)
            except Exception:
                start = 1

            parts = []
            for index, child in enumerate(content, start=start):
                parts.append(
                    self._walk(
                        child,
                        list_depth=list_depth + 1,
                        ordered_index=index,
                    )
                )
            return "".join(parts)

        if node_type == "listItem":
            text = self._normalize(self._walk(content, list_depth=list_depth))
            if not text:
                return ""

            indent = "  " * max(0, list_depth - 1)
            bullet = f"{ordered_index}." if ordered_index is not None else "-"
            lines = text.splitlines()

            first = f"{indent}{bullet} {lines[0]}"
            rest = [f"{indent}  {line}" if line else "" for line in lines[1:]]

            return "\n".join([first, *rest]) + "\n"

        # -------------------------
        # Tasks and decisions
        # -------------------------
        if node_type == "taskList":
            return "".join(
                self._walk(child, list_depth=list_depth)
                for child in content
            )

        if node_type == "taskItem":
            state = attrs.get("state")
            checkbox = "[x]" if state == "DONE" else "[ ]"
            text = self._normalize(self._walk(content, list_depth=list_depth))
            return f"{checkbox} {text}\n" if text else f"{checkbox}\n"

        if node_type == "decisionList":
            return "".join(
                self._walk(child, list_depth=list_depth)
                for child in content
            )

        if node_type == "decisionItem":
            text = self._normalize(self._walk(content, list_depth=list_depth))
            return f"Decision: {text}\n" if text else ""

        # -------------------------
        # Tables
        # -------------------------
        if node_type == "table":
            rows = [
                self._walk(child, list_depth=list_depth).rstrip("\n")
                for child in content
            ]
            rows = [row for row in rows if row.strip()]
            return "\n".join(rows) + ("\n" if rows else "")

        if node_type == "tableRow":
            cells = []
            for child in content:
                cell_text = self._normalize(self._walk(child, list_depth=list_depth))
                cell_text = " ".join(cell_text.splitlines())
                cells.append(cell_text)
            return self.table_cell_separator.join(cells) + "\n"

        if node_type in {"tableCell", "tableHeader"}:
            return self._walk(content, list_depth=list_depth)

        # -------------------------
        # Media / files
        # -------------------------
        if node_type == "mediaSingle":
            return self._walk(content, list_depth=list_depth)

        if node_type == "mediaGroup":
            return "".join(
                self._walk(child, list_depth=list_depth)
                for child in content
            )

        if node_type == "media":
            return self._format_media(attrs)

        # -------------------------
        # Jira / Confluence special-ish nodes
        # -------------------------
        if node_type == "unsupportedBlock":
            original = attrs.get("originalValue") or attrs.get("type")
            return f"[unsupported block: {original}]\n" if original else ""

        if node_type == "unsupportedInline":
            original = attrs.get("originalValue") or attrs.get("type")
            return f"[unsupported inline: {original}]" if original else ""

        if node_type == "fragment":
            return self._walk(content, list_depth=list_depth)

        # -------------------------
        # Fallback
        # -------------------------
        if content:
            return self._walk(content, list_depth=list_depth)

        fallback_keys = ("text", "title", "name", "label", "id")
        if self.include_urls:
            fallback_keys = ("text", "title", "name", "label", "url", "href", "link", "id")

        for key in fallback_keys:
            if attrs.get(key):
                return str(attrs[key])

        return ""

    def _format_text_node(self, text: str, marks: list[dict[str, Any]]) -> str:
        if not text:
            return ""

        if not self.include_urls:
            return text

        href = self._extract_link_from_marks(marks)
        if not href:
            return text

        if href == text:
            return href

        return f"[{text}]({href})"

    def _extract_link_from_marks(self, marks: list[dict[str, Any]]) -> str | None:
        for mark in marks:
            if mark.get("type") != "link":
                continue

            attrs = mark.get("attrs") or {}
            href = attrs.get("href") or attrs.get("url") or attrs.get("link")

            if href:
                return str(href)

        return None

    def _format_card(self, attrs: dict[str, Any]) -> str:
        url = attrs.get("url") or attrs.get("href") or attrs.get("link")
        data = attrs.get("data") or {}

        title = (
            data.get("name")
            or data.get("title")
            or data.get("text")
            or attrs.get("title")
            or attrs.get("text")
            or url
        )

        if self.include_urls and url and title and title != url:
            return f"[{title}]({url})"

        return title or ""

    def _format_media(self, attrs: dict[str, Any]) -> str:
        if not self.include_media_placeholders:
            return ""

        media_type = attrs.get("type")
        alt = attrs.get("alt")
        filename = attrs.get("fileName") or attrs.get("filename") or attrs.get("name")
        url = attrs.get("url") or attrs.get("href") or attrs.get("link")

        label = alt or filename or media_type or "media"

        if self.include_urls and url:
            return f"[media: {label}]({url})\n"

        return f"[media: {label}]\n"

    def _format_adf_date(self, attrs: dict[str, Any]) -> str:
        timestamp = attrs.get("timestamp")

        if timestamp:
            try:
                ts = int(timestamp) / 1000
                return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
            except Exception:
                return str(timestamp)

        return ""


def adf_to_text(
    node: Any,
    *,
    include_urls: bool = True,
    include_media_placeholders: bool = True,
    include_status: bool = True,
    table_cell_separator: str = " | ",
) -> str:
    """
    Backward-compatible wrapper.

    Existing imports like this still work:

        from app.utils.adf import adf_to_text
    """

    converter = ADFTextConverter(
        include_urls=include_urls,
        include_media_placeholders=include_media_placeholders,
        include_status=include_status,
        table_cell_separator=table_cell_separator,
    )

    return converter.convert(node)