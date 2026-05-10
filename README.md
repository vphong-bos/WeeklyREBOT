<p align="center">
  <img src="assets/logo.png" alt="WeeklyREBOT Logo" width="200" height="200">
</p>

# WeeklyREBOT

`WeeklyREBOT` generates a weekly report from Jira issue data and the comments you wrote during a selected week.

The current flow is:
1. Search candidate Jira issues in the selected date window.
2. Fetch issue comments.
3. Filter comments by retrieval mode and selected week.
4. Extract issue metadata such as issue link, status, and start/due fields.
5. Build either a prompt, a template report, or a Hugging Face generated report.

## Project Structure

```text
WeeklyREBOT/
├── assets/
│   └── logo.png
├── app/
│   ├── api/                  # Reserved package for future API integrations
│   ├── bot/                  # High-level orchestration for weekly report generation
│   ├── ingestion/            # Jira client and data fetching
│   ├── llm/                  # Prompt building and Hugging Face generation
│   ├── retrieval/            # Comment filtering and retrieval logic
│   ├── utils/                # Shared helpers such as config, dates, and ADF parsing
│   └── main.py               # App entrypoint module
├── data/
│   ├── raw/                  # Optional raw output storage
│   ├── processed/            # Generated markdown reports
│   ├── prompt/               # Generated prompt text files
│   └── indexes/              # Reserved for future indexing/search use
├── scripts/
│   └── cli.py                # Command-line interface used to run the project
├── tests/                    # Unit tests for retrieval and ADF conversion
├── .env                      # Local secrets and runtime configuration
├── .env.example              # Example environment variables
├── requirements.txt          # Python dependencies
├── setup_env.sh              # Environment bootstrap script
└── README.md
```

## Key Files
- `app/ingestion/jira_client.py`: talks to Jira, caches Jira field metadata, searches candidate issues, and fetches paginated comments.
- `app/retrieval/comment_filter.py`: defines retrieval modes and filters comments by author, mentions, reply status, and week range.
- `app/utils/adf.py`: converts Jira ADF comment/description content into readable plain text.
- `app/utils/dates.py`: parses Jira timestamps and resolves weekly date ranges.
- `app/utils/config.py`: loads runtime settings from `.env`.
- `app/bot/weekly_bot.py`: coordinates Jira retrieval, enriches issues with links and time fields, and transforms them into report items.
- `app/llm/generator.py`: creates Confluence-style prompt and template output from retrieved Jira items.
- `app/llm/hf_client.py`: runs Hugging Face text generation for final report mode.
- `scripts/cli.py`: main command you run from the terminal and prints retrieved comment details before generating output.
- `tests/test_comment_filter.py`: retrieval filter tests.
- `tests/test_adf.py`: ADF-to-text conversion tests.

## Environment Setup
Please make sure setup_env.sh executable:
```bash
chmod +x setup_env.sh
```

Then run it:
```bash
./setup_env.sh
```

If you prefer to set things up manually, install dependencies from `requirements.txt` in your virtual environment.

## Configuration
Create a `.env` file from `.env.example` and fill in your Jira and Hugging Face credentials.

Important variables used by the current code:
- `JIRA_BASE_URL`: your Jira site URL, for example `https://your-company.atlassian.net`
- `JIRA_EMAIL`: Jira login email
- `JIRA_API_TOKEN`: Jira API token used by the client
- `JIRA_ACCOUNT_ID`: the Jira account ID whose comments should be included
- `JIRA_PROJECT_KEYS`: optional comma-separated project keys, for example `AISW,OJT`
- `HF_API_TOKEN`: Hugging Face token
- `HF_MODEL`: model name used for report generation
- `HF_DEVICE`: device setting for Transformers, default is `auto`
- `HF_MAX_NEW_TOKENS`: max generated tokens
- `HF_TEMPERATURE`: generation temperature

Note:
- The code reads `JIRA_API_TOKEN`, not `JIRA_API_KEY`.
- `JIRA_PROJECT_KEYS` can be left empty to search across all accessible projects.

## How To Run
Run from the `WeeklyREBOT` directory.

Generate a prompt for the previous week:
```bash
python -m scripts.cli
```

Note:
- The current default mode is `prompt`.
- To generate a final report, pass `--mode report`.
- The current default retrieval mode is `member`.

Generate a prompt for a custom week:
```bash
python -m scripts.cli --start 2026-05-04 --end 2026-05-10
```

Generate a prompt only:
```bash
python -m scripts.cli --mode prompt --start 2026-05-04 --end 2026-05-10
```

Generate a final report:
```bash
python -m scripts.cli --mode report --start 2026-05-04 --end 2026-05-10
```

Use template mode instead of Hugging Face:
```bash
python -m scripts.cli --mode report --llm-provider template
```

Use `member` retrieval mode:
```bash
python -m scripts.cli --retrieval-mode member --mode prompt --start 2026-05-04 --end 2026-05-10
```

Use `leader` retrieval mode:
```bash
python -m scripts.cli --retrieval-mode leader --mode prompt --start 2026-05-04 --end 2026-05-10
```

Retrieval mode behavior:
- `member`: keeps comments authored by `JIRA_ACCOUNT_ID`
- `leader`: keeps comments that mention `JIRA_ACCOUNT_ID` in the Jira comment body

Print the generated output to the terminal:
```bash
python -m scripts.cli --mode prompt --stdout
```

Write to a custom output path:
```bash
python -m scripts.cli --start 2026-05-04 --end 2026-05-10 --output-path data/processed/my_report.md
```

## Current Retrieval Logic
- Candidate issues are searched by `JIRA_PROJECT_KEYS` and issue `updated` date range.
- All comments for each candidate issue are fetched with pagination.
- Comments are filtered through `retrieve_comments(...)` in `app/retrieval/comment_filter.py`.
- The default retrieval mode is `member`, which keeps only comments authored by `JIRA_ACCOUNT_ID`.
- A `leader` retrieval mode also exists in the filter module for mention-based retrieval.
- Reply-style comments can be excluded by the filter configuration.
- Only comments whose `created` timestamp falls inside the selected week are kept.
- Jira ADF content is converted to plain text before prompt/report generation.
- Empty comment bodies are skipped.
- Issue start/due fields are resolved from Jira metadata when available.

## Output
- Report mode writes markdown to `data/processed/` by default.
- Prompt mode writes text to `data/prompt/` by default.
- The CLI also prints the retrieved comment details and final retrieved comment count during execution.
