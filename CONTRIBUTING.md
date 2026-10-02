# Contributing to AGent

Thank you for your interest in contributing to AGent! This document provides guidelines for contributing.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/0xgf-18/AGent/issues)
2. If not, create a new issue using the [Bug Report Template](https://github.com/0xgf-18/AGent/issues/new?template=bug_report.md)
3. Include as much detail as possible:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Environment (OS, Python version, etc.)

### Requesting Features

1. Check if the feature has already been requested
2. Create a new issue using the [Feature Request Template](https://github.com/0xgf-18/AGent/issues/new?template=feature_request.md)
3. Describe the feature and its use case

### Pull Requests

1. Fork the repository
2. Create a new branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Write or update tests
5. Ensure all tests pass
6. Commit your changes (`git commit -m "Add your feature"`)
7. Push to your fork (`git push origin feature/your-feature`)
8. Create a Pull Request

## Code Style

- **Python**: Follow PEP 8, use type hints, docstrings for all functions
- **Markdown**: Use consistent heading levels, code blocks with language tags
- **Commit Messages**: Use conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)

## Development Setup

```bash
# Clone the repo
git clone https://github.com/0xgf-18/AGent.git
cd AGent

# Set up Python environment
python -m venv .agent/scripts/.venv
. .agent/scripts/.venv/bin/activate  # Linux/Mac
# .agent/scripts\.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r .agent/scripts/requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linting
ruff check .
mypy .
```

## Project Structure

```
AGent/
├── .agent/              # Agent firmware (rules, protocols, schemas, scripts)
├── documentation/       # Documentation assets
├── knowledge_base/      # The KB (articles, inbox, visualizer)
├── tools/               # Tools (unpackers)
├── AGENTS.md            # Master orchestrator
├── README.md            # Project overview
└── CONTRIBUTING.md      # This file
```

## Questions?

Open an issue or start a [discussion](https://github.com/0xgf-18/AGent/discussions).
