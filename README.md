# Citizenship Search App (Restart)

Clean restart of the discovery-first research app, rebuilt with a simpler architecture and GitHub-first workflow.

## What this version does

- Stores one investigation case with person aliases and evidence claims.
- Tracks conflicting facts (for example, father name variants).
- Produces a discovery report and archive request checklist.
- Keeps non-English source text and an English translation copy side-by-side.
- Preserves source provenance for each claim.

## Quick start

```bash
cd /Users/paulevans/Projects/citizenship-search-app
PYTHONPATH=src python3 -m citizenship_search.cli --query "Roman Senus Stryj 1957"
```

## Run the local web app

```bash
cd /Users/paulevans/Projects/citizenship-search-app
PYTHONPATH=src python3 -m citizenship_search.web
```

Then open `http://127.0.0.1:8000` in your browser.

## Run tests

```bash
cd /Users/paulevans/Projects/citizenship-search-app
PYTHONPATH=src python3 -m pytest -q
```

## Important

- This tool supports archival research workflows.
- It does not provide legal advice.
