# IT Setup Checklist

Use this checklist when provisioning a new secure-scraper-sandbox repo for a team.

## Repository setup
- [ ] Create private repo in GitHub organization
- [ ] Push template files (or use GitHub template repo feature)
- [ ] Verify `CLAUDE.md` is present and unmodified

## Branch protection (Settings → Branches → `main`)
- [ ] Require pull request before merging
- [ ] Require at least 1 approval
- [ ] Require status checks to pass (`PR Checks` workflow)
- [ ] Do not allow bypassing the above settings
- [ ] Restrict who can push to matching branches (optional)

## CODEOWNERS (required — this is a hard control, not optional)
- [ ] Add `CODEOWNERS` file requiring IT review for:
  - `CLAUDE.md`
  - `.claude/**`
  - `.github/workflows/`
  - `requirements.txt`
  - `CODEOWNERS` (itself — prevents self-modification)

## Access control
- [ ] Grant analyst(s) write access to the repo
- [ ] Ensure IT security team has admin access
- [ ] Enable audit log monitoring for the repo (if available on your plan)

## Secrets (only if scheduled output delivery is needed)
- [ ] Add scoped secrets (e.g., `SHAREPOINT_TOKEN`) via Settings → Secrets → Actions
- [ ] Document what each secret is for and its access scope
- [ ] Set secret expiration reminders

## Claude Code sandbox enforcement (CRITICAL — this is the real security layer)

CLAUDE.md is advisory. The sandbox provides actual OS-level enforcement.

### Option A: Managed settings (recommended — IT-controlled, analyst can't override)

Place this file on the analyst's machine. It takes highest precedence over all other settings.

- **macOS**: `/Library/Application Support/ClaudeCode/managed-settings.json`
- **Linux**: `/etc/claude-code/managed-settings.json`

```json
{
  "permissions": {
    "deny": [
      "Bash(rm -rf *)",
      "Bash(curl * | bash)",
      "Bash(wget * | bash)",
      "Bash(pip install *)",
      "Bash(git push *)",
      "Bash(git remote *)",
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

**Why no network restrictions here?** Analysts already have unrestricted internet access on their machines (browser, terminal, etc.). Restricting Claude Code's web access during development adds friction without meaningful security benefit — the workspace has no secrets to exfiltrate, and nothing deploys without PR review. Network restrictions are enforced in CI/production instead (see GitHub Actions workflows).

- [ ] Deploy managed settings file to analyst machine(s)
- [ ] Verify managed settings cannot be overridden by the analyst

### Option B: Project settings (included in repo — weaker, analyst could modify locally)

The repo ships with `.claude/settings.json` which provides project-level sandbox config. This is a fallback if managed settings deployment isn't feasible.

- [ ] Verify `.claude/settings.json` is present in the repo

### Known limitations (be aware)
- Permission `deny` rules for Read/Write tools have confirmed bugs (they may not block file reads)
- The OS-level sandbox (`/sandbox` mode) **does** enforce restrictions — ensure analysts run in sandbox mode
- Sub-agents may bypass some permission rules — the sandbox is the backstop

## Analyst machine setup
- [ ] Install Claude Code: `npm install -g @anthropic-ai/claude-code`
- [ ] Provision Anthropic API key for the team
- [ ] Instruct analyst to set `ANTHROPIC_API_KEY` as environment variable (never in a file)
- [ ] Deploy managed settings (see above) before the analyst starts using Claude Code
- [ ] Verify analyst can clone repo and run `claude` in the repo directory

## Verification
- [ ] Analyst runs `claude` and confirms CLAUDE.md constraints are loaded
- [ ] Test sandbox enforcement: ask Claude to `cat ~/.ssh/id_rsa` — should be blocked
- [ ] Analyst makes a test request and opens a PR
- [ ] IT reviews the test PR and verifies CI checks pass
- [ ] Merge and confirm scheduled workflow runs (or trigger manually via workflow_dispatch)
