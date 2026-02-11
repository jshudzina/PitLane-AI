# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-11

### Documentation

- Fix broken links and update PyPI badges ([#44](https://github.com/jshudzina/PitLane-AI/pull/44))

- Add mermaid diagrams and streamline architecture docs ([#45](https://github.com/jshudzina/PitLane-AI/pull/45))

- Update documentation for v0.1.3 features and refactoring ([#72](https://github.com/jshudzina/PitLane-AI/pull/72))


### Features

- Add temporal context system for F1 season awareness ([#36](https://github.com/jshudzina/PitLane-AI/pull/36))

- Add session resumption for conversations ([#47](https://github.com/jshudzina/PitLane-AI/pull/47))

- Add position changes tracking to f1-analyst skill ([#51](https://github.com/jshudzina/PitLane-AI/pull/51)) ([#60](https://github.com/jshudzina/PitLane-AI/pull/60))

- Implement standings data fetching commands ([#61](https://github.com/jshudzina/PitLane-AI/pull/61)) ([#66](https://github.com/jshudzina/PitLane-AI/pull/66))

- Add championship possibilities analysis to f1-analyst skill ([#50](https://github.com/jshudzina/PitLane-AI/pull/50)) ([#68](https://github.com/jshudzina/PitLane-AI/pull/68))

- Add race-control skill for contextualizing F1 race events ([#59](https://github.com/jshudzina/PitLane-AI/pull/59)) ([#69](https://github.com/jshudzina/PitLane-AI/pull/69))


### Miscellaneous Tasks

- Add GitHub Actions workflow for automatic documentation deployment ([#41](https://github.com/jshudzina/PitLane-AI/pull/41))

- Fix dependency group in docs deployment workflow ([#43](https://github.com/jshudzina/PitLane-AI/pull/43))

- Update Python version requirement to 3.12-3.14 ([#73](https://github.com/jshudzina/PitLane-AI/pull/73))

- Lock file updates ([#74](https://github.com/jshudzina/PitLane-AI/pull/74))


### Refactor

- Code smell fixes base on #60 review ([#65](https://github.com/jshudzina/PitLane-AI/pull/65))

- Rename session to workspace and add uv-pytest skill ([#75](https://github.com/jshudzina/PitLane-AI/pull/75))


### Refactoring

- Rename scripts to commands and reorganize module structure ([#67](https://github.com/jshudzina/PitLane-AI/pull/67))


### Testing

- Add FastF1 integration tests with working fixtures ([#37](https://github.com/jshudzina/PitLane-AI/pull/37))

## [0.1.2.dev2] - 2026-02-02

### Miscellaneous Tasks

- Add PyPI READMEs and enable workflow commit signing ([#32](https://github.com/jshudzina/PitLane-AI/pull/32))

- Switch to GPG commit signing in version-bump workflow ([#33](https://github.com/jshudzina/PitLane-AI/pull/33))

## [0.1.1.dev0] - 2026-02-01

### Bug Fixes

- Use pd.notna() for proper pandas null checks in scripts ([#6](https://github.com/jshudzina/PitLane-AI/pull/6))

- Address critical security vulnerabilities and performance improvements ([#15](https://github.com/jshudzina/PitLane-AI/pull/15))

- Support pre-release versions in bump_version.py ([#17](https://github.com/jshudzina/PitLane-AI/pull/17))

- Add secure git-cliff installation with cargo ([#18](https://github.com/jshudzina/PitLane-AI/pull/18))


### Documentation

- Added minimal setup information to the README


### Features

- Add F1 data analysis MVP with chat interface

- Added an event schedule skill ([#3](https://github.com/jshudzina/PitLane-AI/pull/3))

- Add F1 driver information skill with Ergast API integration ([#5](https://github.com/jshudzina/PitLane-AI/pull/5))

- Add WebFetch tool with domain restrictions and OpenTelemetry tracing ([#8](https://github.com/jshudzina/PitLane-AI/pull/8))

- Implement workspace-based architecture with secure session management ([#9](https://github.com/jshudzina/PitLane-AI/pull/9))

- Add unique filenames for chart visualizations ([#12](https://github.com/jshudzina/PitLane-AI/pull/12))

- Add favicon ([#13](https://github.com/jshudzina/PitLane-AI/pull/13))

- Add lap time distribution visualization with violin plots ([#14](https://github.com/jshudzina/PitLane-AI/pull/14))

- Add automated release workflow ([#16](https://github.com/jshudzina/PitLane-AI/pull/16))

- Add speed trace overlay telemetry analysis ([#23](https://github.com/jshudzina/PitLane-AI/pull/23))


### Miscellaneous Tasks

- Ruff fixes ([#4](https://github.com/jshudzina/PitLane-AI/pull/4))

- Ignore warnings in the cli ([#7](https://github.com/jshudzina/PitLane-AI/pull/7))

- Add conventional commits pre-commit hook ([#19](https://github.com/jshudzina/PitLane-AI/pull/19))

- Add comprehensive PR checks workflow ([#20](https://github.com/jshudzina/PitLane-AI/pull/20))

- Create PR for version bump ([#21](https://github.com/jshudzina/PitLane-AI/pull/21))


### Refactoring

- Move agent loop to pitlane-agent and use ClaudeSDKClient

- Migrate CLI scripts from argparse to click with comprehensive tests

- Reorganize f1-analyst skill with progressive disclosure pattern ([#11](https://github.com/jshudzina/PitLane-AI/pull/11))

- Split release workflow into two-stage process ([#27](https://github.com/jshudzina/PitLane-AI/pull/27))

<!-- generated by git-cliff -->
