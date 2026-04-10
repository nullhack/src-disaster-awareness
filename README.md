# Disaster Surveillance Reporter

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?style=for-the-badge)](docs/coverage/index.html)

> Backend pipeline for disaster incident processing. Fetches from modular sources, transforms with DSPy AI, classifies via OpenCode CLI, stores via pluggable backends. No dashboard - pure backend processing.

**AI-Enhanced Python Project** built with enterprise-grade architecture, TDD workflows, and zero-config quality standards.

## Features

- **Modular Source Adapters**: Pluggable incident sources using adapter pattern
  - **GDACSAdapter**: https://www.gdacs.org/ (disaster database) - Real HTTP calls required
  - **ProMEDAdapter**: https://www.promedmail.org/ (disease database)
  - **ReliefWebAdapter**: https://reliefweb.int/ (humanitarian data)
  - **HealthMapAdapter**: https://www.healthmap.org/ (disease surveillance)
  - **WHOAdapter**: https://www.who.int/emergencies/ (health emergencies)
  - Easy to add new sources without modifying core code
- **Modular Storage Backends**: Pluggable storage using adapter pattern
  - **JSONLBackend**: Date-based subfolders (`incidents/by-date/YYYY-MM-DD/incidents.jsonl`)
  - **SQLiteBackend**: Store in `incidents.db` with defined schema
  - **EmailBackend**: Send incidents via SMTP
  - **GoogleSheetsBackend**: Write to Google Sheets (one tab per day, append to next empty row)
  - Easy to add new storage without modifying core code
- **DSPy AI Transformation**: Convert raw source data to schema-compliant format
- **Rule-Based Classification**: Country groups (A/B/C), severity levels (1-4), priority (HIGH/MEDIUM/LOW)
- **Test Mocks**: All external AI calls mockable for testing (avoid free model quota limits)
- **Real Data Tests**: GDACS adapter tests make actual HTTP calls to https://www.gdacs.org/
- **CLI Interface**: fetch, classify, store, status, full-cycle commands

---

## ⚡ Quick Start

```bash
# Clone and setup
git clone https://github.com/nullhack/disaster-surveillance-reporter
cd disaster-surveillance-reporter

# Install UV package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Initialize AI development environment
opencode && /init

# Setup development environment
uv venv && uv pip install -e '.[dev]'

# Validate everything works
task test && task lint && task static-check
```

## 🤖 AI-Powered Development

This project includes built-in AI agents to accelerate your development.

### Multi-Session Development

Complex projects are developed across multiple AI sessions. `TODO.md` at the root acts as the shared state — any AI agent can pick up exactly where the last session stopped.

```bash
# Start any session: read state, orient, continue
@developer /skill session-workflow

# End any session: update TODO.md, commit progress, hand off
@developer /skill session-workflow
```

### Feature Development Workflow

```bash
# Define new features with SOLID principles
@developer /skill feature-definition

# Create prototypes and validate concepts  
@developer /skill prototype-script

# Write comprehensive tests first (TDD)
@developer /skill tdd

# Get architecture review before implementing
@architect

# Implement with guided TDD workflow
@developer /skill implementation

# Create releases with smart versioning
@repo-manager /skill git-release
```

## 🏗️ Architecture & Standards

- **🎯 SOLID Principles** - Single responsibility, dependency inversion, clean interfaces
- **🔧 Object Calisthenics** - No primitives, small classes, behavior-rich objects
- **🧪 TDD Testing** - 100% coverage requirement with property-based tests
- **⚡ Modern Toolchain** - UV, Ruff, PyTest, Hypothesis, PyRight
- **🚀 Smart Releases** - Calver versioning with AI-generated themed names

## 📋 Development Commands

```bash
# Core development workflow
task run              # Execute main application
task test             # Run comprehensive test suite  
task lint             # Format and lint code
task static-check     # Type safety validation
task doc-serve        # Live pdoc documentation server
task doc-build        # Build static pdoc API docs
task doc-publish      # Publish API docs to GitHub Pages

# Quality assurance
task test-report      # Detailed coverage report
task mut-report       # Mutation testing (optional)
```

## 🎯 Project Structure

```
disaster-surveillance-reporter/
├── disaster_surveillance_reporter/        # Main application package
│   ├── __init__.py                       # Package initialization
│   └── disaster_surveillance_reporter.py   # Core module
├── .opencode/                            # AI development agents
│   ├── agents/                           # Specialized AI agents
│   │   ├── developer.md                  # 7-phase development workflow
│   │   ├── architect.md                  # SOLID architecture review
│   │   └── repo-manager.md               # Release and PR management
│   └── skills/                           # Development skills
│       ├── session-workflow/             # Multi-session development state
│       ├── feature-definition/           # Requirements planning
│       ├── tdd/                          # Test-driven development
│       ├── implementation/               # Guided implementation
│       └── code-quality/                 # Quality enforcement
├── tests/                                # Comprehensive test suite
├── docs/                                 # Documentation (api/, tests/, coverage/)
├── TODO.md                               # Development roadmap & session state
├── Dockerfile                            # Multi-stage container build
└── pyproject.toml                        # Project configuration
```

## 🔧 Technology Stack

| Category | Tools |
|----------|-------|
| **Package Management** | UV (blazing fast pip/poetry replacement) |
| **Code Quality** | Ruff (linting + formatting), PyRight (type checking) |
| **Testing** | PyTest + Hypothesis (property-based testing), pytest-html-plus (BDD reports) |
| **AI Integration** | OpenCode agents for development automation |
| **Documentation** | pdoc with search functionality |
| **Containerization** | Docker with optimized multi-stage builds |

## 📈 Quality Metrics

- ✅ **100% Test Coverage** - Comprehensive test suite including edge cases
- ✅ **Static Type Safety** - Full type hints with protocol-based interfaces  
- ✅ **Zero Linting Issues** - Automated formatting and style enforcement
- ✅ **Property-Based Testing** - Hypothesis for robust validation
- ✅ **Architecture Compliance** - AI-enforced SOLID principles

## 🚀 Deployment Ready

```bash
# Production container build
docker build --target prod -t disaster_surveillance_reporter:latest .
docker run disaster_surveillance_reporter:latest

# Build API documentation
task doc-build  # Generates docs/api/index.html

# Publish API docs to GitHub Pages
task doc-publish  # Pushes docs/api to gh-pages branch

# Smart release management
@repo-manager /skill git-release
# Creates versioned release: v1.2.20260315 "Creative Fox"
```

## 🤝 Contributing

Built with AI-assisted development workflows:

```bash
# Start a new feature
@developer /skill feature-definition
@developer /skill prototype-script
@developer /skill tdd
@architect  # Architecture review
@developer /skill implementation
@repo-manager /skill pr-management
```

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

## 🙏 Built With

- [AI-Enhanced Python Template](https://github.com/nullhack/python-project-template) - Enterprise-grade Python project template
- [OpenCode](https://opencode.ai) - AI-powered development platform
- [UV](https://astral.sh/uv/) - Modern Python package manager
- [Ruff](https://astral.sh/ruff/) - Extremely fast Python linter

---

**Author:** eol ([@nullhack](https://github.com/nullhack))  
**Project:** [disaster-surveillance-reporter](https://github.com/nullhack/disaster-surveillance-reporter)  
**Documentation:** [nullhack.github.io/disaster-surveillance-reporter](https://nullhack.github.io/disaster-surveillance-reporter)

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/nullhack/disaster-surveillance-reporter.svg?style=for-the-badge
[contributors-url]: https://github.com/nullhack/disaster-surveillance-reporter/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/nullhack/disaster-surveillance-reporter.svg?style=for-the-badge
[forks-url]: https://github.com/nullhack/disaster-surveillance-reporter/network/members
[stars-shield]: https://img.shields.io/github/stars/nullhack/disaster-surveillance-reporter.svg?style=for-the-badge
[stars-url]: https://github.com/nullhack/disaster-surveillance-reporter/stargazers
[issues-shield]: https://img.shields.io/github/issues/nullhack/disaster-surveillance-reporter.svg?style=for-the-badge
[issues-url]: https://github.com/nullhack/disaster-surveillance-reporter/issues
[license-shield]: https://img.shields.io/badge/license-MIT-green?style=for-the-badge
[license-url]: https://github.com/nullhack/disaster-surveillance-reporter/blob/main/LICENSE