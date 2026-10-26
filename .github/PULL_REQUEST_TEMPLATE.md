## Description

Please include a summary of the change and which issue it fixes (if applicable). Include relevant motivation and context.

Fixes #(issue)

---

## Type of Change

Please delete options that are not relevant:

- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 🎯 New MITRE ATT&CK scenario / Correlation Rule
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🎨 Code style / Refactor / Performance improvement

---

## How Has This Been Tested?

Please describe the tests that you ran to verify your changes:

- [ ] Tested locally via `docker compose -f dev.compose.yml up`
- [ ] Backend tests passing (`pytest` / `ruff check` / `mypy`)
- [ ] Frontend linting & type checks passing (`pnpm lint`, `pnpm typecheck`)
- [ ] Manual testing of attack scenarios or alert feeds

---

## Checklist

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have updated the documentation / README if needed
- [ ] My changes generate no new warnings or errors
- [ ] Any dependent changes have been merged and published in downstream modules
