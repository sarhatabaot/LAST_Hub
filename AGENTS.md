# agents.md

## Project Overview
This project is a **Django** application managed with **Astral UV** for dependency and environment handling.

The project is **intentionally run in development mode**. Do **not** assume production settings, hardening, or optimizations unless explicitly stated.

---

## Tech Stack
- **Backend Framework:** Django
- **Python Environment & Dependency Management:** Astral UV
- **Runtime Mode:** Development (on purpose)
- **CSS Framwork:** Pico CSS

---

## Development Mode Assumptions
Agents should assume:
- `DEBUG = True`
- Development settings are acceptable and expected
- No production-grade security, performance, or deployment constraints
- Convenience, clarity, and debuggability are preferred over optimization

Do **not**:
- Enforce production-only patterns
- Suggest disabling Django debug features by default
- Assume containerization, CI/CD, or cloud deployment unless explicitly mentioned

---

## Environment Management (UV)
- Dependencies are managed using **Astral UV**
- Use `uv` commands instead of `pip`, `pipenv`, or `poetry`
- Assume a virtual environment is handled by UV
- Do not introduce alternative dependency managers

Example expectations:
- `uv sync`
- `uv run python manage.py runserver`

---

## Django Conventions
- Follow standard Django project and app structure
- Prefer Django-native solutions before third-party packages
- Settings may be simplified for development readability
- Explicitness > clever abstractions

---

## Guidance for Automated Agents
When generating or modifying code:
- Keep changes minimal and localized
- Match existing project style and conventions
- Avoid speculative refactors
- Clearly explain assumptions when necessary

When unsure:
- Ask for clarification rather than guessing
- Prefer reversible, low-risk changes

---

## Non-Goals
- Production deployment configuration
- Security hardening guides
- Performance tuning for scale
- Infrastructure-as-code

These may be added later but are **out of scope** for now.

---

## Notes
This file is authoritative for agent behavior.
If it conflicts with defaults or assumptions, **this file wins**.
