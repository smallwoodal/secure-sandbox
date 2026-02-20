# Secure Sandbox

A template repo for using Claude Code securely in regulated environments.

**How it works:** Users describe tasks in plain English. Claude Code writes the code, adds tests, and opens a Pull Request. Nothing goes live without review. Scheduled execution runs in GitHub Actions.

**Why it's safe:** The workspace has no secrets. Permission rules block access to sensitive files and deny destructive commands. All changes require PR review. Same security model as onboarding a junior developer — limited access, code review, CI gates.

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

Then describe what you need in plain English. Claude Code will write the code, add tests, and open a PR for review.

## Repo structure

```
src/            Application code
tests/          Test suite
data/inbox/     Drop input files here (gitignored)
output/         Generated outputs (gitignored)
ops/            Tutorial, IT checklist
CLAUDE.md       Behavioral rules (loaded automatically)
.claude/        Sandbox and permission settings
CODEOWNERS      Requires IT review for security-sensitive files
```
