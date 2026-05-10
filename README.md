# WeeklyREBOT

`WeeklyREBOT` is an auto generation project based on JIRA task's comments in one week.

The purpose of this bot is to mainly retrieve user's comment, task's info from your task in one week and auto generate weekly report.

## Project Structure

```text
WeeklyREBOT/
├── app/
│   ├── api/
│   ├── bot/
│   ├── ingestion/
│   ├── llm/
│   ├── retrieval/
│   └── utils/
├── data/
│   ├── raw/
│   ├── processed/
│   └── indexes/
├── scripts/
├── tests/
├── .env # Store private api, double check if you want to push
├── requirements.txt
└── README.md # It's me

## Enviroment setup
Please make sure setup_env.sh executable:
```bash
chmod +x setup_env.sh
```
Then run it, and we are all set:
```bash
./setup_env.sh
```