from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def adf_to_text(
    node: Any,
    *,
    include_urls: bool = True,
    include_media_placeholders: bool = True,
    include_status: bool = True,
    table_cell_separator: str = " | ",
) -> str:
    """
    Convert Atlassian Document Format JSON into readable plain text.

    Designed to be defensive and MVP-friendly while supporting most common ADF nodes.

    Args:
        node:
            ADF node, list of nodes, string, or None.
        include_urls:
            Whether to append URLs for links, inline cards, media, etc.
        include_media_placeholders:
            Whether to include placeholders like [media: filename].
        include_status:
            Whether to include status lozenges as text.
        table_cell_separator:
            Separator used between table cells.
    Returns:
        Plain text representation of the ADF document.
    """

    def normalize(text: str) -> str:
        # Keep intentional newlines, but trim trailing whitespace per line.
        lines = [line.rstrip() for line in text.splitlines()]
        return "\n".join(lines).strip()

    def join_blocks(parts: list[str]) -> str:
        cleaned = [part.strip("\n") for part in parts if part and part.strip()]
        return "\n".join(cleaned)

    def walk(value: Any, *, list_depth: int = 0, ordered_index: int | None = None) -> str:
        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, list):
            return "".join(
                walk(child, list_depth=list_depth, ordered_index=ordered_index)
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
            return join_blocks([walk(child) for child in content]) + "\n"

        if node_type in {
            "layoutSection",
            "layoutColumn",
            "bodiedExtension",
            "extension",
            "nestedExpand",
            "expand",
        }:
            title = attrs.get("title") or attrs.get("text")
            body = join_blocks([walk(child) for child in content])
            if title and body:
                return f"{title}\n{body}\n"
            if title:
                return f"{title}\n"
            return body + ("\n" if body else "")

        # -------------------------
        # Text and inline nodes
        # -------------------------
        if node_type == "text":
            text = value.get("text", "")

            if include_urls:
                href = None
                for mark in marks:
                    if mark.get("type") == "link":
                        href = (mark.get("attrs") or {}).get("href")
                        break

                if href and href not in text:
                    text = f"{text} ({href})"

            return text

        if node_type == "hardBreak":
            return "\n"

        if node_type == "mention":
            return attrs.get("text") or attrs.get("displayName") or attrs.get("id") or ""

        if node_type == "emoji":
            return attrs.get("shortName") or attrs.get("text") or attrs.get("id") or ""

        if node_type == "date":
            timestamp = attrs.get("timestamp")
            if timestamp:
                try:
                    # ADF date timestamp is usually milliseconds.
                    ts = int(timestamp) / 1000
                    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
                except Exception:
                    return str(timestamp)
            return ""

        if node_type == "status":
            if not include_status:
                return ""
            text = attrs.get("text") or ""
            color = attrs.get("color")
            return f"[{text}]" if text else (f"[status: {color}]" if color else "")

        if node_type == "inlineCard":
            url = attrs.get("url")
            data = attrs.get("data") or {}
            title = (
                data.get("name")
                or data.get("title")
                or data.get("text")
                or attrs.get("title")
                or url
            )
            if include_urls and url and title and title != url:
                return f"{title} ({url})"
            return title or ""

        if node_type == "placeholder":
            return attrs.get("text", "")

        # -------------------------
        # Blocks
        # -------------------------
        if node_type == "paragraph":
            text = walk(content, list_depth=list_depth)
            return text + ("\n" if text else "")

        if node_type == "heading":
            level = attrs.get("level", 1)
            text = walk(content, list_depth=list_depth).strip()
            if not text:
                return ""
            return f"{'#' * max(1, min(int(level), 6))} {text}\n"

        if node_type == "blockquote":
            text = normalize(walk(content, list_depth=list_depth))
            if not text:
                return ""
            return "\n".join(f"> {line}" if line else ">" for line in text.splitlines()) + "\n"

        if node_type == "codeBlock":
            language = attrs.get("language")
            code = walk(content, list_depth=list_depth).rstrip("\n")
            if language:
                return f"```{language}\n{code}\n```\n"
            return f"```\n{code}\n```\n"

        if node_type == "rule":
            return "---\n"

        if node_type == "panel":
            panel_type = attrs.get("panelType")
            text = normalize(walk(content, list_depth=list_depth))
            if not text:
                return ""
            prefix = f"[{panel_type}] " if panel_type else ""
            return f"{prefix}{text}\n"

        # -------------------------
        # Lists
        # -------------------------
        if node_type == "bulletList":
            return "".join(walk(child, list_depth=list_depth + 1) for child in content)

        if node_type == "orderedList":
            start = attrs.get("order", attrs.get("start", 1))
            try:
                start = int(start)
            except Exception:
                start = 1

            parts = []
            for index, child in enumerate(content, start=start):
                parts.append(
                    walk(
                        child,
                        list_depth=list_depth + 1,
                        ordered_index=index,
                    )
                )
            return "".join(parts)

        if node_type == "listItem":
            text = normalize(walk(content, list_depth=list_depth))
            if not text:
                return ""

            indent = "  " * max(0, list_depth - 1)
            bullet = f"{ordered_index}." if ordered_index is not None else "-"
            lines = text.splitlines()

            first = f"{indent}{bullet} {lines[0]}"
            rest = [
                f"{indent}  {line}" if line else ""
                for line in lines[1:]
            ]

            return "\n".join([first, *rest]) + "\n"

        # -------------------------
        # Tasks and decisions
        # -------------------------
        if node_type == "taskList":
            return "".join(walk(child, list_depth=list_depth) for child in content)

        if node_type == "taskItem":
            state = attrs.get("state")
            checkbox = "[x]" if state == "DONE" else "[ ]"
            text = normalize(walk(content, list_depth=list_depth))
            return f"{checkbox} {text}\n" if text else f"{checkbox}\n"

        if node_type == "decisionList":
            return "".join(walk(child, list_depth=list_depth) for child in content)

        if node_type == "decisionItem":
            text = normalize(walk(content, list_depth=list_depth))
            return f"Decision: {text}\n" if text else ""

        # -------------------------
        # Tables
        # -------------------------
        if node_type == "table":
            rows = [walk(child, list_depth=list_depth).rstrip("\n") for child in content]
            rows = [row for row in rows if row.strip()]
            return "\n".join(rows) + ("\n" if rows else "")

        if node_type == "tableRow":
            cells = []
            for child in content:
                cell_text = normalize(walk(child, list_depth=list_depth))
                cell_text = " ".join(cell_text.splitlines())
                cells.append(cell_text)
            return table_cell_separator.join(cells) + "\n"

        if node_type in {"tableCell", "tableHeader"}:
            return walk(content, list_depth=list_depth)

        # -------------------------
        # Media / files
        # -------------------------
        if node_type == "mediaSingle":
            return walk(content, list_depth=list_depth)

        if node_type == "mediaGroup":
            return "".join(walk(child, list_depth=list_depth) for child in content)

        if node_type == "media":
            if not include_media_placeholders:
                return ""

            media_type = attrs.get("type")
            alt = attrs.get("alt")
            filename = attrs.get("fileName") or attrs.get("filename") or attrs.get("name")
            url = attrs.get("url")

            label = alt or filename or media_type or "media"

            if include_urls and url:
                return f"[media: {label}] ({url})\n"

            return f"[media: {label}]\n"

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
            return walk(content, list_depth=list_depth)

        # -------------------------
        # Fallback:
        # If the node has content, recursively parse it.
        # If not, try useful attrs.
        # -------------------------
        if content:
            return walk(content, list_depth=list_depth)

        for key in ("text", "title", "name", "label", "url", "id"):
            if attrs.get(key):
                return str(attrs[key])

        return ""

    return normalize(walk(node))
