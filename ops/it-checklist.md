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

## CODEOWNERS (optional but recommended)
- [ ] Add `CODEOWNERS` file requiring IT review for:
  - `CLAUDE.md`
  - `.github/workflows/`
  - `requirements.txt`

## Access control
- [ ] Grant analyst(s) write access to the repo
- [ ] Ensure IT security team has admin access
- [ ] Enable audit log monitoring for the repo (if available on your plan)

## Secrets (only if scheduled output delivery is needed)
- [ ] Add scoped secrets (e.g., `SHAREPOINT_TOKEN`) via Settings → Secrets → Actions
- [ ] Document what each secret is for and its access scope
- [ ] Set secret expiration reminders

## Analyst machine setup
- [ ] Install Claude Code: `npm install -g @anthropic-ai/claude-code`
- [ ] Provision Anthropic API key for the team
- [ ] Instruct analyst to set `ANTHROPIC_API_KEY` as environment variable (never in a file)
- [ ] Verify analyst can clone repo and run `claude` in the repo directory

## Verification
- [ ] Analyst runs `claude` and confirms CLAUDE.md constraints are loaded
- [ ] Analyst makes a test request and opens a PR
- [ ] IT reviews the test PR and verifies CI checks pass
- [ ] Merge and confirm scheduled workflow runs (or trigger manually via workflow_dispatch)
