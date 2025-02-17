#!/usr/bin/python3

from signal import signal, SIGCHLD, SIG_IGN
from subprocess import Popen, DEVNULL
from dataclasses import dataclass
from operator import attrgetter
from shlex import split
import curses
import sys
import os

from xdg.BaseDirectory import xdg_data_home
from xdg.DesktopEntry import DesktopEntry
from natsort import natsorted
from validators import url

__version__ = "0.1"

D_ENTRY_EXT = ".desktop"

# https://specifications.freedesktop.org/desktop-entry-spec/latest/exec-variables.html
FIELD_CODES_IGNORED = ("%i", "%c", "%k")

APPS_DIRS = (
    os.path.join(xdg_data_home, "applications"),
    "/usr/share/applications",
    "/usr/local/share/applications",
)


def fixed_len_slice(data, max_len, offset=0):
    data_len = len(data)
    if data_len <= max_len:
        return data
    offset = max(0, min(offset, data_len - max_len))
    return data[offset : max_len + offset]


def is_url(absolute_url):
    return url(absolute_url) == True


def is_desktop_file(path):
    return os.path.isfile(path) and (path[-len(D_ENTRY_EXT) :] == D_ENTRY_EXT)


def exec_nonblocking(cmd):
    p = Popen(split(cmd), stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL, start_new_session=True)
    return p.pid


def edit_units(units):
    units_list = []
    for u in units:
        units_list.append("".join(('"', u, '"')))
    return " ".join(units_list)


def edit_exec_cmd(cmd, paths, urls):
    cmd_splitted = cmd.split()
    cmd_edited = []
    for c in cmd_splitted:
        if c in FIELD_CODES_IGNORED:
            continue
        if c == "%f":
            if not paths:
                continue
            cmd_edited.append(edit_units(paths[0:1]))
        elif c == "%F":
            if not paths:
                continue
            cmd_edited.append(edit_units(paths))
        elif c == "%u":
            if not paths and not urls:
                continue
            cmd_edited.append(edit_units((*urls, *paths)[0:1]))
        elif c == "%U":
            if not paths and not urls:
                continue
            cmd_edited.append(edit_units((*urls, *paths)))
        else:
            cmd_edited.append(c)
    return " ".join(cmd_edited)


@dataclass
class DEntry:
    terminal: bool
    path: str
    name: str
    comment: str
    exec_cmd: str


class RelevantEntries:
    def __init__(self, dirs):
        self.dirs, self.entries = dirs, []

    def sort_by_name(self, reverse=False):
        self.entries = natsorted(self.entries, key=attrgetter("name"), reverse=reverse)

    def update(self, visibility=True):
        hidden_basenames = []
        self.entries *= 0

        for d in self.dirs:
            try:
                f_list = os.listdir(d)
            except FileNotFoundError:
                continue
            except NotADirectoryError:
                continue

            for f in f_list:
                fp = os.path.join(d, f)
                if not is_desktop_file(fp):
                    continue

                de = DesktopEntry(fp)

                if visibility:
                    if de.getNoDisplay() or de.getHidden():
                        hidden_basenames.append(f)
                        continue

                dentry = DEntry(
                    terminal=de.getTerminal(),
                    path=os.path.abspath(fp),
                    name=de.getName(),
                    comment=de.getComment(),
                    exec_cmd=de.getExec(),
                )

                if self.find_index_by_basename(f) == -1 and f not in hidden_basenames:
                    self.entries.append(dentry)

    def find_index_by_basename(self, basename):
        return next(
            (
                i
                for i, dentry in enumerate(self.entries)
                if os.path.basename(dentry.path) == basename
            ),
            -1,
        )

    def find_index_by_name(self, name):
        return next((i for i, dentry in enumerate(self.entries) if dentry.name == name), -1)

    def longest_name_num(self):
        n = 0
        for e in self.entries:
            n = max(n, len(e.name))
        return n


class Interface:
    UNUSED_LINES = 3
    LIST_START = 1

    def __init__(self, dirs, paths, urls, term_cmd):
        self.paths, self.urls, self.term_cmd = paths, urls, term_cmd

        self.entries = RelevantEntries(dirs)
        self.entries.update()
        self.entries.sort_by_name()

        self.longest_name = self.entries.longest_name_num()

        self.cursor, self.offset = 0, 0

        self.window = curses.initscr()
        self.window.keypad(True)
        curses.curs_set(0)
        curses.noecho()
        curses.start_color()
        curses.use_default_colors()

        self.refresh_sizes()

    def refresh_sizes(self):
        curses.update_lines_cols()
        self.avail_lines = curses.LINES - self.UNUSED_LINES
        self.avail_lines_i = self.avail_lines - 1

    def draw(self):
        line_num = self.LIST_START
        for i, e in enumerate(fixed_len_slice(self.entries.entries, self.avail_lines, self.offset)):
            self.window.addstr(
                line_num,
                max(0, (curses.COLS // 2) - (self.longest_name // 2)),
                fixed_len_slice(e.name, curses.COLS, 0),
                curses.A_REVERSE if i == self.cursor else curses.color_pair(0),
            )

            if i == self.cursor:
                try:
                    info = []
                    if e.terminal:
                        info.append("Terminal-based;")
                    info.append("No desc." if not e.comment else e.comment)
                    self.window.addstr(
                        curses.LINES - 1, 0, fixed_len_slice(" ".join(info), curses.COLS, 0)
                    )
                except curses.error:
                    pass

            line_num += 1

        if not len(self.entries.entries):
            msg = " No entries! "
            self.window.addstr(
                curses.LINES // 2,
                max(0, (curses.COLS // 2) - (len(msg) // 2)),
                fixed_len_slice(msg, curses.COLS, 0),
                curses.A_REVERSE,
            )

    def set_cursor(self, index):
        list_i = len(self.entries.entries) - 1

        if index < 0 or index > list_i:
            self.cursor, self.offset = 0, 0
            return

        # First page:
        if 0 <= index <= self.avail_lines_i:
            self.cursor = index
            self.offset = 0
            return

        # Last page:
        lastpage_first_i = list_i - self.avail_lines_i
        if (lastpage_first_i + 2) <= index <= list_i:
            self.cursor = self.avail_lines_i - (list_i - index)
            self.offset = index - self.cursor
            return

        # To the middle:
        self.cursor = self.avail_lines // 2
        rema = self.avail_lines - self.cursor
        self.offset = index - rema
        if self.cursor != rema:
            self.offset += 1

    def input_down(self):
        if (self.cursor + self.offset) == (len(self.entries.entries) - 1):
            self.set_cursor(0)
            return

        self.cursor += 1
        if self.cursor > self.avail_lines_i:
            self.cursor = self.avail_lines_i
            self.offset += 1

    def input_up(self):
        if not (self.cursor + self.offset):
            self.set_cursor(len(self.entries.entries) - 1)
            return

        self.cursor -= 1
        if self.cursor < 0:
            self.cursor = 0
            self.offset -= 1

    def input(self):
        ch = self.window.getch()

        if not len(self.entries.entries) and ch != curses.KEY_RESIZE:
            return True

        if ch == curses.KEY_RESIZE:
            self.refresh_sizes()
            self.set_cursor(self.cursor + self.offset)
        elif ch == curses.KEY_DOWN:
            self.input_down()
        elif ch == curses.KEY_UP:
            self.input_up()
        elif ch in (curses.KEY_ENTER, ord("\n"), curses.KEY_RIGHT):
            exec_nonblocking(self.edit_current_cmd())
            return True
        else:
            return True
        return False

    def edit_current_cmd(self):
        e = self.entries.entries[self.cursor + self.offset]

        if e.terminal:
            return " ".join(
                (
                    self.term_cmd,
                    "".join(("'", edit_exec_cmd(e.exec_cmd, self.paths, self.urls), "'")),
                )
            )
        return edit_exec_cmd(e.exec_cmd, self.paths, self.urls)

    def loop(self):
        while 1:
            self.window.erase()
            self.draw()
            self.window.refresh()
            if self.input():
                break

    def run(self):
        try:
            self.loop()
        except KeyboardInterrupt:
            pass
        finally:
            curses.endwin()


ENV_USR_APPS_DIRS = os.getenv("LNCH_APPS_DIRS", "")
ENV_TERM_CMD = os.getenv("LNCH_TERM_CMD", "foot")

if __name__ == "__main__":
    signal(SIGCHLD, SIG_IGN)  # Prevents the formation of zombie processes.

    paths, urls = [], []
    for u in sys.argv[1:]:
        if is_url(u):
            urls.append(u)
        else:
            paths.append(u)  # hopefully paths

    usr_apps_dirs = []
    for d in ENV_USR_APPS_DIRS.split(":"):
        if os.path.isdir(d):
            usr_apps_dirs.append(d)

    app = Interface(usr_apps_dirs if usr_apps_dirs else APPS_DIRS, paths, urls, ENV_TERM_CMD)
    app.run()