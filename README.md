# Wlr layout UI

An simple GUI to setup the screens layout on wlroots based systems and X11 (using xrandr), Hyprland is the first class user.

## Features

- Load and save profiles
- Set the screen settings
  - Layout: position, rotation and scale
  - Resolution
  - Refresh rate

> [!note]
> Non Hyprland should work without screen rotation or scaling support

## Video / Demo

A bit outdated, but still relevant.

[![Video](https://img.youtube.com/vi/bJxVIu9cMzg/0.jpg)](https://www.youtube.com/watch?v=bJxVIu9cMzg)

## Requires

- wlr-randr (if not using Hyprland >= 0.37)
- Python: pyglet, tomli

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
