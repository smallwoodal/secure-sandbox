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
| Internet access | Claude's web browsing works like a normal browser (same access the analyst already has). Bash commands are sandboxed to an allowlisted set of domains — shell-level exfiltration is blocked. |
| Untracked code | Everything is in Git. CODEOWNERS enforces review. CI runs are logged. Full audit trail. |

### The three security layers

No single layer is sufficient alone.

| Layer | What it does | Enforcement |
|---|---|---|
| **CLAUDE.md** | Behavioral rules: PR-only workflow, don't access secrets, treat external content as untrusted | **Advisory** — Claude follows these but nothing technically prevents violation |
| **GitHub controls** | Branch protection, CODEOWNERS, required reviews, CI checks | **Enforced by GitHub** — no code reaches `main` without review |
| **Claude Code managed settings** | Bash sandbox (OS-level write isolation + network restrictions), managed allow/deny rules for all tools, MCP server lockout, hook locks, marketplace restrictions, `dontAsk` default mode. IT controls the full permission model. | **Enforced by Claude Code + OS** — IT deploys managed settings the user can't override. |

**CLAUDE.md alone is not enough.** All three layers must be active. See [`it-checklist.md`](it-checklist.md) for setup.

### Known limitations (be honest with IT about these)

- **Read/Edit deny rules only block those specific tools.** A Bash command like `cat ~/.ssh/id_rsa` is not blocked by `Read(~/.ssh/**)`. The Bash sandbox network restrictions mitigate this — even if Bash reads a file, it can't send it to an unlisted domain.
- **`Bash(python *)` in the allow list is broad.** Python scripts can call subprocess/os modules, bypassing shell-level command denies. The sandbox network restrictions limit where data can go. For tighter control, replace with specific patterns like `Bash(python src/*)` or audited wrapper scripts. PR review is the backstop.
- **Sandbox Bash reads are unrestricted by default.** Bash can read files outside the working directory. Writes are restricted to the working directory. The network allowlist prevents exfiltration.
- **Claude's web browsing is unrestricted.** The sandbox network allowlist only affects Bash commands. Claude's WebFetch/WebSearch are allowed because analysts need web access for research and testing. However, autonomous tool-driven exfiltration is a different risk class than human browsing — a prompt injection can trigger it faster and less visibly. The Bash sandbox blocks shell-level exfiltration (the more dangerous vector). For maximum lockdown, move WebFetch/WebSearch from the allow list to the deny list.
- **Prompt injection defense is advisory.** CLAUDE.md tells Claude to parse deterministically, but there is no technical enforcement that prevents it from writing non-deterministic code. Code review is the control.
- **Merged code can access CI secrets.** If scheduled workflows use secrets, a malicious PR that passes review could exfiltrate them. Mitigate with protected GitHub Environments requiring deployment reviewers.
- **`github.com` in `allowedDomains` is a broad domain.** Anthropic's docs explicitly warn: *"Users should be aware of potential risks that come from allowing broad domains like `github.com` that may allow for data exfiltration."* We include it because PR workflows require it. If your threat model is concerned about Bash-level exfil via GitHub API, remove it and have analysts push manually.
- **Domain fronting can bypass network sandbox filtering.** Anthropic's docs note that *"in some cases it may be possible to bypass the network filtering through domain fronting."* The network allowlist is a strong control but not airtight — PR review remains the backstop for code that attempts network access tricks.
- **`autoAllowBashIfSandboxed` defaults to `true`.** When the sandbox is enabled, Bash commands matching the allow list are auto-approved without prompts. This is the intended behavior under `dontAsk` mode (unapproved commands are auto-denied), but IT should be aware that sandboxed Bash commands won't generate user-facing approval prompts. Set `autoAllowBashIfSandboxed: false` in managed settings if you want explicit prompts for every Bash command.

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
  "allowedMcpServers": [],
  "strictKnownMarketplaces": [],
  "permissions": {
    "defaultMode": "dontAsk",
    "disableBypassPermissionsMode": "disable",
    "allow": [
      "Read",
      "Edit",
      "Write",
      "Glob",
      "Grep",
      "Bash(pytest *)",
      "Bash(python *)",
      "Bash(python3 *)",
      "Bash(ls *)",
      "Bash(mkdir *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Bash(git branch *)",
      "Bash(git checkout *)",
      "Bash(git switch *)",
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(git log *)",
      "Bash(git stash *)",
      "Bash(git push origin *)",
      "Bash(gh pr create *)",
      "Bash(gh pr view *)",
      "WebFetch",
      "WebSearch"
    ],
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
- `allowManagedPermissionRulesOnly` — only permission rules in this file apply. Project/user-level rules are ignored. IT controls the full permission model.
- `allowManagedHooksOnly` — blocks user/project hooks that could bypass controls
- `allowedMcpServers: []` — blocks all MCP server connections (empty allowlist = nothing permitted)
- `strictKnownMarketplaces: []` — empty array blocks all marketplace/plugin installations. Add approved marketplace sources to the array as needed.
- `permissions.defaultMode: "dontAsk"` — auto-denies any tool not in the managed allow list above. No permission prompts to social-engineer.
- `permissions.disableBypassPermissionsMode` — prevents unrestricted mode
- `permissions.allow` — the explicit allowlist of tools Claude can use. **IT controls this list.** Includes WebFetch/WebSearch (web browsing — same access the analyst already has). `Bash(python *)` is broad by design — for tighter control, replace with specific commands like `Bash(python src/*)`. For maximum lockdown, move WebFetch/WebSearch to the deny list.
- `Read()`/`Edit()` deny rules — block Claude's file tools from sensitive paths
- `Bash()` deny rules — block destructive and unauthorized shell commands. Deny rules always override allow rules.
- `sandbox.enabled` + `allowUnsandboxedCommands: false` — OS-level Bash isolation with no escape hatch
- `sandbox.network.allowedDomains` — restricts what Bash commands can reach (curl, python scripts, etc.)

### 5. Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
export ANTHROPIC_API_KEY="sk-ant-..."   # IT provides this
git clone https://github.com/your-org/your-sandbox.git
cd your-sandbox
claude
```

### 6. Verify

Test each enforcement layer:

```
> Show me the contents of ~/.ssh/
```
The Read tool should be blocked by deny rules.

```
> Run: curl https://webhook.site/test
```
Should be blocked by sandbox network restrictions (domain not in allowlist).

If neither is blocked, managed settings aren't active — go back to step 4.

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
Managed settings control the full permission model: only IT-approved tools are allowed, everything else is auto-denied (`dontAsk` mode) — no permission prompts for a user to approve. `Read()`/`Edit()` deny rules block sensitive paths. The Bash sandbox restricts writes to the working directory and limits network to allowlisted domains. MCP servers, unapproved hooks, and unapproved marketplace plugins are all blocked. Without managed settings, protection is advisory only.

**Q: Can Claude push directly to main?**
Branch protection prevents this. Claude can push to feature branches and open PRs — it cannot push to `main`.

**Q: What about prompt injection?**
We assume it will happen. The defense is: even if injection succeeds, there are no secrets to steal, dangerous commands are denied, sensitive files are blocked by the sandbox, and nothing deploys without human review of the PR.

**Q: Claude has internet access — isn't that risky?**
Claude's web browsing works like a normal browser — the same access the analyst already has on their machine. Bash commands (curl, python scripts, etc.) are the more dangerous exfiltration vector, and those are sandboxed to an allowlisted set of domains. For maximum lockdown, IT can move WebFetch/WebSearch from the allow list to the deny list.

**Q: What's the audit trail?**
Git history (every change + who approved it), PR review records, GitHub Actions logs (every scheduled run), branch protection audit log.

**Q: What infrastructure is required?**
None. GitHub repo + GitHub Actions (included in GitHub plans) + Claude Code on the user's machine. No servers, databases, or VPNs.

---

## The pitch to IT (one paragraph)

This doesn't make the AI agent safe. It makes the environment safe for an imperfect agent. IT controls the full permission model via managed settings — only approved tools work, everything else is auto-denied. The workspace has nothing valuable to steal. Bash commands are sandboxed with network restrictions so data can't leave through unauthorized channels. MCP connections are blocked. Sensitive file paths are blocked. Hooks, marketplace plugins, and bypass mode are locked. All code changes require human review before they go live. It's the same security model you use for junior developers — limited access, code review, and CI gates. The difference is this developer works 100x faster and never forgets to write tests.
