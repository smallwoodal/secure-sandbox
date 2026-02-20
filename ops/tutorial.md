# Setting Up Claude Code in a Secure Sandbox

A guide for teams to present to their IT departments.

---

## What is Claude Code?

A command-line tool from Anthropic. Users describe tasks in plain English — Claude writes code, adds tests, and opens a Pull Request. Think of it as a developer that works inside a single folder, proposes changes for review, and has no keys to anything else.

---

## Why this is safe for regulated environments

**The core principle:** we don't try to make the agent perfectly safe. We make the environment safe for an imperfect agent.

| Concern | How it's addressed |
|---|---|
| Agent accesses sensitive data | Permission deny rules block Read/Edit access to sensitive paths (~/.ssh, ~/.aws, ~/.env). Managed settings prevent override. |
| Agent makes unauthorized changes | All changes go through Pull Requests. Nothing reaches production without human review. |
| Prompt injection (poisoned content) | Even if injection succeeds, there are no secrets to steal, dangerous commands are denied, and nothing deploys without PR review. |
| Secrets leak | No secrets exist in the workspace. Scheduled CI runs use scoped GitHub Secrets that Claude never sees. |
| Internet access | Users already have internet on their machines — Claude is no different. Security comes from having nothing to exfiltrate, not blocking the network. |
| Untracked code | Everything is in Git. CODEOWNERS enforces review. CI runs are logged. Full audit trail. |

### The three security layers

No single layer is sufficient alone.

| Layer | What it does | Enforcement |
|---|---|---|
| **CLAUDE.md** | Behavioral rules: PR-only workflow, don't access secrets, treat external content as untrusted | **Advisory** — Claude follows these but nothing technically prevents violation |
| **GitHub controls** | Branch protection, CODEOWNERS, required reviews, CI checks | **Enforced by GitHub** — no code reaches `main` without review |
| **Claude Code managed settings** | Permission deny rules block sensitive file access (Read/Edit) and destructive commands (Bash). Enterprise lock flags prevent local override. | **Enforced by Claude Code** — IT deploys managed settings the user can't override. Deny rules evaluated before allow rules. |

**CLAUDE.md alone is not enough.** All three layers must be active. See [`it-checklist.md`](it-checklist.md) for setup.

### Known limitations (be honest with IT about these)

- **Permission deny rules have had bugs** in Claude Code. Managed settings with `allowManagedPermissionRulesOnly` provide the strongest enforcement. Verify deny rules are working during the verification step.
- **Python code can call subprocess/os modules** which could bypass shell-level command denies. All code must pass PR review before merging — this is the control for code-level bypasses.
- **Prompt injection defense is advisory.** CLAUDE.md tells Claude to parse deterministically, but there is no technical enforcement that prevents it from writing non-deterministic code. Code review is the control.
- **Merged code can access CI secrets.** If scheduled workflows use secrets, a malicious PR that passes review could exfiltrate them. Mitigate with protected GitHub Environments requiring deployment reviewers.

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

**This is the most important step.** Place this file on the user's machine via MDM (Jamf, Intune, etc.). It cannot be overridden.

**macOS:** `/Library/Application Support/ClaudeCode/managed-settings.json`
**Linux:** `/etc/claude-code/managed-settings.json`

```json
{
  "allowManagedPermissionRulesOnly": true,
  "disableBypassPermissionsMode": "disable",
  "permissions": {
    "deny": [
      "Read(~/.ssh)",
      "Read(~/.ssh/**)",
      "Read(~/.aws)",
      "Read(~/.aws/**)",
      "Read(~/.gnupg)",
      "Read(~/.gnupg/**)",
      "Read(~/.env)",
      "Read(~/.env.*)",
      "Read(~/.config/gcloud/**)",
      "Read(~/.claude/memory/**)",
      "Edit(~/.ssh/**)",
      "Edit(~/.aws/**)",
      "Edit(~/.bashrc)",
      "Edit(~/.zshrc)",
      "Edit(~/.profile)",
      "Bash(rm -rf *)",
      "Bash(curl * | *)",
      "Bash(curl * -o *)",
      "Bash(wget *)",
      "Bash(pip install *)",
      "Bash(pip3 install *)",
      "Bash(python -m pip *)",
      "Bash(python3 -m pip *)",
      "Bash(git push --force *)",
      "Bash(git push -f *)",
      "Bash(git push origin main)",
      "Bash(git push origin master)",
      "Bash(git push origin HEAD:main)",
      "Bash(git push origin HEAD:master)",
      "Bash(git remote add *)",
      "Bash(git remote set-url *)",
      "Bash(git config *)"
    ]
  }
}
```

- `allowManagedPermissionRulesOnly` — local/project settings cannot override these deny rules
- `disableBypassPermissionsMode` — prevents the user from entering unrestricted mode
- `Read()`/`Edit()` deny rules block sensitive file access across all tools
- `Bash()` deny rules block destructive and unauthorized commands

**Why no network restrictions?** Users already have internet on their machines. Restricting Claude's web access adds friction without security benefit — the workspace has no secrets and nothing deploys without review.

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

## Day-to-day usage

Open a terminal in the repo, run `claude`, and describe what you need in plain English. Claude writes the code, adds tests, and opens a PR.

Every request produces a Pull Request with a diff, test results, and risk notes. Review it, merge it, done.

---

## How IT reviews PRs

| Check | What to look for |
|---|---|
| Files changed | Changes to protected files (CLAUDE.md, workflows, deps) trigger CODEOWNERS review automatically. |
| External integrations | Any new domains, APIs, or data sources? Expected and necessary? |
| Dependencies | New packages? Well-known and necessary? |
| Tests | Do they exist? Do they pass? (CI checks automatically.) |
| Secrets | Any hardcoded keys or tokens? (There shouldn't be.) |

---

## Scheduled runs

Once merged to `main`, automation can run on a schedule via GitHub Actions. The `scheduled-run.yml` workflow runs on a configurable schedule and uploads outputs as downloadable artifacts.

If output delivery to external systems is needed, IT adds scoped secrets to the repo (Settings → Secrets → Actions). Claude Code never sees these — they only exist in CI.

---

## IT security FAQ

**Q: Can Claude Code access the user's email, files, or credentials?**
Claude Code can technically access files on the machine. That's why managed settings are critical — they include `Read()` and `Edit()` deny rules that block access to sensitive paths (~/.ssh, ~/.aws, ~/.env). The `allowManagedPermissionRulesOnly` flag ensures these can't be overridden by local or project settings. Without managed settings, protection is advisory only.

**Q: Can Claude push directly to main?**
Branch protection prevents this. Claude can push to feature branches and open PRs — it cannot push to `main`.

**Q: What about prompt injection?**
We assume it will happen. The defense is: even if injection succeeds, there are no secrets to steal, dangerous commands are denied, sensitive files are blocked by the sandbox, and nothing deploys without human review of the PR.

**Q: Claude has internet access — isn't that risky?**
The user already has internet access on the same machine. Claude fetching a webpage is no different from opening it in a browser. Security comes from having nothing to exfiltrate, not from blocking the network.

**Q: What's the audit trail?**
Git history (every change + who approved it), PR review records, GitHub Actions logs (every scheduled run), branch protection audit log.

**Q: What infrastructure is required?**
None. GitHub repo + GitHub Actions (included in GitHub plans) + Claude Code on the user's machine. No servers, databases, or VPNs.

---

## The pitch to IT (one paragraph)

This doesn't make the AI agent safe. It makes the environment safe for an imperfect agent. The workspace has nothing valuable to steal. Dangerous commands are blocked at the OS level. All code changes require human review before they go live. It's the same security model you use for junior developers — limited access, code review, and CI gates. The difference is this developer works 100x faster and never forgets to write tests.
