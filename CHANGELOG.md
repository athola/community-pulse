# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.7] - 2025-12-24

### Fixed
- Deploy: Use REST API for uploads to control MIME types (Supabase Storage rejects charset suffix)
- Deploy: Align dry-run upload test with actual deploy method

## [0.1.6] - 2025-12-24

### Fixed
- Deploy: Use Storage REST API for bucket creation (SQL inserts don't register with Storage service)
- Deploy: Add proper bucket verification via REST API before uploads
- Deploy: Remove unreliable `supabase storage ls --experimental` checks
- Deploy: Add comprehensive dry-run validation

## [0.1.5] - 2025-12-23

### Changed
- Use true co-occurrence edges from shared posts in graph analysis

### Fixed
- CI: Use SQL for bucket creation and handle init messages
- CI: Handle errexit properly in storage bucket checks
- CI: Add --experimental flag to supabase storage ls commands
- CI: Apply same error handling fix to deploy-dry-run.yml

## [0.1.4] - 2025-12-22

### Fixed
- CI: Add error context for db migrations and storage bucket checks

## [0.1.3] - 2025-12-22

### Changed
- Replace hardcoded check names with regex pattern in CI

### Fixed
- CI: Improve error messages for version extraction and Supabase deployments
- CI: Create storage bucket before upload
- CI: Address PR review feedback

## [0.1.2] - 2025-12-22

### Changed
- Move pulse thresholds to Pydantic Settings config module

### Fixed
- CI: Add --experimental flag to supabase storage cp command
- Address PR review feedback for config validation

## [0.1.1] - 2025-12-20

### Added
- Release automation workflow
- Supabase local development support
- GitHub Actions CI/CD pipeline

### Fixed
- CI: Address PR review security and reliability issues

## [0.1.0] - 2025-12-16

### Added
- Initial POC implementation
- Velocity-based trend detection algorithm
- Co-occurrence graph analysis using rustworkx
- FastAPI backend with rate limiting
- React frontend with TailwindCSS
- Docker Compose development environment
- Comprehensive test suite with 95% coverage

### Fixed
- Replace global singleton with @cache decorator in snapshot_store
- Critical security and reliability issues from PR review

[Unreleased]: https://github.com/athola/community-pulse/compare/v0.1.5...HEAD
[0.1.5]: https://github.com/athola/community-pulse/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/athola/community-pulse/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/athola/community-pulse/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/athola/community-pulse/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/athola/community-pulse/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/athola/community-pulse/releases/tag/v0.1.0
