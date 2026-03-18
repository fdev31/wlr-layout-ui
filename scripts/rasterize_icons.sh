#!/bin/sh
# Rasterize SVG icons to PNG for wlr-layout-ui profile action buttons.
# Requires: rsvg-convert (from librsvg)
#
# Usage: ./scripts/rasterize_icons.sh
#
# SVG sources are read from scripts/icon_*.svg and written to
# src/wlr_layout_ui/icons/ as 64x64 RGBA PNGs.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SVG_DIR="$SCRIPT_DIR"
OUT_DIR="$PROJECT_DIR/src/wlr_layout_ui/icons"

mkdir -p "$OUT_DIR"

for svg in "$SVG_DIR"/icon_*.svg; do
    name="$(basename "$svg" .svg)"
    name="${name#icon_}"
    out="$OUT_DIR/${name}.png"
    rsvg-convert -w 64 -h 64 "$svg" -o "$out"
    echo "  $svg -> $out"
done

echo "Done."
