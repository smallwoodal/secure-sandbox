"""Security policy conformance tests.

Validates that repo security controls are correctly configured.
These tests run in CI on every PR to catch accidental weakening of controls.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
SETTINGS_PATH = ROOT / ".claude" / "settings.json"
CODEOWNERS_PATH = ROOT / "CODEOWNERS"
CLAUDE_MD_PATH = ROOT / "CLAUDE.md"
TUTORIAL_PATH = ROOT / "ops" / "tutorial.md"
IT_CHECKLIST_PATH = ROOT / "ops" / "it-checklist.md"
PR_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "pr-checks.yml"
SCHEDULED_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "scheduled-run.yml"


def _load_settings():
    return json.loads(SETTINGS_PATH.read_text())


# --- Required files exist ---


def test_security_files_exist():
    """All security-critical files must be present."""
    required = [
        SETTINGS_PATH,
        CODEOWNERS_PATH,
        CLAUDE_MD_PATH,
        TUTORIAL_PATH,
        IT_CHECKLIST_PATH,
        PR_WORKFLOW_PATH,
        SCHEDULED_WORKFLOW_PATH,
    ]
    for path in required:
        assert path.exists(), f"Missing security file: {path.relative_to(ROOT)}"


# --- Project settings.json policy ---


def test_settings_has_schema():
    settings = _load_settings()
    assert "$schema" in settings, "settings.json missing $schema for validation"


def test_settings_sandbox_enabled():
    settings = _load_settings()
    sandbox = settings.get("sandbox", {})
    assert sandbox.get("enabled") is True, "Sandbox must be enabled"
    assert sandbox.get("allowUnsandboxedCommands") is False, (
        "allowUnsandboxedCommands must be false"
    )


def test_settings_network_allowlist_exists():
    settings = _load_settings()
    domains = settings.get("sandbox", {}).get("network", {}).get("allowedDomains", [])
    assert len(domains) > 0, "Network allowlist must not be empty"
    assert "github.com" in domains, "github.com must be in allowlist"


def test_settings_deny_list_covers_sensitive_paths():
    """Deny rules must block Read/Edit access to sensitive paths."""
    settings = _load_settings()
    deny = settings.get("permissions", {}).get("deny", [])
    required_denies = [
        "Read(~/.ssh)",
        "Read(~/.ssh/**)",
        "Read(~/.aws)",
        "Read(~/.aws/**)",
        "Edit(~/.ssh/**)",
        "Edit(~/.aws/**)",
    ]
    for rule in required_denies:
        assert rule in deny, f"Missing required deny rule: {rule}"


def test_settings_deny_list_covers_dangerous_commands():
    """Deny rules must block destructive Bash commands."""
    settings = _load_settings()
    deny = settings.get("permissions", {}).get("deny", [])
    required_denies = [
        "Bash(rm -rf *)",
        "Bash(git push --force *)",
        "Bash(git push -f *)",
        "Bash(git push origin main)",
        "Bash(git push origin master)",
    ]
    for rule in required_denies:
        assert rule in deny, f"Missing required deny rule: {rule}"


def test_settings_deny_list_covers_pip():
    """Deny rules must block unauthorized package installation."""
    settings = _load_settings()
    deny = settings.get("permissions", {}).get("deny", [])
    pip_denies = [r for r in deny if "pip" in r.lower()]
    assert len(pip_denies) >= 4, (
        f"Expected at least 4 pip deny rules, found {len(pip_denies)}"
    )


# --- CODEOWNERS policy ---


def test_codeowners_protects_security_files():
    """CODEOWNERS must require review for security-sensitive files."""
    content = CODEOWNERS_PATH.read_text()
    required_patterns = [
        "CLAUDE.md",
        ".claude/**",
        ".github/workflows/",
        "requirements.txt",
        "CODEOWNERS",
    ]
    for pattern in required_patterns:
        assert pattern in content, (
            f"CODEOWNERS missing protection for: {pattern}"
        )


def test_codeowners_protects_itself():
    """CODEOWNERS must include itself to prevent self-modification."""
    content = CODEOWNERS_PATH.read_text()
    lines = [line.strip() for line in content.splitlines() if not line.startswith("#")]
    codeowners_lines = [line for line in lines if line.startswith("CODEOWNERS")]
    assert len(codeowners_lines) > 0, "CODEOWNERS must protect itself"


# --- CLAUDE.md policy ---


def test_claude_md_has_required_rules():
    """CLAUDE.md must contain key behavioral rules."""
    content = CLAUDE_MD_PATH.read_text()
    required_phrases = [
        "untrusted",
        "PR",
        "Pull Request",
        "secrets",
    ]
    for phrase in required_phrases:
        assert phrase.lower() in content.lower(), (
            f"CLAUDE.md missing required concept: {phrase}"
        )


# --- Workflow policy ---


def test_pr_workflow_has_secret_scanning():
    """PR checks must include secret scanning."""
    content = PR_WORKFLOW_PATH.read_text()
    assert "gitleaks" in content.lower(), "PR workflow must include secret scanning"


def test_pr_workflow_has_codeowners_check():
    """PR checks must validate CODEOWNERS is configured."""
    content = PR_WORKFLOW_PATH.read_text()
    assert "CODEOWNERS" in content, "PR workflow must validate CODEOWNERS"


def test_scheduled_workflow_uses_protected_environment():
    """Scheduled workflow must use a protected environment."""
    content = SCHEDULED_WORKFLOW_PATH.read_text()
    assert "environment:" in content, (
        "Scheduled workflow must use a protected environment"
    )


def test_scheduled_workflow_has_environment_check():
    """Scheduled workflow must verify environment protection rules."""
    content = SCHEDULED_WORKFLOW_PATH.read_text()
    assert "protection_rules" in content, (
        "Scheduled workflow must check for environment protection rules"
    )


def test_workflows_use_pinned_actions():
    """All GitHub Actions must be SHA-pinned, not tag-pinned."""
    for workflow_path in [PR_WORKFLOW_PATH, SCHEDULED_WORKFLOW_PATH]:
        content = workflow_path.read_text()
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("- uses:") or stripped.startswith("uses:"):
                ref = stripped.split("@")[-1] if "@" in stripped else ""
                # SHA pins are 40 hex chars; tags are short like "v4"
                if ref and not ref.startswith("$"):
                    assert len(ref.split()[0]) >= 40, (
                        f"Action not SHA-pinned in {workflow_path.name}: {stripped}"
                    )


# --- Doc consistency ---


def test_tutorial_and_checklist_managed_settings_match():
    """The managed settings JSON in tutorial and IT checklist must be identical."""
    tutorial = TUTORIAL_PATH.read_text()
    checklist = IT_CHECKLIST_PATH.read_text()

    def extract_json_block(text):
        """Extract the first large JSON block (managed settings)."""
        blocks = text.split("```json")
        for block in blocks[1:]:
            json_text = block.split("```")[0].strip()
            try:
                parsed = json.loads(json_text)
                # The managed settings block has allowManagedPermissionRulesOnly
                if "allowManagedPermissionRulesOnly" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue
        return None

    tutorial_settings = extract_json_block(tutorial)
    checklist_settings = extract_json_block(checklist)

    assert tutorial_settings is not None, "Could not find managed settings in tutorial"
    assert checklist_settings is not None, (
        "Could not find managed settings in IT checklist"
    )
    assert tutorial_settings == checklist_settings, (
        "Managed settings in tutorial and IT checklist do not match"
    )


# --- Managed settings schema validation ---


def _extract_managed_settings(text):
    """Extract managed settings JSON block from a doc file."""
    blocks = text.split("```json")
    for block in blocks[1:]:
        json_text = block.split("```")[0].strip()
        try:
            parsed = json.loads(json_text)
            if "allowManagedPermissionRulesOnly" in parsed:
                return parsed
        except json.JSONDecodeError:
            continue
    return None


def test_managed_settings_required_keys():
    """Managed settings must contain all required security keys."""
    for doc_path in [TUTORIAL_PATH, IT_CHECKLIST_PATH]:
        settings = _extract_managed_settings(doc_path.read_text())
        assert settings is not None, f"No managed settings found in {doc_path.name}"

        required_top = [
            "allowManagedPermissionRulesOnly",
            "allowManagedHooksOnly",
            "allowedMcpServers",
            "strictKnownMarketplaces",
        ]
        for key in required_top:
            assert key in settings, (
                f"{doc_path.name} managed settings missing: {key}"
            )

        perms = settings.get("permissions", {})
        required_perms = ["defaultMode", "disableBypassPermissionsMode", "allow", "deny"]
        for key in required_perms:
            assert key in perms, (
                f"{doc_path.name} permissions missing: {key}"
            )

        sandbox = settings.get("sandbox", {})
        assert sandbox.get("enabled") is True, f"{doc_path.name} sandbox not enabled"
        assert sandbox.get("allowUnsandboxedCommands") is False, (
            f"{doc_path.name} missing allowUnsandboxedCommands: false"
        )


def test_managed_settings_correct_types():
    """Managed settings values must have correct types per schema."""
    for doc_path in [TUTORIAL_PATH, IT_CHECKLIST_PATH]:
        settings = _extract_managed_settings(doc_path.read_text())
        assert settings is not None

        # Boolean flags
        assert settings["allowManagedPermissionRulesOnly"] is True
        assert settings["allowManagedHooksOnly"] is True

        # Arrays (not booleans or strings)
        assert isinstance(settings["allowedMcpServers"], list), (
            f"{doc_path.name}: allowedMcpServers must be an array"
        )
        assert isinstance(settings["strictKnownMarketplaces"], list), (
            f"{doc_path.name}: strictKnownMarketplaces must be an array"
        )

        perms = settings["permissions"]
        assert isinstance(perms["allow"], list), "permissions.allow must be an array"
        assert isinstance(perms["deny"], list), "permissions.deny must be an array"
        assert perms["defaultMode"] == "dontAsk", "defaultMode must be dontAsk"
        assert perms["disableBypassPermissionsMode"] == "disable"

        # defaultMode must be under permissions, not top-level
        assert "defaultMode" not in settings, (
            f"{doc_path.name}: defaultMode must be under permissions, not top-level"
        )


def test_managed_settings_deny_not_in_allow():
    """No tool should appear in both allow and deny lists."""
    for doc_path in [TUTORIAL_PATH, IT_CHECKLIST_PATH]:
        settings = _extract_managed_settings(doc_path.read_text())
        assert settings is not None
        perms = settings["permissions"]
        allow_set = set(perms["allow"])
        deny_set = set(perms["deny"])
        overlap = allow_set & deny_set
        assert len(overlap) == 0, (
            f"{doc_path.name}: tools in both allow and deny: {overlap}"
        )


# --- Workflow security checks ---


def test_scheduled_workflow_fails_closed():
    """Environment check must fail-closed (exit 1 on unknown), not fail-open."""
    content = SCHEDULED_WORKFLOW_PATH.read_text()
    # Find the section between 'unknown' check and the next branch/end
    # and verify it contains 'exit 1'
    lines = content.splitlines()
    in_unknown_block = False
    found_exit_1 = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if "unknown" in stripped:
            in_unknown_block = True
            continue
        if in_unknown_block:
            if "exit 1" in stripped:
                found_exit_1 = True
                break
            # Stop at the next conditional branch or block end
            if stripped.startswith("else") or stripped == "fi":
                break
    assert found_exit_1, (
        "Scheduled workflow environment check must exit 1 on unknown (fail-closed)"
    )


def test_workflows_use_hash_verified_install():
    """CI workflows must use --require-hashes for pip install."""
    for workflow_path in [PR_WORKFLOW_PATH, SCHEDULED_WORKFLOW_PATH]:
        content = workflow_path.read_text()
        assert "--require-hashes" in content, (
            f"{workflow_path.name} must use --require-hashes for pip install"
        )
