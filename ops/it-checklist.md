# IT Setup Checklist

Use this checklist when provisioning a new sandbox repo for a team.

## 1. Repository setup
- [ ] Create private repo in GitHub organization (use this repo as template)
- [ ] Verify `CLAUDE.md` and `.claude/settings.json` are present and unmodified

## 2. Branch protection (Settings → Branches → `main`)
- [ ] Require pull request before merging
- [ ] Require at least 1 approval
- [ ] Require status checks to pass (`PR Checks` workflow)
- [ ] Do not allow bypassing the above settings

## 3. CODEOWNERS (required — this is a hard control)
- [ ] Add `CODEOWNERS` file requiring IT review for:
  - `CLAUDE.md`
  - `.claude/**`
  - `.github/workflows/`
  - `requirements.txt`
  - `CODEOWNERS` (itself — prevents self-modification)

## 4. Access control
- [ ] Grant analyst(s) write access to the repo
- [ ] Ensure IT security team has admin access
- [ ] Enable audit log monitoring (if available on your GitHub plan)

## 5. Deploy managed sandbox settings (CRITICAL)

CLAUDE.md is advisory. The sandbox provides actual OS-level enforcement. Deploy this file via MDM (Jamf, Intune, etc.) — analysts cannot override it.

- **macOS**: `/Library/Application Support/ClaudeCode/managed-settings.json`
- **Linux**: `/etc/claude-code/managed-settings.json`

```json
{
  "allowManagedPermissionRulesOnly": true,
  "allowManagedHooksOnly": true,
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
  },
  "sandbox": {
    "enabled": true,
    "network": {
      "allowedDomains": [
        "github.com",
        "api.github.com",
        "pypi.org",
        "files.pythonhosted.org"
      ]
    }
  },
  "deniedMcpServers": [{ "serverName": "*" }]
}
```

**What each layer does:**
- `allowManagedPermissionRulesOnly` — prevents local/project settings from overriding denies
- `allowManagedHooksOnly` — blocks user/project hooks
- `disableBypassPermissionsMode` — prevents unrestricted mode
- `Read()`/`Edit()` deny rules — block Claude's file tools from sensitive paths
- `Bash()` deny rules — block destructive and unauthorized shell commands
- `sandbox.enabled` — OS-level Bash isolation (restricts writes to working directory)
- `sandbox.network.allowedDomains` — restricts outbound network from Bash commands. **Claude's built-in web browsing is not affected** — only shell commands (curl, python scripts, etc.)
- `deniedMcpServers` — blocks all MCP server connections

**Note:** Claude can push to feature branches (needed for PRs) but cannot push to `main`. Add domains to `allowedDomains` as analysts need new integrations.

- [ ] Deploy managed settings file to analyst machine(s)
- [ ] Verify managed settings cannot be overridden
- [ ] Add scraper-specific domains to `allowedDomains` as needed

### Known limitations (be transparent with security reviewers)
- `Read()`/`Edit()` deny rules only block those specific tools — a Bash command like `cat ~/.ssh/id_rsa` is a separate surface. The sandbox network restrictions mitigate this: even if Bash reads a sensitive file, it can't send it to an unlisted domain.
- Command deny patterns match specific strings. Creative variations may bypass them. PR review is the backstop for code-level bypasses.
- The deny list is partial, not comprehensive. It blocks common dangerous patterns but cannot anticipate every variant.
- Sandbox reads are unrestricted by default — Bash can read files outside the working directory. Writes are restricted. The network allowlist prevents exfiltration of read data.

## 6. Analyst machine setup
- [ ] Install Claude Code: `npm install -g @anthropic-ai/claude-code`
- [ ] Provision Anthropic API key (environment variable, never in a file)
- [ ] Deploy managed settings (step 5) before the analyst starts
- [ ] Verify analyst can clone repo and run `claude`

## 7. Verification
- [ ] Ask Claude to `cat ~/.ssh/id_rsa` — should be blocked by sandbox
- [ ] Ask Claude to `rm -rf /` — should be denied by permissions
- [ ] Analyst makes a test request and opens a PR
- [ ] IT reviews the test PR, verifies CI checks pass
- [ ] Merge and confirm scheduled workflow runs (or trigger manually)

## Secrets (only if scheduled output delivery is needed)

**WARNING:** Any code merged to `main` can access secrets in scheduled CI runs. This is a real exfiltration risk. Mitigate with protected environments.

- [ ] Create a **protected environment** (Settings → Environments → New → "production")
  - Require at least 1 reviewer before deployment
  - Limit which branches can deploy (only `main`)
- [ ] Add scoped secrets to the **environment**, not to the repo
- [ ] Uncomment `environment: production` in `scheduled-run.yml`
- [ ] Document what each secret is for and its scope
- [ ] Set expiration reminders
- [ ] Enable GitHub secret scanning (Settings → Code security → Secret scanning)
