# Contributing to SIEM Dashboard

Thank you for your interest in contributing to **SIEM Dashboard**! 🎉

We welcome contributions of all kinds: bug fixes, new MITRE ATT&CK scenario playbooks, correlation rules, UI enhancements, documentation improvements, and architectural extensions.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Adding MITRE ATT&CK Scenarios](#adding-mitre-attck-scenarios)
  - [Pull Requests](#pull-requests)
- [Development Setup](#development-setup)
  - [Prerequisites](#prerequisites)
  - [Using Docker Compose (Recommended)](#using-docker-compose-recommended)
  - [Local Development (Without Docker)](#local-development-without-docker)
- [Project Architecture](#project-architecture)
- [Code Quality & Linting](#code-quality--linting)
- [Git Commit Conventions](#git-commit-conventions)
- [Getting Help](#getting-help)

---

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior according to our reporting guidelines.

---

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the [existing issues](https://github.com/) to see if the problem has already been reported.

When creating a bug report, please include:
- A clear, descriptive title.
- Steps to reproduce the behavior.
- Expected behavior vs. actual behavior.
- Relevant logs (`docker logs siem-backend-dev` or browser console logs).
- Environment details (OS, Docker version, browser).

### Suggesting Enhancements

Feature requests and ideas are warmly welcomed! Please open an issue using the Feature Request template, describing:
- The problem or use-case you are trying to solve.
- Your proposed solution or desired behavior.
- Any alternative approaches you've considered.

### Adding MITRE ATT&CK Scenarios

One of the easiest and most impactful ways to contribute is by adding new attack scenario playbooks!
Playbooks are YAML files located in [`backend/app/scenarios/playbooks/`](backend/app/scenarios/playbooks/):

1. Check existing playbooks (e.g. `brute_force_lateral.yml`, `dns_tunneling.yml`).
2. Map your scenario to MITRE ATT&CK tactics & techniques (e.g. Credential Access, Persistence).
3. Define the sequential event stages and metadata.
4. Add corresponding correlation rules in [`backend/app/engine/`](backend/app/engine/) if new event types are introduced.

### Pull Requests

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/siem-dashboard.git
   cd siem-dashboard
   ```
3. **Create a branch** for your work:
   ```bash
   git checkout -b feat/add-slack-alerts
   # or
   git checkout -b fix/event-stream-reconnect
   ```
4. **Make your changes** and test them thoroughly.
5. **Format & lint** your code before pushing (see [Code Quality & Linting](#code-quality--linting)).
6. **Commit** using conventional commit messages.
7. **Push** to your fork:
   ```bash
   git push origin feat/add-slack-alerts
   ```
8. **Submit a Pull Request** against the `main` branch of this repository.

---

## Development Setup

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose v2](https://docs.docker.com/compose/)
- [Git](https://git-scm.com/)
- Optional: [`just`](https://github.com/casey/just) command runner

For local native development (without Docker):
- [Python 3.14+](https://www.python.org/) and [`uv`](https://docs.astral.sh/uv/)
- [Node.js 20+](https://nodejs.org/) and [`pnpm`](https://pnpm.io/)
- MongoDB 8 & Redis 7 instances

### Using Docker Compose (Recommended)

1. **Clone the repo and configure environment:**
   ```bash
   cp .env.example .env
   ```

2. **Start the development stack:**
   ```bash
   # Using docker compose
   docker compose -f dev.compose.yml up -d

   # Or using just
   just dev
   ```

3. **Create an admin user:**
   ```bash
   docker exec -it siem-backend-dev flask admin create --email admin@example.com --password adminpassword

   # Or using just
   just create-admin --email admin@example.com --password adminpassword
   ```

4. **Access the application:**
   - Web UI: [http://localhost:3420](http://localhost:3420)
   - API / Nginx Proxy: [http://localhost:8431](http://localhost:8431)
   - API Docs: [http://localhost:8431/api/docs](http://localhost:8431/api/docs)

5. **View logs:**
   ```bash
   docker compose -f dev.compose.yml logs -f
   ```

### Local Development (Without Docker)

#### Backend Setup
```bash
cd backend
uv sync --extra dev
source .venv/bin/activate # or .venv\Scripts\activate on Windows
flask run --port 5113
```

#### Frontend Setup
```bash
cd frontend
pnpm install
pnpm dev
```

---

## Project Architecture

```
siem-dashboard/
├── backend/
│   ├── app/
│   │   ├── controllers/      # Route controllers (auth, alerts, logs, rules, scenarios)
│   │   ├── core/             # Auth, streaming (SSE), rate limiting, serialization
│   │   ├── engine/           # Correlation rules engine, normalizers, severity calculators
│   │   ├── models/           # MongoEngine documents (User, Alert, LogEvent, CorrelationRule)
│   │   ├── routes/           # Blueprint route registrations
│   │   ├── scenarios/        # MITRE ATT&CK attack simulation engine & YAML playbooks
│   │   └── schemas/          # Pydantic validation models
│   ├── pyproject.toml        # Backend dependencies & tool configurations
│   └── wsgi.py               # Application entry point
├── frontend/
│   ├── src/
│   │   ├── api/              # React Query hooks & API client types
│   │   ├── core/             # Shell layout, router, stores (Zustand), chart themes
│   │   ├── routes/           # Page routes (Dashboard, Alerts, Logs, Rules, Scenarios, Admin)
│   │   └── styles/           # SCSS tokens and global mixins
│   └── package.json          # Frontend dependencies & scripts
├── conf/                     # Nginx configurations
├── learn/                    # Educational security & architectural walk-throughs
├── compose.yml               # Production Docker Compose definition
├── dev.compose.yml           # Development Docker Compose with live reloading
└── justfile                  # Convenient task runner shortcuts
```

---

## Code Quality & Linting

Please run linters and formatters before submitting your pull request.

### Backend

```bash
# Linting with Ruff
docker exec siem-backend-dev ruff check app/
# Or locally:
uv run ruff check app/

# Type checking with Mypy
docker exec siem-backend-dev mypy app/
# Or locally:
uv run mypy app/

# Run tests
docker exec siem-backend-dev pytest
# Or locally:
uv run pytest
```

### Frontend

```bash
cd frontend

# Biome code formatting & linting
pnpm lint
pnpm lint:fix

# SCSS linting
pnpm lint:scss

# TypeScript check
pnpm typecheck
```

---

## Git Commit Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` A new feature or scenario playbook
- `fix:` A bug fix
- `docs:` Documentation only changes
- `style:` Formatting, missing semi colons, etc (no code logic change)
- `refactor:` A code change that neither fixes a bug nor adds a feature
- `perf:` A code change that improves performance
- `test:` Adding missing tests or correcting existing tests
- `chore:` Changes to the build process or auxiliary tools/libraries

Example:
```bash
git commit -m "feat(scenarios): add kerberoasting MITRE ATT&CK attack scenario"
git commit -m "fix(sse): handle client reconnection gracefully in live alert stream"
```

---

## Getting Help

If you have questions or need guidance on contributing:
- Open a GitHub Discussion or create an Issue with the question tag.
- Check the [Learning Modules](learn/00-OVERVIEW.md) for deep dives into SIEM concepts and system architecture.

Thank you for helping make SIEM Dashboard better for everyone!
