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
| name           | default value |
| -------------- | ------------- |
| LNCH_APPS_DIRS | *empty*       |
| LNCH_TERM_CMD  | "foot"        |

### Usage:
```bash
lnch
lnch .
lnch screenshot.png
```