import tkinter as tk
import unittest
from types import SimpleNamespace
from keyboard_shortcuts import install_shortcuts

class ShortcutTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.var = tk.StringVar(value='текст')
        self.entry = tk.Entry(self.root, textvariable=self.var)
        self.entry.pack()
        self.opened = 0
        self.handle = install_shortcuts(self.root, self.open_file)
        self.root.update()
        self.entry.focus_force()
        self.root.update()
    def open_file(self):
        self.opened += 1
    def key(self, vk, keysym, state=4):
        return self.handle(SimpleNamespace(widget=self.entry, keycode=vk, keysym=keysym, state=state))
    def tearDown(self):
        self.root.destroy()
    def test_russian_copy_cut_paste_select(self):
        self.assertEqual(self.key(65, 'Cyrillic_ef'), 'break')
        self.assertEqual(self.entry.index('sel.first'), 0)
        self.assertEqual(self.entry.index('sel.last'), 5)
        self.key(67, 'Cyrillic_es')
        self.assertEqual(self.root.clipboard_get(), 'текст')
        self.key(88, 'Cyrillic_che')
        self.assertEqual(self.var.get(), '')
        self.key(86, 'Cyrillic_em')
        self.assertEqual(self.var.get(), 'текст')
    def test_undo_redo_and_open(self):
        self.entry.insert('end', '123')
        self.key(90, 'Cyrillic_ya')
        self.assertEqual(self.var.get(), 'текст')
        self.key(89, 'Cyrillic_en')
        self.assertEqual(self.var.get(), 'текст123')
        self.key(90, 'Cyrillic_ya')
        self.key(90, 'Cyrillic_YA', 5)
        self.assertEqual(self.var.get(), 'текст123')
        self.key(79, 'Cyrillic_shcha')
        self.assertEqual(self.opened, 1)
        self.key(79, 'Cyrillic_shcha', 12)
        self.assertEqual(self.opened, 1)
    def test_real_binding_no_double_paste(self):
        self.var.set('')
        self.root.clipboard_clear(); self.root.clipboard_append('one')
        self.entry.event_generate('<Control-KeyPress>', keycode=86)
        self.root.update()
        self.assertEqual(self.var.get(), 'one')
        self.entry.event_generate('<Control-KeyPress>', keycode=65)
        self.root.update()
        self.assertTrue(self.entry.selection_present())
    def test_disabled_entry_unchanged(self):
        self.entry.configure(state='disabled')
        self.key(88, 'Cyrillic_che')
        self.key(90, 'Cyrillic_ya')
        self.assertEqual(self.var.get(), 'текст')

if __name__ == '__main__': unittest.main()
