# Contributing to mnemoreg

Thanks for considering a contribution! This document explains the development workflow and how to get started quickly.

Quick start (local)
- Clone and install in editable mode:
  ```bash
  git clone https://github.com/i3iorn/mnemoreg.git
  cd mnemoreg
  python -m venv .venv

    Windows cmd: .venv\Scripts\activate
    Windows PowerShell: .venv\Scripts\Activate.ps1
    Unix/Mac: source .venv/bin/activate

  pip install -e ".[dev]"
  ```
- Run tests:
  ```bash
  python -m pytest -q
  ```
- Run formatting & checks:
  ```bash
    ruff check --fix .
    isort --profile black .
    black .
    pre-commit run --all-files
    ruff check .
    python -m mypy mnemoreg --ignore-missing-imports
  ```

Tests and CI
- The repository uses pytest for tests. CI runs tests on multiple Python versions.
- Add tests for any new behavior or bug fixes. Keep tests small and deterministic.

Coding style
- Use Black and Ruff (pre-commit is configured).
- Add type annotations for public functions and classes. Run `mypy` (see Makefile).

Pull request checklist
- [ ] Tests added / updated
- [ ] Typechecked (mypy)
- [ ] Formatted (black/ruff)
- [ ] CHANGELOG entry (if user-visible change)

Reporting issues
- Use the bug/feature templates when opening issues so we can triage them quickly.

License
- By contributing you agree that your contributions are licensed under the project MIT license.
