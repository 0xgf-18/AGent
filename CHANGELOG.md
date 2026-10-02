# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Folder path exception in intake gate (searches for APKs in provided folder)
- LICENSE (MIT)
- CONTRIBUTING.md
- CHANGELOG.md
- SECURITY.md
- .env.example
- requirements-dev.txt
- pyproject.toml
- Makefile
- GitHub issue and PR templates
- GitHub Actions CI workflow
- Pre-commit hooks configuration
- Development documentation (SETUP.md, USAGE.md, API.md, ARCHITECTURE.md)

### Changed
- Renamed `.kb/` → `.agent/`
- Renamed `docs/` → `documentation/`
- Renamed `knowledge_base/` → `vault/`
- Renamed `knowledge_base/graph/` → `vault/visualizer/`
- Renamed `knowledge_base/raw/` → `vault/inbox/`
- Renamed `knowledge_base/wiki/` → `vault/articles/`
- Renamed `scripts/` → `tools/`
- Renamed `scripts/packers/` → `tools/unpackers/`

## [1.0.0] - 2026-10-02

### Added
- Initial release
- Master orchestrator (AGENTS.md) with intake gate and mode dispatcher
- Knowledge base with 5 packer articles, 5 technique articles, 3 experiment records
- 15 tool registry entries
- APK unpacking fast-path scripts
- Verification gate system
- Knowledge graph visualizer
- Crawl, fingerprint, and record scripts
