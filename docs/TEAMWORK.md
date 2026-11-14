# Teamwork with Git and GitHub

## Rules

1. Nobody commits directly to `main`.
2. One task = one branch = one Pull Request (PR).
3. Every PR needs at least one review from another team member before merge.
4. Never commit `.env`, `.venv/` or `data/processed/`.

## Branches and task split (example for 4 people)

| Task | Branch | Files |
|---|---|---|
| API and Parquet | `feature-api-parquet` | `ingest_api.py`, `config.py` |
| Sales CSV and cleaning | `feature-sales-cleaning` | `make_sales_csv.py`, `clean_sales.py`, `schemas.py`, tests |
| PostgreSQL model and loading | `feature-postgres-model` | `sql/schema.sql`, `sql/queries.sql`, `load_db.py` |
| Pipeline runner, README, presentation | `feature-docs-runner` | `run_pipeline.py`, `README.md`, `docs/` |

If the team has a different size, merge or split rows, but keep one branch per task.

## Daily workflow

```bash
git switch main
git pull
git switch -c feature-your-task
# write code
git status
git add .
git commit -m "Add API ingestion to Parquet"
git push -u origin feature-your-task
```

Then open a Pull Request on GitHub: `feature-your-task` -> `main`.

## Commit messages

Short, in the imperative form, one idea per commit:
`Add price cleaning`, `Fix date parsing`, `Create orders table`.

## Pull Request description

Use the PR template (`.github/pull_request_template.md`): what was done, which files changed, how to test.

## Code review checklist

- [ ] The code runs: `python -m pytest tests -v` passes.
- [ ] No secrets, no `.venv`, no processed data in the commit.
- [ ] Names are clear; there are short comments for non-obvious decisions.
- [ ] Cleaning rules are explained in the code or README.
- [ ] SQL has primary keys, foreign keys and sensible constraints.
- [ ] The PR is small enough to review in 10-15 minutes.

Reviewer: leave comments on specific lines, then choose **Approve** or **Request changes**.
Author: fix the comments with new commits on the same branch and push again.

## Merge conflicts

1. `git switch main` and `git pull`.
2. `git switch feature-your-task` and `git merge main`.
3. Open the conflicted file, keep the correct version, delete `<<<<<<<`, `=======`, `>>>>>>>`.
4. `git add .`, `git commit -m "Resolve merge conflict"`, `git push`.

## After the merge

```bash
git switch main
git pull
```
