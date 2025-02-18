# Code of Conduct for pydantic-settings-export

## Project Context

This is a personal project developed and maintained during personal time.
While we strive for quality and responsiveness, specific resolution timelines can't be guaranteed.

## Communication & Contributions

### Primary Communication Channel

GitHub Issues are **required** as the first point of contact for:

- Bug reports
- Feature requests
- Documentation improvements
- General questions

### Secondary Contact Methods

Only after creating an issue, contributors may use:

- GitHub anonymous email: `30597878+jag-k@users.noreply.github.com`
- Other contact methods listed on the maintainer's GitHub profile

## Development Priorities

1. Bug fixes
2. Features from Roadmap:
   - Issues with the closest milestone
   - General milestone issues
   - General issues with label `bug` or `feature request`
   - Features listed in README.md
3. New feature proposals

## Contribution Guidelines

### Issue Creation

All contributions must start with a GitHub issue to:
- Track the proposed changes
- Discuss implementation details
- Document decisions

### Branch Naming Convention

- Format: `<domain>/<issue-number>-<short-description>`
- Domains:
  - `fix/` for bug fixes
  - `feature/` for new features
- Example: `feature/6-inject-config-to-markdown`

### Pull Requests Requirements

1. Must reference an existing issue
2. Must pass GitHub Actions checks
3. Must include changelog in PR description

### CI/CD Process

The project uses GitHub Actions for:

- Code linting
- Testing
- Building
- Publishing to PyPI (triggered by tags)

Version numbering:

- GitHub tags/releases: prefixed with `v` (e.g., `v1.0.0`)
- PyPI versions: no prefix (e.g., `1.0.0`)

## Documentation Structure

- Primary documentation maintained in GitHub Wiki
- README.md contains essential information and roadmap
- Milestones track planned development
- PR descriptions serve as changelog entries

## Platform Guidelines

### GitHub Interactions

Use [GitHub Issues][gh-issues] or [GitHub Discussions][gh-discussions] for:

- Feature brainstorming
- Documentation questions
- Roadmap suggestions

### PyPI Considerations

- Package versions follow [SemVer](https://semver.org)
- Security reports should use GitHub Issues
- Package publishing is automated through GitHub Actions

## Enforcement

### GitHub-Specific Sanctions

- Repository access revocation
- Issue/PR commenting restrictions
- Forking restrictions for severe cases

### PyPI Security

Malicious package versions will be:

1. Reported to [PyPI Security](mailto:security@pypi.org)
2. Yanked within 24 hours of confirmation
3. Documented in GitHub Issues

## Adaptations

This Code of Conduct combines elements from:

- [Contributor Covenant 2.1](https://www.contributor-covenant.org)
- [GitHub Community Guidelines](https://docs.github.com/en/site-policy/github-terms/github-community-guidelines)

---

**Version**: 1.0 \
**Effective Date**: Immediately upon merging \
**Project Wiki**: [General docs][gh-wiki]

[gh-issues]: https://github.com/jag-k/pydantic-settings-export/issues
[gh-discussions]: https://github.com/jag-k/pydantic-settings-export/discussions
[gh-wiki]: https://github.com/jag-k/pydantic-settings-export/wiki
