# AGENTS Instructions

## Scope
These instructions apply to the entire repository.

## Development Workflow
- Use the `develop` branch for all work.
- Before committing, run formatting and checks:
  - `pre-commit run --files <files>`
  - `pytest`
- Ensure the working tree is clean (`git status --short`) before finishing.

## Coding Style
- Follow PEP 8 style guidelines for Python code.
- Prefer descriptive naming and include docstrings for public functions and classes.

## Miscellaneous
- Use `rg` for searching the codebase instead of `grep -R` or `ls -R`.
- Avoid amending or re-writing history; create new commits for changes.
- Include references (citations) to file paths and line numbers in summaries or PR descriptions when relevant.
