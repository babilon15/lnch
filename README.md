# Lnch
- simple application launcher for Linux (curses-based)

![screenshot](https://raw.githubusercontent.com/babilon15/lnch/main/screenshot.png)

### (Arch) dependencies:
- [python-validators](https://github.com/python-validators/validators)
- [python-natsort](https://github.com/SethMMorton/natsort)
- [python-pyxdg](https://freedesktop.org/wiki/Software/pyxdg)

```bash
pacman -Syu python-validators python-natsort python-pyxdg
```

### Environment variables:
| name           | default value | comment                                                                                         |
| -------------- | ------------- | ----------------------------------------------------------------------------------------------- |
| LNCH_APPS_DIRS | *empty*       | The paths are separated by `:`. If the variable is not empty, it overwrites the standard paths. |
| LNCH_TERM_CMD  | `foot`        |                                                                                                 |
| LNCH_AUTO_EXIT | `true`        |                                                                                                 |

### Usage:
```bash
lnch
lnch .
lnch screenshot.png
lnch "https://www.google.com"
```

### On Hyprland:
- `~/.config/hypr/hyprland.conf`

for example:

```
bind = SUPER, L, exec, foot --title=lnch ~/.local/bin/lnch
windowrulev2 = float, title:^(lnch)
windowrulev2 = center 1, title:^(lnch)
windowrulev2 = size 500 300, title:^(lnch)
```

After you press the SUPER and L keys, it looks like this:

![screenshot](https://raw.githubusercontent.com/babilon15/lnch/main/screenshot_floating.png)