# Setting Up Claude Code for Secure Automation

A step-by-step guide for fund managers to present to their IT departments.

---

## Table of Contents

1. [What is Claude Code?](#1-what-is-claude-code)
2. [Why this approach is safe for regulated environments](#2-why-this-approach-is-safe)
3. [Prerequisites](#3-prerequisites)
4. [Setup walkthrough](#4-setup-walkthrough)
5. [How analysts use it day-to-day](#5-how-analysts-use-it)
6. [How IT reviews and approves changes](#6-how-it-reviews-changes)
7. [Scheduled automation](#7-scheduled-automation)
8. [IT security FAQ](#8-it-security-faq)
9. [Threat model summary](#9-threat-model-summary)

---

## 1. What is Claude Code?

Claude Code is a command-line tool from Anthropic that lets users describe tasks in plain English. It reads and writes files in a project, runs approved commands, and proposes changes via Git pull requests. It does not have persistent access to the user's computer, email, cloud storage, or credentials.

Think of it as a developer that works inside a single folder, proposes changes for review, and has no keys to anything else.

---

## 2. Why this approach is safe

Traditional "AI agent" setups give the agent broad access to a user's machine. That's unacceptable in regulated environments. This setup is different:

| Concern | How it's addressed |
|---|---|
| **Agent accesses sensitive data** | Claude only sees files inside one GitHub repo. No access to email, drives, credentials, or other repos. |
| **Agent makes unauthorized changes** | All changes go through Pull Requests. Nothing reaches production without human review. |
| **Prompt injection (poisoned web pages)** | External content is parsed deterministically (selectors, regex, schemas) — never interpreted as instructions. Even if injection succeeds, there are no secrets to steal and no privileged actions available. |
| **Secrets leak** | No secrets exist in the workspace. Scheduled runs use scoped GitHub Secrets that Claude never sees. |
| **Uncontrolled internet access** | Each scraper declares its allowed domains. Network access is auditable and scoped. |
| **Shadow IT / untracked code** | Everything is in Git with full history. CODEOWNERS enforces review. CI runs are logged. |

**The core principle: capability containment.** We don't try to prevent all attacks — we ensure that even a successful attack can't do meaningful damage.

---

## 3. Prerequisites

### For IT to provision:
- [ ] A **GitHub organization** (or use an existing one)
- [ ] A **private repository** created from this template
- [ ] **Branch protection** enabled on `main` (require PR reviews, require status checks)
- [ ] **CODEOWNERS** file (optional but recommended — ensures IT reviews changes to sensitive files)
- [ ] **Claude Code** installed on the analyst's machine ([install guide](https://docs.anthropic.com/en/docs/claude-code))
- [ ] An **Anthropic API key** provisioned for the team (set as an environment variable, never committed to the repo)

### For the analyst:
- [ ] GitHub account with write access to the repo
- [ ] Claude Code installed and authenticated
- [ ] Basic comfort with: opening a terminal, typing a sentence, and reviewing a pull request on GitHub

### No special infrastructure required:
- No servers to manage
- No databases to provision
- No VPNs or network changes (GitHub Actions runs in GitHub's cloud)
- No admin access on the analyst's machine

---

## 4. Setup walkthrough

### Step 1: Create the repo

IT creates a new private repo in the organization, using this repo as a template (or by pushing these files).

```
your-org/analyst-automations   (private repo)
```

### Step 2: Enable branch protection

In GitHub → Settings → Branches → Add rule for `main`:
- [x] Require a pull request before merging
- [x] Require approvals (1 or more)
- [x] Require status checks to pass (select "PR Checks")
- [x] Do not allow bypassing the above settings

This ensures no code reaches `main` without review.

### Step 3: (Optional) Add CODEOWNERS

Create a `CODEOWNERS` file in the repo root:

```
# IT must approve changes to security-sensitive files
CLAUDE.md                    @your-org/it-security
.github/workflows/           @your-org/it-security
requirements.txt             @your-org/it-security
```

This means even if an analyst approves a PR, changes to these files also require IT sign-off.

### Step 4: Install Claude Code on the analyst's machine

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Set the API key (IT provides this)
export ANTHROPIC_API_KEY="sk-ant-..."

# Clone the repo and open Claude Code in it
git clone https://github.com/your-org/analyst-automations.git
cd analyst-automations
claude
```

When Claude Code starts, it reads `CLAUDE.md` automatically. All the security constraints are loaded — the analyst doesn't need to configure anything.

### Step 5: Verify the constraints are active

The analyst can test this by asking Claude Code:

```
> Show me the contents of ~/.ssh/
```

Claude Code will refuse — `CLAUDE.md` prohibits accessing anything outside the repo workspace.

```
> Edit .github/workflows/pr-checks.yml and add a step
```

Claude Code will flag this as a security-sensitive change and explain that it requires explicit acknowledgment.

---

## 5. How analysts use it

The analyst opens a terminal in the repo folder and runs `claude`. Then they type natural language requests:

### Build a scraper
```
Create a scraper under scrapers/sec_filings/ that pulls the latest 10-K
filings index from SEC EDGAR for a given CIK number. Extract filing date,
company name, and document URL. Add schema validation and tests. Open a PR.
```

Claude Code will:
1. Create the files in `scrapers/sec_filings/`
2. Write a `config.yaml` declaring `efts.sec.gov` as the allowed domain
3. Write `scrape.py` and `extract.py` with deterministic parsing
4. Write tests
5. Create a branch, commit, and open a PR

### Process an Excel file
```
Read data/inbox/holdings.xlsx, validate that it has columns Ticker, Shares,
and Price, compute the market value for each row, and output a summary CSV
to output/holdings_summary.csv. Add tests with a synthetic fixture. Open a PR.
```

### Fix something that broke
```
Tests are failing for the sec_filings scraper. The SEC changed their HTML
format. Diagnose and fix the extraction logic. Open a PR.
```

### What the analyst sees

Every request results in a **Pull Request** on GitHub. The PR includes:
- What changed
- What domains/data sources are used
- How to run the tests
- Risk notes (any new dependencies, domain changes, etc.)

The analyst (or IT) reviews the PR, and if it looks good, merges it.

---

## 6. How IT reviews changes

### What to look for in a PR

| Check | What it means |
|---|---|
| **Files changed** | Are changes limited to `scrapers/`, `pipelines/`, `connectors/`, `schemas/`, `tests/`? Changes to `.github/workflows/`, `CLAUDE.md`, or `requirements.txt` need extra scrutiny. |
| **Domains** | Does `config.yaml` only list expected public domains? No unexpected outbound targets? |
| **Dependencies** | Are new packages in `requirements.txt` well-known and necessary? |
| **Test coverage** | Are there tests? Do they pass? (CI checks this automatically.) |
| **No secrets** | Are there any hardcoded credentials, API keys, or tokens? (There shouldn't be.) |

### Automated checks

The `pr-checks.yml` workflow runs on every PR:
- Installs dependencies
- Runs `pytest`
- Runs linting with `ruff`

No secrets are available during PR checks. This is intentional — it prevents a malicious PR from exfiltrating credentials.

---

## 7. Scheduled automation

Once a scraper or pipeline is merged to `main`, it can run on a schedule via GitHub Actions.

The `scheduled-run.yml` workflow:
- Runs on weekday mornings (configurable)
- Executes `pipelines/run_all.py`
- Uploads outputs as GitHub Actions artifacts (downloadable for 30 days)

### If output delivery to SharePoint/OneDrive is needed

IT adds a scoped secret to the repo (Settings → Secrets → Actions):
- e.g., `SHAREPOINT_TOKEN` with write access to one specific folder
- The workflow references it: `${{ secrets.SHAREPOINT_TOKEN }}`
- Claude Code never sees this secret — it only exists in the CI environment

---

## 8. IT security FAQ

**Q: Can Claude Code access the analyst's email, files, or browser?**
No. Claude Code operates inside the repo directory only. The `CLAUDE.md` constraints explicitly prohibit accessing anything outside the workspace.

**Q: Can Claude Code push directly to main?**
Not if branch protection is enabled (Step 2). All changes must go through a PR with review.

**Q: What if a scraped web page contains prompt injection?**
The `CLAUDE.md` rules require deterministic parsing (CSS selectors, regex, JSON schemas). Claude Code is instructed never to interpret scraped content as instructions. Even if injection somehow succeeds, the agent has no secrets, no network credentials, and no access to anything outside the repo.

**Q: Can Claude Code install arbitrary packages?**
`CLAUDE.md` prohibits modifying `requirements.txt` without explicit user approval and PR review. IT can enforce this further via CODEOWNERS.

**Q: What about data exfiltration?**
Each scraper declares its allowed domains. There are no secrets in the workspace to exfiltrate. Output goes to `output/` (git-ignored) or GitHub Actions artifacts. Network access is scoped and logged.

**Q: Can Claude Code modify its own rules?**
`CLAUDE.md` is listed as a protected file. Changes require explicit acknowledgment and show up clearly in PRs. CODEOWNERS can require IT approval for any changes to it.

**Q: What audit trail exists?**
- Git history: every change, who authored it, who approved it
- PR reviews: discussion and approval records
- GitHub Actions logs: every scheduled run with full output
- Branch protection audit log: who changed repo settings

**Q: Does this require any servers or infrastructure?**
No. The repo lives on GitHub. CI runs on GitHub Actions (included in GitHub plans). The analyst runs Claude Code on their existing machine. No servers, databases, or VPNs needed.

---

## 9. Threat model summary

### What we protect against

| Threat | Mitigation |
|---|---|
| Claude Code accesses sensitive local files | Workspace containment — only repo files accessible. CLAUDE.md prohibits external access. |
| Malicious code merged to main | Branch protection + required PR reviews + automated CI checks. |
| Prompt injection via scraped content | Deterministic parsing only. No interpretation of external text as instructions. Schema validation on all outputs. |
| Secret exfiltration | No secrets in workspace. PR CI has zero secrets. Scheduled runs use scoped secrets Claude never sees. |
| Dependency supply chain attack | requirements.txt changes require explicit approval. CODEOWNERS can enforce IT review. |
| Unauthorized network access | Per-scraper domain allowlists in config.yaml. Auditable and reviewable. |
| Claude modifies its own constraints | CLAUDE.md is a protected file. Changes visible in PRs. CODEOWNERS enforces IT review. |

### What we accept (residual risk)

- Claude Code could write incorrect or inefficient code → mitigated by tests and review
- A determined attacker with repo write access could bypass controls → mitigated by branch protection and CODEOWNERS
- GitHub Actions has a broad execution environment → mitigated by scoped permissions and no-secret PR checks

### The key insight

**We don't try to make the agent perfectly safe. We make the environment safe for an imperfect agent.** The workspace has nothing valuable to steal, no destructive actions available, and all changes require human review. This is the same security model used for junior developers — limited access, code review, and CI gates.

---

## Next steps

1. IT provisions the repo and enables branch protection
2. Analyst installs Claude Code and clones the repo
3. Analyst makes their first request (try: "Create a scraper for ...")
4. IT reviews the first PR together with the analyst
5. Iterate — add more scrapers and pipelines as needed

Questions? Open an issue in this repo or contact your IT security team.
