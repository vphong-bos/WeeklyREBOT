import argparse
from datetime import date
from pathlib import Path

from app.bot.weekly_bot import WeeklyReportBot
from app.utils.config import get_settings
from app.utils.dates import get_previous_week_range

VALID_MODES = {"report", "prompt"}
VALID_LLM_PROVIDERS = {"huggingface", "template"}

def parse_args():
    parser = argparse.ArgumentParser(
        prog="generate_weekly_report.py",
        description="Generate a weekly report or an LLM prompt from Jira comments.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  # Generate report for previous week using Hugging Face LLM by default
  python scripts/generate_weekly_report.py

  # Generate report for a specific week
  python scripts/generate_weekly_report.py --start 2026-05-04 --end 2026-05-10

  # Generate report with custom output path
  python scripts/generate_weekly_report.py --start 2026-05-04 --end 2026-05-10 --output-path data/processed/my_report.md

  # Generate report with custom Hugging Face model
  python scripts/generate_weekly_report.py --llm-provider huggingface --hf-model Qwen/Qwen2.5-7B-Instruct

  # Generate report without external LLM, using template fallback
  python scripts/generate_weekly_report.py --llm-provider template

  # Only create a prompt from retrieved Jira info, not the final report
  python scripts/generate_weekly_report.py --mode prompt --start 2026-05-04 --end 2026-05-10 --output-path data/processed/weekly_prompt.md

  # Print result to terminal instead of writing file
  python scripts/generate_weekly_report.py --mode prompt --stdout
        """,
    )

    parser.add_argument(
        "--start",
        help="Week start date, format YYYY-MM-DD. If omitted, previous week is used.",
    )
    parser.add_argument(
        "--end",
        help="Week end date, format YYYY-MM-DD. If omitted, previous week is used.",
    )
    parser.add_argument(
        "--output-path",
        help=(
            "Output markdown file path. "
            "For report mode, default is REPORT_OUTPUT_PATH from .env. "
            "For prompt mode, default is PROMPT_OUTPUT_PATH from .env."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=sorted(VALID_MODES),
        default="prompt",
        help=(
            "Generation mode."
            "  report: generate final weekly report. Uses Hugging Face by default."
            "  prompt: only create a prompt from retrieved Jira comments and descriptions."
        ),
    )
    parser.add_argument(
        "--llm-provider",
        choices=sorted(VALID_LLM_PROVIDERS),
        default="huggingface",
        help=(
            "LLM provider for --mode report."
            "  huggingface: use Hugging Face Inference API. Default."
            "  template: no external LLM, use rule-based markdown fallback."
        )
    )
    parser.add_argument(
        "--hf-model",
        help="Override HF_MODEL from .env for this run.",
    )
    parser.add_argument(
        "--hf-api-token",
        help="Override HF_API_TOKEN from .env for this run. Avoid using this in shell history if possible.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print output to terminal instead of writing to file.",
    )
    return parser.parse_args()


def resolve_week_range(args) -> tuple[date, date]:
    if bool(args.start) != bool(args.end):
        raise ValueError("Please provide both --start and --end, or omit both.")

    if args.start and args.end:
        return date.fromisoformat(args.start), date.fromisoformat(args.end)

    return get_previous_week_range()


def resolve_output_path(args) -> Path:
    if args.output_path:
        return Path(args.output_path)

    today = date.today().isoformat()

    if args.mode == "prompt":
        return Path(f"data/prompt/weekly_prompt_{today}.txt")

    return Path(f"data/processed/weekly_report_{today}.md")


def write_output(content: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def print_retrieved_comments(report_items: list[dict]) -> None:
    retrieved_count = 0

    for item in report_items:
        for comment in item["comments"]:
            retrieved_count += 1
            print(f"[Retrieved {retrieved_count}]")
            print(f"Issue: {item['issue_key']} - {item['summary']}")
            print(f"Status: {item['status']}")
            print(f"Comment ID: {comment.get('id', 'unknown')}")
            print(f"Created: {comment.get('created', 'unknown')}")
            print("Comment:")
            print(comment.get("body_text", "").strip() or "(empty)")
            print()

    print(f"Total comments retrieved: {retrieved_count}")


def main():
    args = parse_args()
    settings = get_settings()
    week_start, week_end = resolve_week_range(args)

    bot = WeeklyReportBot(settings)
    report_items = bot.collect_report_items(week_start, week_end)
    print_retrieved_comments(report_items)

    if args.mode == "report":
        if args.llm_provider == "huggingface":
            content = bot.generate_with_huggingface_from_items(
                week_start,
                week_end,
                report_items,
                model=args.hf_model,
            )
        elif args.llm_provider == "template":
            content = bot.generate_template_from_items(week_start, week_end, report_items)
        else:
            raise ValueError(f"Unsupported llm_provider: {args.llm_provider}")
    elif args.mode == "prompt":
        content = bot.generate_prompt_from_items(week_start, week_end, report_items)
    else:
        raise ValueError(f"Unsupported mode: {args.mode}")

    if args.stdout:
        print(content)
        return

    output_path = resolve_output_path(args)
    write_output(content, output_path)

    print(f"Generated {args.mode}: {output_path}")


if __name__ == "__main__":
    main()
