"""Windows editing shortcuts based on virtual-key codes, independent of layout."""
import sys
import tkinter as tk
from tkinter import ttk


class EntryHistory:
    def __init__(self, entry):
        self.entry = entry
        self.variable = tk.StringVar(master=entry, name=entry.cget('textvariable'))
        self.values = [entry.get()]
        self.index = 0
        self.restoring = False
        self.trace = self.variable.trace_add('write', self.changed)
        entry.bind('<Destroy>', self.close, add='+')

    def close(self, event):
        if event.widget is self.entry:
            self.variable.trace_remove('write', self.trace)

    def changed(self, *_):
        if self.restoring:
            return
        value = self.variable.get()
        if self.entry.focus_get() is not self.entry:
            self.values, self.index = [value], 0
        elif value != self.values[self.index]:
            self.values = (self.values[:self.index + 1] + [value])[-100:]
            self.index = len(self.values) - 1

    def move(self, direction):
        if str(self.entry.cget('state')) != 'normal':
            return
        target = self.index + direction
        if 0 <= target < len(self.values):
            self.index = target
            self.restoring = True
            try:
                self.variable.set(self.values[target])
                self.entry.selection_clear()
                self.entry.icursor('end')
            finally:
                self.restoring = False


def install_shortcuts(root, open_file):
    histories = {}

    def handle(event):
        # Windows keycode is VK_A/VK_C/... even with the Russian layout active.
        if event.state & (0x8 | 0x20000):  # Alt / AltGr: do not steal these keys.
            return
        key = chr(event.keycode).lower() if sys.platform == 'win32' and 65 <= event.keycode <= 90 else event.keysym.lower()
        if key == 'o':
            open_file()
            return 'break'
        widget = event.widget
        if not isinstance(widget, (tk.Entry, ttk.Entry, tk.Text)):
            return
        if key == 'a':
            if isinstance(widget, tk.Text):
                widget.tag_add('sel', '1.0', 'end-1c')
            else:
                widget.selection_range(0, 'end')
                widget.icursor('end')
            return 'break'
        virtual = {'c': '<<Copy>>', 'v': '<<Paste>>', 'x': '<<Cut>>'}
        if key in virtual:
            widget.event_generate(virtual[key])
            return 'break'
        if key in ('z', 'y'):
            redo = key == 'y' or bool(event.state & 1)
            if widget in histories:
                histories[widget].move(1 if redo else -1)
            else:
                widget.event_generate('<<Redo>>' if redo else '<<Undo>>')
            return 'break'

    tag = 'FaceitShortcuts' + str(id(root))
    root.bind_class(tag, '<Control-KeyPress>', handle)

    def register(widget):
        if isinstance(widget, (tk.Entry, ttk.Entry, tk.Text)):
            # Run before Entry's class bindings so paste/cut never happens twice.
            widget.bindtags((tag,) + widget.bindtags())
            if isinstance(widget, (tk.Entry, ttk.Entry)):
                histories[widget] = EntryHistory(widget)
        for child in widget.winfo_children():
            register(child)

    register(root)
    root.bind('<Control-KeyPress>', handle)
    return handle  # Also enables deterministic tests with non-Latin keysyms.
