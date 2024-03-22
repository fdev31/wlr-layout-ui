# Wlr layout UI

An simple GUI to setup the screens layout on wlroots based systems.

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
