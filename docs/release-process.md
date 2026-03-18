# Release Process

## Prerequisites

- All CI checks pass on `main`
- `CHANGELOG.md` is updated with the new version
- All features for this release are merged

## Steps

### 1. Update CHANGELOG.md

Move items from `[Unreleased]` to a new version section:

```markdown
## [0.2.0] - 2026-04-01

### Added
- New feature description

### Changed
- Change description
```

### 2. Commit the changelog

```bash
git add CHANGELOG.md
git commit -m "chore: prepare v0.2.0 release"
git push origin main
```

### 3. Wait for CI to pass

Verify at: https://github.com/baronblk/smart-home-app/actions

### 4. Create and push the tag

```bash
git tag -a v0.2.0 -m "v0.2.0 — brief release description"
git push origin v0.2.0
```

### 5. Verify the release

1. Check the Release workflow: https://github.com/baronblk/smart-home-app/actions
2. Verify the GitHub Release was created: https://github.com/baronblk/smart-home-app/releases
3. Verify the container image exists:
   ```bash
   docker pull ghcr.io/baronblk/smart-home-app:0.2.0
   ```

## Hotfix Releases

For critical fixes:

1. Fix on `main` directly (or via PR)
2. Bump patch version (e.g., `v0.1.1`)
3. Follow the same tag + push workflow

## Rollback

To rollback to a previous version:

```bash
docker pull ghcr.io/baronblk/smart-home-app:0.1.0
docker-compose up -d
```

Previous versions remain available in GHCR indefinitely.
