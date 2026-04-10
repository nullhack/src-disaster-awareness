# Disaster Surveillance Reporter

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?style=for-the-badge)](docs/coverage/index.html)

> Multi-stage disaster surveillance pipeline with content similarity deduplication. Fetches from multiple sources, normalizes to JSONL, enhances with DSPy-AI, stores via pluggable backends. No dashboard - pure backend processing with intelligent duplicate prevention.

**AI-Enhanced Python Project** built with enterprise-grade architecture, TDD workflows, and zero-config quality standards.

## Features

### 🔄 **Multi-Stage Pipeline Architecture**
- **Stage 1**: Multi-source fetching → Normalized JSONL with content similarity deduplication
- **Stage 2**: JSONL → DSPy-AI enhancement → Enhanced JSONL
- **Stage 3**: Enhanced JSONL → Multiple storage backends

### 📡 **Modular Source Adapters**
- **GDACSAdapter**: https://www.gdacs.org/ (disaster database) - Real HTTP calls required
- **ProMEDAdapter**: https://www.promedmail.org/ (disease database)
- **ReliefWebAdapter**: https://reliefweb.int/ (humanitarian data)
- **HealthMapAdapter**: https://www.healthmap.org/ (disease surveillance)
- **WHOAdapter**: https://www.who.int/emergencies/ (health emergencies)
- **NewsAdapter**: Aggregated news sources for incident coverage
- Process multiple sources simultaneously with command flags

### 🗃️ **Storage Backends**
- **JSONLBackend**: Date-based subfolders with upsert capability (`incidents/by-date/YYYY-MM-DD/incidents.jsonl`)
- **SQLiteBackend**: Local database storage with schema validation
- **EmailBackend**: SMTP delivery for incident notifications
- **GoogleSheetsBackend**: Real-time spreadsheet updates
- Support multiple simultaneous storage backends

### 🧠 **Intelligence & Deduplication**
- **Content Similarity Matching**: Fuzzy matching on title/description to prevent duplicates
- **DSPy-AI Enhancement**: Fill missing fields, standardize formats, enrich incident data
- **Configurable Similarity Threshold**: Adjust duplicate detection sensitivity
- **Incremental Processing**: Skip already-processed incidents to avoid re-research

### 🖥️ **Enhanced CLI Interface**
```bash
# Multi-source processing
--sources gdacs,promed,reliefweb,healthmap,who,news

# Multi-storage output  
--storage jsonl,sqlite,email,sheets

# Duplicate detection tuning
--duplicate-threshold 0.8
```

### 🧪 **Advanced Testing Strategy**
- **Test Marks**: `unit`, `integration`, `e2e`, `slow`, `mock`, `real_api`
- **Mock-First Development**: All external services mocked by default
- **Optional E2E Tests**: Real API calls available via `task test-e2e` 
- **Property-Based Testing**: Hypothesis for robust validation

---

## ⚡ Quick Start

```bash
# Clone and setup
git clone https://github.com/nullhack/src-disaster-awareness
cd src-disaster-awareness

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
task test             # Run comprehensive test suite (smoke, unit, integration + coverage)
task test-fast        # Run fast tests only (skip slow tests)
task test-slow        # Run slow tests only
task lint             # Format and lint code with ruff
task static-check     # Type safety validation with pyright
task doc-serve        # Live pdoc documentation server
task doc-build        # Build static pdoc API docs with search
task doc-publish      # Publish API docs to GitHub Pages

# Quality assurance
task test-report      # Detailed coverage report with HTML output
task mut-report       # Cosmic ray mutation testing (optional)

# Enhanced CLI Commands
# Multi-source processing with deduplication
python -m disaster_surveillance_reporter.cli full-cycle \
  --sources gdacs,promed,reliefweb \
  --storage jsonl,sqlite \
  --duplicate-threshold 0.8

# Individual pipeline stages  
python -m disaster_surveillance_reporter.cli fetch --sources gdacs,news
python -m disaster_surveillance_reporter.cli enhance --input incidents.jsonl
python -m disaster_surveillance_reporter.cli store --storage email,sheets
python -m disaster_surveillance_reporter.cli status --detailed

# Optional end-to-end tests with real APIs
task test-e2e  # Real API calls - not automated
```

## 🎯 Project Structure

```
src-disaster-awareness/
├── disaster_surveillance_reporter/        # Main application package
│   ├── adapters/                         # Source adapters (GDACS, ProMED, etc.)
│   │   ├── __init__.py
│   │   ├── _types.py                     # Shared types and protocols
│   │   ├── gdacs.py                      # GDACS disaster adapter
│   │   ├── promed.py                     # ProMED disease adapter  
│   │   ├── reliefweb.py                  # ReliefWeb humanitarian adapter
│   │   ├── healthmap.py                  # HealthMap disease surveillance
│   │   └── who.py                        # WHO emergency adapter
│   ├── classification/                   # Rule-based classification
│   │   └── __init__.py
│   ├── storage/                          # Storage backends
│   │   ├── __init__.py
│   │   ├── jsonl.py                      # JSONL date-based storage
│   │   ├── email_reporter.py             # Email backend  
│   │   └── google_sheets.py              # Google Sheets backend
│   ├── pipeline/                         # Pipeline orchestration
│   │   └── __init__.py
│   ├── opencode/                         # OpenCode AI integration
│   │   └── __init__.py
│   ├── cli.py                            # Command-line interface
│   └── __init__.py                       # Package initialization
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
├── scripts/                              # Validation and utility scripts
├── docs/                                 # Documentation (api/, tests/, coverage/)
├── main.py                               # Test entry point
├── TODO.md                               # Development roadmap & session state
├── AGENTS.md                             # Agent configuration
├── Dockerfile                            # Multi-stage container build
├── uv.lock                               # UV dependency lock file
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
**Project:** [src-disaster-awareness](https://github.com/nullhack/src-disaster-awareness)  
**Documentation:** [nullhack.github.io/src-disaster-awareness](https://nullhack.github.io/src-disaster-awareness)

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/nullhack/src-disaster-awareness.svg?style=for-the-badge
[contributors-url]: https://github.com/nullhack/src-disaster-awareness/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/nullhack/src-disaster-awareness.svg?style=for-the-badge
[forks-url]: https://github.com/nullhack/src-disaster-awareness/network/members
[stars-shield]: https://img.shields.io/github/stars/nullhack/src-disaster-awareness.svg?style=for-the-badge
[stars-url]: https://github.com/nullhack/src-disaster-awareness/stargazers
[issues-shield]: https://img.shields.io/github/issues/nullhack/src-disaster-awareness.svg?style=for-the-badge
[issues-url]: https://github.com/nullhack/src-disaster-awareness/issues
[license-shield]: https://img.shields.io/badge/license-MIT-green?style=for-the-badge
[license-url]: https://github.com/nullhack/src-disaster-awareness/blob/main/LICENSE