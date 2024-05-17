# Wlr layout UI

An simple GUI to setup the screens layout on wlroots based systems and X11 (using xrandr), Hyprland is the first class user.

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

- Python: pyglet, tomli, tomli-w
- wlr-randr (if not using Hyprland >= 0.37)
- xrandr (for X11 support)

## Installation

Check your distro for the package:

[![Packaging status](https://repology.org/badge/vertical-allrepos/wlr-layout-ui.svg)](https://repology.org/project/wlr-layout-ui/versions)

or install with pip in a virtual environment:

```
python -m venv myenv
./myenv/bin/pip install wlr-layout-ui
```

This will create a "myenv" folder with the app installed.
You will need to run the app with the full path to it (/path/to/myenv/bin/wlrlui).

## Usage

### Start the GUI

```
wlrlui
```

Note that a `.desktop` file is provided in the `files` folder for an easy integration to your environment.

### List available profiles (CLI)

```
wlrlui -l
```

### Load a profile

To load the profile called "cinema":

```
wlrlui cinema
```

### Magic layout

Applies the first profile matching the set of monitors which are currently active:

```
wlrlui -m
```

### GUI shortcuts

- `ENTER`: apply the current settings
- `ESC`: close the app
- `TAB`: switch between profiles
