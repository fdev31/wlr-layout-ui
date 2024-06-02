# Wlr layout UI

An simple GUI to setup the screens layout.
Works best on Hyprland but should support most systems in a slightly degraded way
(Wayland and Xorg are supported via 3rd party applications)

## Features

- Load and save profiles
- No grid snapping, but anchors in a smart way on overlap
- Set the screen settings
  - Layout: position, rotation, scale and flipping
  - Resolution
  - Refresh rate
- Makes clean, easy to understand layouts, with no negative values of random offsets `</monk>`

> [!note]
> Non Hyprland should work without screen rotation or scaling support

## Video / Demo

A bit outdated, but still relevant.

[![Video](https://img.youtube.com/vi/bJxVIu9cMzg/0.jpg)](https://www.youtube.com/watch?v=bJxVIu9cMzg)

## Requires

- Python
  - pyglet
  - tomli
  - tomli-w
- One of:
  - Hyprland >= 0.37
  - wlr-randr (for other wayland systems)
  - xrandr (for X11 / Xorg)

## Installation

Check your distro for the package:

[![Packaging status](https://repology.org/badge/vertical-allrepos/wlr-layout-ui.svg)](https://repology.org/project/wlr-layout-ui/versions)

or install with pip in a virtual environment:

```bash
python -m venv myenv
./myenv/bin/pip install wlr-layout-ui
```

This will create a "myenv" folder with the app installed.
You will need to run the app with the full path to it (/path/to/myenv/bin/wlrlui).

## Usage

### Start the GUI

```bash
wlrlui
```

Note that a `.desktop` file is provided in the `files` folder for an easy integration to your environment.

### List available profiles (CLI)

```bash
wlrlui -l
```

### Load a profile

To load the profile called "cinema":

```bash
wlrlui cinema
```

### Magic layout

_added in 1.6.11_

Applies the first profile (in alphabetical order) matching the set of monitors which are currently active:

```bash
wlrlui -m
```

### GUI shortcuts

- `ENTER`: apply the current settings
- `ESC`: close the app
- `TAB`: switch between profiles
