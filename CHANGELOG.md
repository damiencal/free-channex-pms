# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-03-02

### Added

- Multi-platform booking ingestion from Airbnb, VRBO, RVshare, and Mercury bank exports
- Double-entry accounting engine with chart of accounts, journal entries, and automated revenue recognition
- Financial reporting: profit & loss, balance sheet, and income statement with period filtering (YTD, year, quarter, month, date range)
- Resort compliance automation: PDF form filling, email submission, urgency tracking, and operator approval workflow
- Guest communication orchestration: welcome messages and pre-arrival messages with platform-aware delivery (Airbnb native, VRBO/RVshare operator-assisted)
- Interactive React dashboard with financial metrics, occupancy charts, booking calendar, and action items
- Natural language query interface powered by local Ollama (text-to-SQL with streaming narrative response)
- Config-driven architecture: YAML property configs, Jinja2 message templates, JSON PDF field mappings
- Docker Compose deployment with PostgreSQL and automatic database migrations
- CLI management tool (`manage.py`) for interactive property setup

[1.0.0]: https://github.com/captainarcher/roost/releases/tag/v1.0.0
[Unreleased]: https://github.com/captainarcher/roost/compare/v1.0.0...HEAD
