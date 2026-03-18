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

# Release: run all checks, build, and publish to PyPI
release:
    #!/usr/bin/env bash
    set -euo pipefail
    # Ensure clean working tree
    if [ -n "$(git status --porcelain)" ]; then
        echo "ERROR: Working tree is not clean. Commit or stash changes first."
        exit 1
    fi
    # Run checks
    uv run ruff check src/
    uv run ruff format --check src/
    uv run mypy
    # Build and publish
    rm -rf dist/
    uv build
    uv publish
