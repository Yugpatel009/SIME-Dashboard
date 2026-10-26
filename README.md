```ruby
███████╗██╗███████╗███╗   ███╗
██╔════╝██║██╔════╝████╗ ████║
███████╗██║█████╗  ██╔████╔██║
╚════██║██║██╔══╝  ██║╚██╔╝██║
███████║██║███████╗██║ ╚═╝ ██║
╚══════╝╚═╝╚══════╝╚═╝     ╚═╝
```

[![Python](https://img.shields.io/badge/Python-3.14+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![License: AGPLv3](https://img.shields.io/badge/License-AGPL_v3-purple.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker)](https://www.docker.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)

> Full-stack SIEM (Security Information & Event Management) dashboard with real-time log correlation and MITRE ATT&CK attack scenario simulation engine.

*This is a quick overview — security theory, architecture, and full walkthroughs are in the [learn modules](#learn).*

**[Screenshots & demo overview →](DEMO.md)**

## What It Does

- **Real-Time Log Ingestion & Event Correlation**: Three rule types (Threshold, Sequence, Aggregation) for instant threat detection.
- **MITRE ATT&CK Scenario Simulation**: Four YAML-based attack playbooks (Brute Force, DNS Tunneling, Phishing, Privilege Escalation).
- **Server-Sent Events (SSE)**: Live streaming alerts and notifications with paginated, filterable security log viewer.
- **Alert Lifecycle Management**: Complete triage lifecycle (acknowledge, investigate, resolve, mark false positive).
- **Extensible Architecture**: Easily add custom attack scenarios and correlation rules via YAML.
- **Developer-Ready**: Task automation with [`just`](https://github.com/casey/just) and full Docker Compose development & production stacks.

## Quick Start

### 1. Using Docker Compose (Fastest)

```bash
# Clone the repository
git clone <your-repo-url>
cd siem-dashboard

# Copy sample environment configuration
cp .env.example .env

# Start development stack
docker compose -f dev.compose.yml up -d
```

Visit:
- **Web Dashboard**: [http://localhost:3420](http://localhost:3420)
- **API & Reverse Proxy**: [http://localhost:8431](http://localhost:8431)
- **API Documentation**: [http://localhost:8431/api/docs](http://localhost:8431/api/docs)

Create an initial admin user:
```bash
docker exec -it siem-backend-dev flask admin create --email admin@example.com --password adminpassword
```

> [!TIP]
> This project includes a [`justfile`](https://github.com/casey/just). Run `just` in your terminal to see all available shortcuts for building, running tests, creating admin accounts, and viewing logs.

## Tech Stack

- **Backend:** Flask, MongoEngine, Redis Streams, Pydantic, Argon2, JWT, Gunicorn
- **Frontend:** React 19, TypeScript, Vite, TanStack Query, Zustand, visx, SCSS Modules
- **Data & Cache:** MongoDB 8, Redis 7
- **Reverse Proxy & Deployment:** Nginx, Docker & Docker Compose

## Repository Structure

```
siem-dashboard/
├── backend/                  # Flask REST API, correlation engine & scenario runner
│   ├── app/
│   │   ├── controllers/      # Request handlers & logic
│   │   ├── engine/           # Correlation rules & log normalization
│   │   ├── scenarios/        # MITRE ATT&CK simulation runner & YAML playbooks
│   │   └── models/           # MongoEngine documents
├── frontend/                 # React 19 + TypeScript frontend application
│   ├── src/
│   │   ├── api/              # TanStack Query hooks & API schemas
│   │   ├── core/             # Layouts, Zustand stores, chart themes
│   │   └── routes/           # Dashboard, Alerts, Logs, Rules, Scenarios
├── conf/                     # Nginx configurations & Dockerfiles
├── learn/                    # In-depth educational guides
├── dev.compose.yml           # Hot-reloading development environment
├── compose.yml               # Production deployment configuration
└── justfile                  # Convenient task automation commands
```

## Learn

This project includes comprehensive educational modules covering cybersecurity fundamentals, SIEM architecture, and implementation details:

| Module | Topic |
|--------|-------|
| [00 - Overview](learn/00-OVERVIEW.md) | Prerequisites and quick start |
| [01 - Concepts](learn/01-CONCEPTS.md) | Security theory and real-world breaches |
| [02 - Architecture](learn/02-ARCHITECTURE.md) | System design and data flow |
| [03 - Implementation](learn/03-IMPLEMENTATION.md) | Code walkthrough |
| [04 - Challenges](learn/04-CHALLENGES.md) | Extension ideas and exercises |

## Contributing

Contributions are what make the open-source community such an amazing place to learn, build, and innovate. Any contributions you make are **warmly welcomed** and **greatly appreciated**!

Please read our [**Contributing Guide**](CONTRIBUTING.md) to get started with:
- Setting up your local environment
- Adding new MITRE ATT&CK scenario playbooks
- Submitting pull requests and following code style conventions

### 💡 Ideas for Contribution
- [ ] Add new MITRE ATT&CK scenarios (e.g., Kerberoasting, Ransomware simulation, SQL Injection) in `backend/app/scenarios/playbooks/`
- [ ] Add notification webhooks (Slack, Discord, Email, Microsoft Teams) for alerts
- [ ] Add export capabilities (CSV, PDF compliance reports) for logs and alerts
- [ ] Expand automated unit and integration tests

All contributors must adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

## Security

For vulnerability reports and disclosure procedures, please see our [Security Policy](SECURITY.md).

## License

This project is licensed under the [GNU Affero General Public License v3.0](LICENSE).
