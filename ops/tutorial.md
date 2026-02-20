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
| Internet access | Claude's built-in web browsing works like a browser. Bash commands are sandboxed to an allowlisted set of domains — shell-level exfiltration is blocked. |
| Untracked code | Everything is in Git. CODEOWNERS enforces review. CI runs are logged. Full audit trail. |

### The three security layers

No single layer is sufficient alone.

| Layer | What it does | Enforcement |
|---|---|---|
| **CLAUDE.md** | Behavioral rules: PR-only workflow, don't access secrets, treat external content as untrusted | **Advisory** — Claude follows these but nothing technically prevents violation |
| **GitHub controls** | Branch protection, CODEOWNERS, required reviews, CI checks | **Enforced by GitHub** — no code reaches `main` without review |
| **Claude Code managed settings** | Bash sandbox (OS-level write isolation + network restrictions), permission deny rules for file tools and commands, hook/MCP/plugin locks. Enterprise flags prevent local override. | **Enforced by Claude Code + OS** — IT deploys managed settings the user can't override. |

**CLAUDE.md alone is not enough.** All three layers must be active. See [`it-checklist.md`](it-checklist.md) for setup.

### Known limitations (be honest with IT about these)

- **Read/Edit deny rules only block those specific tools.** A Bash command like `cat ~/.ssh/id_rsa` is not blocked by `Read(~/.ssh/**)`. The Bash sandbox network restrictions mitigate this — even if Bash reads a file, it can't send it to an unlisted domain.
- **Python code can call subprocess/os modules** which could bypass shell-level command denies. The sandbox network restrictions limit where that data can go. PR review is the backstop for code-level bypasses.
- **Sandbox Bash reads are unrestricted by default.** Bash can read files outside the working directory. Writes are restricted to the working directory. The network allowlist prevents exfiltration.
- **Claude's built-in web browsing is unrestricted.** The sandbox network allowlist only affects Bash commands. Claude's WebFetch/WebSearch tools work like a normal browser. This is by design (analysts need web access), but means a prompt injection could potentially use web browsing to exfiltrate data read from local files. The Bash sandbox prevents the most dangerous vector (shell-level exfil). PR review is the backstop.
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
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "allowManagedPermissionRulesOnly": true,
  "allowManagedHooksOnly": true,
  "permissions": {
    "disableBypassPermissionsMode": "disable",
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
  },
  "sandbox": {
    "enabled": true,
    "allowUnsandboxedCommands": false,
    "network": {
      "allowedDomains": [
        "github.com",
        "api.github.com",
        "pypi.org",
        "files.pythonhosted.org"
      ]
    }
  }
}
```

**What each section does:**
- `$schema` — enables validation against the official Claude Code settings schema
- `allowManagedPermissionRulesOnly` — local/project settings cannot override these deny rules
- `allowManagedHooksOnly` — blocks user/project hooks that could bypass controls
- `permissions.disableBypassPermissionsMode` — prevents unrestricted mode
- `Read()`/`Edit()` deny rules — block Claude's file tools from sensitive paths
- `Bash()` deny rules — block destructive and unauthorized shell commands
- `sandbox.enabled` + `allowUnsandboxedCommands: false` — OS-level Bash isolation with no escape hatch
- `sandbox.network.allowedDomains` — restricts what Bash commands can reach. **Only affects shell commands — Claude's built-in web browsing is not restricted.** Add domains as analysts build integrations.

### 5. Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
export ANTHROPIC_API_KEY="sk-ant-..."   # IT provides this
git clone https://github.com/your-org/your-sandbox.git
cd your-sandbox
claude
```

### 6. Verify

Test the controls are working:

```
> Show me the contents of ~/.ssh/
```

The Read tool should be blocked by deny rules. Also try:

```
> Run: curl https://webhook.site/test
```

Should be blocked by sandbox network restrictions (domain not in allowlist). If neither is blocked, managed settings aren't active — go back to step 4.

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

If output delivery to external systems is needed, IT adds scoped secrets to a **protected GitHub Environment** (not repo-level secrets). Protected environments require a deployment reviewer before any workflow can access the secrets — this prevents a malicious merged PR from silently exfiltrating them. See [`it-checklist.md`](it-checklist.md) for setup.

---

## IT security FAQ

**Q: Can Claude Code access the user's email, files, or credentials?**
Managed settings provide multiple layers: `Read()`/`Edit()` deny rules block Claude's file tools from sensitive paths. The Bash sandbox restricts writes to the working directory and limits network access to allowlisted domains — so even if a Bash command reads a sensitive file, it can't send it anywhere unauthorized. Hooks, MCP servers, and bypass mode are all locked. Without managed settings, protection is advisory only.

**Q: Can Claude push directly to main?**
Branch protection prevents this. Claude can push to feature branches and open PRs — it cannot push to `main`.

**Q: What about prompt injection?**
We assume it will happen. The defense is: even if injection succeeds, there are no secrets to steal, dangerous commands are denied, sensitive files are blocked by the sandbox, and nothing deploys without human review of the PR.

**Q: Claude has internet access — isn't that risky?**
Claude's built-in web browsing works unrestricted (same as the user opening a browser). Bash commands (curl, python scripts, etc.) are sandboxed — they can only reach domains on the managed allowlist. This blocks the most common exfiltration vector (shell commands sending data to attacker servers). Web browsing is a weaker exfiltration path — it's harder to abuse programmatically and the analyst can see what Claude is doing. New domains are added by IT as analysts build integrations.

**Q: What's the audit trail?**
Git history (every change + who approved it), PR review records, GitHub Actions logs (every scheduled run), branch protection audit log.

**Q: What infrastructure is required?**
None. GitHub repo + GitHub Actions (included in GitHub plans) + Claude Code on the user's machine. No servers, databases, or VPNs.

---

## The pitch to IT (one paragraph)

This doesn't make the AI agent safe. It makes the environment safe for an imperfect agent. The workspace has nothing valuable to steal. Bash commands are sandboxed with network restrictions so data can't leave through unauthorized channels. Sensitive file paths are blocked. Hooks, plugins, and bypass mode are locked. All code changes require human review before they go live. It's the same security model you use for junior developers — limited access, code review, and CI gates. The difference is this developer works 100x faster and never forgets to write tests.
