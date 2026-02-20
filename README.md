# Secure Sandbox

A template repo for using Claude Code to build web scrapers and Excel automation in regulated environments.

**How it works:** An analyst describes a task in plain English. Claude Code writes the code, adds tests, and opens a Pull Request. Nothing goes live without review. Scheduled execution runs in GitHub Actions.

**Why it's safe:** The workspace has no secrets, the filesystem sandbox blocks access to sensitive files, dangerous commands are denied, and all changes require PR review. Same security model as onboarding a junior developer — limited access, code review, CI gates.

## Getting started

- **Fund managers / analysts:** Read [`ops/tutorial.md`](ops/tutorial.md) for the full walkthrough
- **IT teams:** Start with [`ops/it-checklist.md`](ops/it-checklist.md) for setup steps
- **Security review:** See the three-layer security model in the tutorial and the constraints in [`CLAUDE.md`](CLAUDE.md)

## Quick start (after IT setup is complete)

```bash
git clone https://github.com/your-org/your-sandbox-repo.git
cd your-sandbox-repo
claude
```

Then describe what you need:

```
Create a scraper for SEC EDGAR that pulls the latest 10-K filings index.
Extract filing date, company name, and document URL. Add tests. Open a PR.
```

## Repo structure

```
scrapers/       Fetch and parse data from websites
pipelines/      Orchestration and scheduling logic
connectors/     Excel read/write, storage integrations
schemas/        JSON schemas for output validation
data/inbox/     Drop Excel files here (gitignored)
output/         Generated outputs (gitignored)
ops/            Tutorial, IT checklist, runbooks
tests/          Test suite
```
