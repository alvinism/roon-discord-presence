# Releasing

Releases are published by `.github/workflows/release.yml` when a `v*` tag is pushed:
tests → build → PyPI → GitHub release (wheel, sdist and `Roon-Discord-Presence.alfredworkflow`).

## One-time setup

1. **PyPI trusted publisher** (no API token needed): on pypi.org → *Your account → Publishing →
   Add a new pending publisher*:
   - PyPI project name: `roon-discord-presence`
   - Owner: `alvinism`, repository: `roon-discord-presence`
   - Workflow: `release.yml`, environment: `pypi`
2. **GitHub environment**: repo → *Settings → Environments → New environment* named `pypi`
   (optionally require your approval before each publish).

## Each release

1. Bump `__version__` in `src/roon_discord_presence/__init__.py`.
2. Commit, then tag and push:
   ```sh
   git tag v0.1.0
   git push origin main v0.1.0
   ```
3. Watch the *Release* workflow; the release appears under GitHub Releases when it finishes.
