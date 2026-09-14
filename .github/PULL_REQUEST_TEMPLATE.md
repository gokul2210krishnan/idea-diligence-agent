## Description

Please provide a brief summary of the changes introduced in this pull request and the motivation behind them.

Fixes / Closes #(issue number if applicable)

---

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 🛡️ Security / Governance enhancement (improves safety boundaries, budget, or data sanitization)
- [ ] 📝 Documentation update (improves guides, README, or docstrings)
- [ ] 🧪 Tests (adds missing unit or integration tests)
- [ ] ⚙️ Refactoring / Performance improvement

---

## Governance & Security Impact

Does this change touch any of the 5 defense boundaries?
- [ ] Boundary 1: Safety & Scope Gate (`src/governance/safety_gate.py`)
- [ ] Boundary 2: Budget Governor (`src/governance/budget_governor.py`)
- [ ] Boundary 3: Untrusted Web Data Sanitizer (`src/governance/data_sanitizer.py`)
- [ ] Boundary 4: State Authority / Propose-Validate-Merge (`src/governance/state_updater.py`)
- [ ] Boundary 5: Decision-Impact Unknowns (`src/models.py`)
- [ ] No governance boundaries touched

---

## Verification & Testing

Please describe how you tested your changes:

- [ ] Ran automated test suite (`python -m pytest`) — all tests passed
- [ ] Tested CLI demo mode (`python -m src.main --demo`)
- [ ] Tested Web UI workspace (`python -m src.main --web`)
- [ ] Ran live investigation with configured model provider

---

## Contributor Checklist

- [ ] My code follows the project's coding standards and PEP 8 guidelines.
- [ ] I have maintained **Windows console compatibility** (no raw non-ASCII unicode glyphs in CLI outputs).
- [ ] I have added/updated tests that prove my fix is effective or that my feature works.
- [ ] I have updated the documentation accordingly (README, docstrings, CHANGELOG).
- [ ] I have verified that no API keys, credentials, or `.env` secrets are included in this PR.
