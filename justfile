# Default: list available recipes
default:
    @just --list

# Run the main application
run:
    uv run wlrlui

# Run the demo (programmatic)
demo:
    uv run python demo.py

# Run the TOML demo
demo-toml:
    uv run python demo_toml.py

# Run tests
test:
    uv run pytest

# Lint with ruff
lint:
    uv run ruff check --fix src/

# Format with ruff
fmt:
    uv run ruff format src/

# Type check with mypy
typecheck:
    uv run mypy src/

# Regenerate PNG icons from SVG sources
icons:
    ./scripts/rasterize_icons.sh

# Build the package
build:
    uv build

# Clean build artifacts
clean:
    rm -rf dist/ build/ *.egg-info src/*.egg-info

# Update the AUR wlr-layout-ui package to a released version (default: pyproject version)
aur version="":
    #!/usr/bin/env bash
    set -euo pipefail
    cd "$(git rev-parse --show-toplevel)"

    version="{{ version }}"
    if [ -z "$version" ]; then
        version=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -n 1)
    fi

    workdir=$(mktemp -d)
    trap 'rm -rf "$workdir"' EXIT
    # ssh, not https: the AUR https endpoint is read-only
    git clone -q ssh://aur@aur.archlinux.org/wlr-layout-ui.git "$workdir/aur"
    cd "$workdir/aur"

    # The tarball must exist upstream before the checksum can be computed
    url="https://github.com/fdev31/wlr-layout-ui/archive/refs/tags/${version}.tar.gz"
    if ! curl -fsL "$url" -o src.tar.gz; then
        echo "ERROR: no release tarball for ${version} at ${url}"
        exit 1
    fi
    sum=$(sha256sum src.tar.gz | cut -d' ' -f1)
    rm -f src.tar.gz

    sed -i -E \
        -e "s|^pkgver=.*|pkgver=${version}|" \
        -e "s|^pkgrel=.*|pkgrel=1|" \
        -e "s|^sha256sums=.*|sha256sums=('${sum}')|" \
        PKGBUILD
    makepkg --printsrcinfo > .SRCINFO

    if [ -z "$(git status --porcelain)" ]; then
        echo "AUR already up to date for ${version}"
        exit 0
    fi

    git diff --stat
    git add PKGBUILD .SRCINFO
    git commit -q -m "Update to ${version}"
    git push -q
    echo "AUR wlr-layout-ui updated to ${version}"

# Release: run all checks, bump version, tag, publish to PyPI, create GitHub release
release:
    #!/usr/bin/env bash
    set -euo pipefail
    cd "$(git rev-parse --show-toplevel)"

    # Ensure clean working tree
    if [ -n "$(git status --porcelain)" ]; then
        echo "ERROR: Working tree is not clean. Commit or stash changes first."
        exit 1
    fi

    # Show current version, prompt for new one
    ver_line=$(grep '^version' pyproject.toml | head -n 1)
    echo "Current: $ver_line"
    echo -n "New version: "
    read -r version

    # Run all checks
    uv run ruff check src/
    uv run ruff format --check src/
    uv run mypy

    # Bump version in pyproject.toml, commit, tag
    sed -i "s#${ver_line}#version = \"${version}\"#" pyproject.toml
    git add pyproject.toml
    git commit -m "Version ${version}" --no-verify
    git tag -a "${version}" -m "${version}"

    # Push commit + tag
    git push
    git push --tags

    # Build and publish to PyPI
    rm -rf dist/
    uv build
    uv publish

    # Create GitHub release with auto-generated notes from git log
    prev_tag=$(git tag --sort=-v:refname | sed -n '2p')
    if [ -n "$prev_tag" ]; then
        notes=$(git log --oneline "${prev_tag}..${version}" --no-decorate)
    else
        notes="Initial release"
    fi

    TOKEN=$(gopass show -o websites/api.github.com/fdev31)
    URL=https://api.github.com/repos/fdev31/wlr-layout-ui

    curl -sf -X POST "$URL/releases" \
        -H "Accept: application/vnd.github+json" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        -d @- <<EOF
    {
      "tag_name": "${version}",
      "name": "${version}",
      "body": $(echo "$notes" | jq -Rs .),
      "draft": false,
      "prerelease": false
    }
    EOF

    echo ""
    echo "Released ${version}"

    # Keep the AUR package in sync
    just aur "${version}"
