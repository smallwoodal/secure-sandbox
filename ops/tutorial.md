# Setting Up Claude Code for Secure Automation

A guide for fund managers to present to their IT departments.

---

## What is Claude Code?

A command-line tool from Anthropic. Users describe tasks in plain English — Claude writes code, adds tests, and opens a Pull Request. Think of it as a developer that works inside a single folder, proposes changes for review, and has no keys to anything else.

---

## Why this is safe for regulated environments

**The core principle:** we don't try to make the agent perfectly safe. We make the environment safe for an imperfect agent.

| Concern | How it's addressed |
|---|---|
| Agent accesses sensitive data | OS-level sandbox blocks access to SSH keys, AWS credentials, and other sensitive files on the machine. |
| Agent makes unauthorized changes | All changes go through Pull Requests. Nothing reaches production without human review. |
| Prompt injection (poisoned web pages) | Even if injection succeeds, there are no secrets to steal, dangerous commands are denied, and nothing deploys without PR review. |
| Secrets leak | No secrets exist in the workspace. Scheduled CI runs use scoped GitHub Secrets that Claude never sees. |
| Internet access | Analysts already have internet on their machines — Claude is no different. Security comes from having nothing to exfiltrate, not blocking the network. |
| Untracked code | Everything is in Git. CODEOWNERS enforces review. CI runs are logged. Full audit trail. |

### The three security layers

No single layer is sufficient alone.

| Layer | What it does | Enforcement |
|---|---|---|
| **CLAUDE.md** | Behavioral rules: PR-only workflow, deterministic parsing, don't access secrets | **Advisory** — Claude follows these but nothing technically prevents violation |
| **GitHub controls** | Branch protection, CODEOWNERS, required reviews, CI checks | **Enforced by GitHub** — no code reaches `main` without review |
| **Claude Code sandbox** | OS-level filesystem restrictions, dangerous commands denied | **Enforced at OS level** — IT deploys managed settings the analyst can't override |

**CLAUDE.md alone is not enough.** All three layers must be active. See [`it-checklist.md`](it-checklist.md) for setup.

---

## Setup (6 steps)

### 1. Create the repo

IT creates a private repo in the org from this template.

### 2. Enable branch protection

GitHub → Settings → Branches → Add rule for `main`:
- [x] Require a pull request before merging
- [x] Require at least 1 approval
- [x] Require status checks to pass ("PR Checks")
- [x] Do not allow bypassing the above settings

### 3. Add CODEOWNERS

Create `CODEOWNERS` in the repo root:

```
CLAUDE.md                    @your-org/it-security
.claude/**                   @your-org/it-security
.github/workflows/           @your-org/it-security
requirements.txt             @your-org/it-security
CODEOWNERS                   @your-org/it-security
```

This is a hard control, not optional. It protects itself — can't be silently modified.

### 4. Deploy managed sandbox settings

**This is the most important step.** Place this file on the analyst's machine via MDM (Jamf, Intune, etc.). It cannot be overridden.

**macOS:** `/Library/Application Support/ClaudeCode/managed-settings.json`
**Linux:** `/etc/claude-code/managed-settings.json`

```json
{
  "permissions": {
    "deny": [
      "Bash(rm -rf *)",
      "Bash(curl * | bash)",
      "Bash(wget * | bash)",
      "Bash(pip install *)",
      "Bash(git push --force *)",
      "Bash(git push origin main)",
      "Bash(git push origin master)",
      "Bash(git remote add *)",
      "Bash(git remote set-url *)",
      "Bash(git config *)"
    ]
  },
  "sandbox": {
    "filesystem": {
      "deniedPaths": [
        "~/.ssh",
        "~/.aws",
        "~/.config",
        "~/.env",
        "~/.gnupg",
        "~/.claude/memory"
      ]
    }
  }
}
```

**Why no network restrictions?** Analysts already have unrestricted internet on their machines. Restricting Claude's web access adds friction without security benefit — the workspace has no secrets and nothing deploys without review.

### 5. Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
export ANTHROPIC_API_KEY="sk-ant-..."   # IT provides this
git clone https://github.com/your-org/your-sandbox.git
cd your-sandbox
claude
```

### 6. Verify

Test the sandbox is working:

```
> Show me the contents of ~/.ssh/
```

Should be blocked at the OS level. If it's not, managed settings aren't active — go back to step 4.

---

## How analysts use it

Open a terminal in the repo, run `claude`, and describe what you need:

**Build a scraper:**
```
Create a scraper under scrapers/treasury_rates/ that pulls daily yield
curve rates from treasury.gov. Add schema validation and tests. Open a PR.
```

**Process Excel:**
```
Read data/inbox/holdings.xlsx, validate columns Ticker/Shares/Price,
compute market value per row, output to output/holdings_summary.csv.
Add tests with a synthetic fixture. Open a PR.
```

**Fix a broken scraper:**
```
Tests are failing for the treasury_rates scraper. Diagnose and fix. Open a PR.
```

Every request produces a Pull Request with a diff, test results, and risk notes. Review it, merge it, done.

---

## How IT reviews PRs

| Check | What to look for |
|---|---|
| Files changed | Scoped to `scrapers/`, `pipelines/`, `connectors/`, `schemas/`, `tests/`? Changes to protected files trigger CODEOWNERS review automatically. |
| Domains | Does `config.yaml` list only expected public domains? |
| Dependencies | New packages in `requirements.txt`? Well-known and necessary? |
| Tests | Do they exist? Do they pass? (CI checks automatically.) |
| Secrets | Any hardcoded keys or tokens? (There shouldn't be.) |

---

## Scheduled runs

Once merged to `main`, scrapers can run on a schedule via GitHub Actions. The `scheduled-run.yml` workflow runs weekday mornings and uploads outputs as downloadable artifacts.

If output delivery to SharePoint/OneDrive is needed, IT adds scoped secrets to the repo (Settings → Secrets → Actions). Claude Code never sees these — they only exist in CI.

---

## IT security FAQ

**Q: Can Claude Code access the analyst's email, files, or credentials?**
Claude Code can technically access files on the machine. That's why managed settings are critical — they block sensitive paths (~/.ssh, ~/.aws, ~/.env) at the OS level. Without the sandbox, protection is advisory only. With it, access is physically blocked.

**Q: Can Claude push directly to main?**
Branch protection prevents this. Claude can push to feature branches and open PRs — it cannot push to `main`.

**Q: What about prompt injection?**
We assume it will happen. The defense is: even if injection succeeds, there are no secrets to steal, dangerous commands are denied, sensitive files are blocked by the sandbox, and nothing deploys without human review of the PR.

**Q: Claude has internet access — isn't that risky?**
The analyst already has internet access on the same machine. Claude fetching a webpage is no different from the analyst opening it in a browser. Security comes from having nothing to exfiltrate, not from blocking the network.

**Q: What's the audit trail?**
Git history (every change + who approved it), PR review records, GitHub Actions logs (every scheduled run), branch protection audit log.

**Q: What infrastructure is required?**
None. GitHub repo + GitHub Actions (included in GitHub plans) + Claude Code on the analyst's machine. No servers, databases, or VPNs.

---

## The pitch to IT (one paragraph)

This doesn't make the AI agent safe. It makes the environment safe for an imperfect agent. The workspace has nothing valuable to steal. Dangerous commands are blocked at the OS level. All code changes require human review before they go live. It's the same security model you use for junior developers — limited access, code review, and CI gates. The difference is this developer works 100x faster and never forgets to write tests.
