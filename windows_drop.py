"""Windows Explorer file drops for Tk, without a runtime dependency."""
import ctypes
from ctypes import wintypes


class FileDrop:
    def __init__(self, root, events):
        self.root = root
        self.events = events
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.shell = ctypes.WinDLL("shell32", use_last_error=True)
        self.user.GetParent.argtypes = [wintypes.HWND]
        self.user.GetParent.restype = wintypes.HWND
        self.user.IsWindow.argtypes = [wintypes.HWND]
        self.user.IsWindow.restype = wintypes.BOOL
        self.user.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        self.user.SetWindowLongPtrW.restype = ctypes.c_void_p
        self.user.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                                            ctypes.c_size_t, ctypes.c_ssize_t]
        self.user.CallWindowProcW.restype = ctypes.c_ssize_t
        self.shell.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
        self.shell.DragAcceptFiles.restype = None
        self.shell.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
        self.shell.DragQueryFileW.restype = wintypes.UINT
        self.shell.DragFinish.argtypes = [wintypes.HANDLE]
        self.shell.DragFinish.restype = None
        root.update_idletasks()
        self.hwnd = self.user.GetParent(root.winfo_id()) or root.winfo_id()
        callback = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
                                     ctypes.c_size_t, ctypes.c_ssize_t)
        self.callback = callback(self.window_proc)
        ctypes.set_last_error(0)
        self.previous = self.user.SetWindowLongPtrW(self.hwnd, -4, ctypes.cast(self.callback, ctypes.c_void_p))
        if not self.previous:
            raise ctypes.WinError(ctypes.get_last_error())
        self.shell.DragAcceptFiles(self.hwnd, True)
        root.bind("<Destroy>", self.on_destroy, add="+")

    def window_proc(self, hwnd, message, wparam, lparam):
        if message == 0x0233:  # WM_DROPFILES
            try:
                paths = []
                count = self.shell.DragQueryFileW(wparam, 0xFFFFFFFF, None, 0)
                for index in range(count):
                    length = self.shell.DragQueryFileW(wparam, index, None, 0)
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    self.shell.DragQueryFileW(wparam, index, buffer, length + 1)
                    paths.append(buffer.value)
                self.events.put(("drop", paths))
            except Exception:
                self.events.put(("drop_error", "Не удалось открыть перетащенный файл."))
            finally:
                self.shell.DragFinish(wparam)
            return 0
        return self.user.CallWindowProcW(self.previous, hwnd, message, wparam, lparam)

    def on_destroy(self, event):
        if event.widget is self.root and self.previous and self.user.IsWindow(self.hwnd):
            self.shell.DragAcceptFiles(self.hwnd, False)
            self.user.SetWindowLongPtrW(self.hwnd, -4, self.previous)
            self.previous = None
