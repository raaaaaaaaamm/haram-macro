import sys
import threading
import time
from pynput.keyboard import Controller

keyboard = Controller()

class MacroEngine:
    def __init__(self):
        self.is_running = False
        self.config = None
        self.target_window = None
        self.threads = []
        self.stop_event = threading.Event()

    def start(self, config, target_window):
        if self.is_running:
            return
        self.config = config
        self.target_window = target_window
        self.is_running = True
        self.stop_event.clear()
        self.threads = []

        fixed_keys = config.get('fixed_keys', {})
        for k, info in fixed_keys.items():
            if info.get('enabled'):
                t = threading.Thread(target=self._key_loop, args=(k, info.get('interval', 1.0)))
                t.daemon = True
                self.threads.append(t)

        custom_keys = config.get('custom_keys', {})
        for k, info in custom_keys.items():
            if info.get('enabled') and info.get('key'):
                t = threading.Thread(target=self._key_loop, args=(info.get('key'), info.get('interval', 1.0)))
                t.daemon = True
                self.threads.append(t)

        if config.get('custom_text_enabled') and config.get('custom_text'):
            t = threading.Thread(target=self._text_loop, args=(config.get('custom_text'),))
            t.daemon = True
            self.threads.append(t)

        for t in self.threads:
            t.start()

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self.stop_event.set()
        self.threads = []

    def _key_loop(self, key_str, interval):
        while not self.stop_event.is_set():
            self._press_key(key_str, interval)
            time.sleep(interval)

    def _text_loop(self, text):
        while not self.stop_event.is_set():
            for char in text:
                if self.stop_event.is_set():
                    break
                self._press_key(char, 0.05)
                time.sleep(0.05)
            time.sleep(1.0)

    def _press_key(self, key_str, interval=0.1):
        if sys.platform == 'win32' and self.target_window:
            try:
                import ctypes, win32gui, win32con, win32process
                hwnd = self.target_window.get('hwnd')
                if hwnd:
                    # 1. Windows 11 Message Filter Unblock
                    try:
                        ctypes.windll.user32.ChangeWindowMessageFilterEx(hwnd, win32con.WM_KEYDOWN, 1, None)
                        ctypes.windll.user32.ChangeWindowMessageFilterEx(hwnd, win32con.WM_KEYUP, 1, None)
                        ctypes.windll.user32.ChangeWindowMessageFilterEx(hwnd, win32con.WM_CHAR, 1, None)
                    except Exception:
                        pass

                    vk = None
                    char_val = None

                    if len(key_str) == 1:
                        char_val = ord(key_str)
                        vk = ctypes.windll.user32.VkKeyScanW(char_val) & 0xFF
                    elif key_str.lower() in ['enter', '\r', '\n']:
                        vk = win32con.VK_RETURN
                    elif key_str.lower() == 'space':
                        vk = win32con.VK_SPACE
                    elif key_str.lower() == 'tab':
                        vk = win32con.VK_TAB

                    if vk:
                        scan_code = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
                        lparam_down = 1 | (scan_code << 16)
                        lparam_up = 1 | (scan_code << 16) | (1 << 30) | (1 << 31)

                        # 2. Windows 11 Thread Queue Linking (AttachThreadInput)
                        target_thread_id, _ = win32process.GetWindowThreadProcessId(hwnd)
                        current_thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

                        attached = False
                        if target_thread_id and target_thread_id != current_thread_id:
                            attached = ctypes.windll.user32.AttachThreadInput(current_thread_id, target_thread_id, True)

                        try:
                            hwnds = [hwnd]
                            def enum_child_proc(child_hwnd, extra):
                                if win32gui.IsWindowVisible(child_hwnd):
                                    hwnds.append(child_hwnd)
                                return True

                            try:
                                win32gui.EnumChildWindows(hwnd, enum_child_proc, None)
                            except Exception:
                                pass

                            hold_time = min(0.02, interval / 2.0)

                            for target_h in hwnds:
                                win32gui.PostMessage(target_h, win32con.WM_KEYDOWN, vk, lparam_down)
                                if char_val and 32 <= char_val <= 126:
                                    win32gui.PostMessage(target_h, win32con.WM_CHAR, char_val, lparam_down)

                            time.sleep(hold_time)

                            for target_h in hwnds:
                                win32gui.PostMessage(target_h, win32con.WM_KEYUP, vk, lparam_up)
                        finally:
                            if attached:
                                ctypes.windll.user32.AttachThreadInput(current_thread_id, target_thread_id, False)
                        return
            except Exception as e:
                print(f'Win11 background key error: {e}')

        elif sys.platform == 'darwin' and self.target_window:
            try:
                import Quartz
                pid = self.target_window.get('pid')
                if pid:
                    char_map = {
                        'a': 0, 's': 1, 'd': 2, 'f': 3, 'h': 4, 'g': 5, 'z': 6, 'x': 7,
                        'c': 8, 'v': 9, 'b': 11, 'q': 12, 'w': 13, 'e': 14, 'r': 15,
                        'y': 16, 't': 17, '1': 18, '2': 19, '3': 20, '4': 21, '6': 22,
                        '5': 23, '=': 24, '9': 25, '7': 26, '-': 27, '8': 28, '0': 29,
                        ']': 30, 'o': 31, 'u': 32, '[': 33, 'i': 34, 'p': 35, 'l': 37,
                        'j': 38, "'": 39, 'k': 40, ';': 41, '\\': 42, ',': 43, '/': 44,
                        'n': 45, 'm': 46, '.': 47, ' ': 49, '\r': 36, '\n': 36, 'enter': 36
                    }
                    mac_vk = char_map.get(key_str.lower())
                    if mac_vk is not None:
                        event_down = Quartz.CGEventCreateKeyboardEvent(None, mac_vk, True)
                        Quartz.CGEventPostToPid(pid, event_down)
                        hold_time = min(0.02, interval / 2.0)
                        time.sleep(hold_time)
                        event_up = Quartz.CGEventCreateKeyboardEvent(None, mac_vk, False)
                        Quartz.CGEventPostToPid(pid, event_up)
                        return
            except Exception as e:
                print(f'Mac background key error: {e}')

        try:
            keyboard.press(key_str)
            keyboard.release(key_str)
        except Exception as e:
            print(f'Error pressing key {key_str}: {e}')
