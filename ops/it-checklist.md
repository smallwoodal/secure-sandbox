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
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "allowManagedPermissionRulesOnly": true,
  "allowManagedHooksOnly": true,
  "allowedMcpServers": [],
  "strictKnownMarketplaces": true,
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
      "Bash(gh pr view *)"
    ],
    "deny": [
      "WebFetch",
      "WebSearch",
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
- `strictKnownMarketplaces: true` — restricts marketplace/plugin installations to verified sources only
- `permissions.defaultMode: "dontAsk"` — auto-denies any tool not in the managed allow list. No permission prompts to social-engineer.
- `permissions.disableBypassPermissionsMode` — prevents unrestricted mode
- `permissions.allow` — the explicit allowlist of tools Claude can use. **IT controls this list.** Adjust for your team's needs. `Bash(python *)` is broad — for tighter control, replace with specific commands like `Bash(python src/*)`.
- `WebFetch`/`WebSearch` deny — blocks Claude's built-in web browsing. **Remove these two lines if analysts need web access** — see Known Limitations for tradeoffs.
- `Read()`/`Edit()` deny rules — block Claude's file tools from sensitive paths
- `Bash()` deny rules — block destructive and unauthorized shell commands. Deny always overrides allow.
- `sandbox.enabled` + `allowUnsandboxedCommands: false` — OS-level Bash isolation with no escape hatch
- `sandbox.network.allowedDomains` — restricts what Bash commands can reach (curl, python scripts, etc.)

**Note:** Claude can push to feature branches (needed for PRs) but cannot push to `main`. Add domains to `allowedDomains` as analysts need new integrations.

- [ ] Deploy managed settings file to analyst machine(s)
- [ ] Verify managed settings cannot be overridden
- [ ] Add project-specific domains to `allowedDomains` as needed

### Known limitations (be transparent with security reviewers)
- `Read()`/`Edit()` deny rules only block those specific tools — a Bash command like `cat ~/.ssh/id_rsa` is a separate surface. The sandbox network restrictions mitigate this: even if Bash reads a sensitive file, it can't send it to an unlisted domain.
- Command deny patterns match specific strings. Creative variations may bypass them. PR review is the backstop for code-level bypasses.
- The deny list is partial, not comprehensive. It blocks common dangerous patterns but cannot anticipate every variant.
- Sandbox reads are unrestricted by default — Bash can read files outside the working directory. Writes are restricted. The network allowlist prevents exfiltration of read data.
- Web browsing (WebFetch/WebSearch) is denied by default. If you remove these deny rules to give analysts web access, web browsing becomes an exfiltration vector not covered by the sandbox network allowlist. Accept this tradeoff explicitly if enabled.

## 6. Analyst machine setup
- [ ] Install Claude Code: `npm install -g @anthropic-ai/claude-code`
- [ ] Provision Anthropic API key (environment variable, never in a file)
- [ ] Deploy managed settings (step 5) before the analyst starts
- [ ] Verify analyst can clone repo and run `claude`

## 7. Verification

Test that each layer is working:

- [ ] **Read tool deny test:** Ask Claude `Show me ~/.ssh/id_rsa` — the Read tool should be blocked by deny rules
- [ ] **Bash network deny test:** Ask Claude `Run: curl https://webhook.site/test` — should be blocked by sandbox network restrictions (domain not in allowlist)
- [ ] **Bash command deny test:** Ask Claude `Run: rm -rf /` — should be denied by Bash permission rules
- [ ] **dontAsk mode test:** Ask Claude to use a tool not in the project allow list — should be auto-denied (no prompt)
- [ ] **WebFetch deny test:** Ask Claude to fetch a webpage — should be blocked by WebFetch deny rule
- [ ] **PR workflow test:** Analyst makes a test request and opens a PR
- [ ] **CI test:** IT reviews the test PR, verifies CI checks pass
- [ ] **Scheduled run test:** Merge and confirm scheduled workflow runs (or trigger manually)

## Secrets (only if scheduled output delivery is needed)

**WARNING:** Any code merged to `main` can access secrets in scheduled CI runs. This is a real exfiltration risk. Mitigate with protected environments.

- [ ] Create a **protected environment** (Settings → Environments → New → "production") **before the first scheduled run**
  - **WARNING:** GitHub auto-creates unprotected environments if they don't exist. Create this manually with protection rules FIRST.
  - Require at least 1 reviewer before deployment
  - Limit which branches can deploy (only `main`)
- [ ] Add scoped secrets to the **environment**, not to the repo
- [ ] Verify `environment: production` is set in `scheduled-run.yml` (already configured in template)
- [ ] Document what each secret is for and its scope
- [ ] Set expiration reminders
- [ ] Enable GitHub secret scanning (Settings → Code security → Secret scanning)
