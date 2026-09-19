import sys

def get_window_list():
    windows = []
    if sys.platform == 'win32':
        try:
            import win32gui
            def enum_windows_callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        windows.append({'title': title, 'hwnd': hwnd, 'pid': None})
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception as e:
            print('Windows list error:', e)
    elif sys.platform == 'darwin':
        try:
            from Quartz import CGWindowListCopyWindowInfo, kCGNullWindowID, kCGWindowListOptionOnScreenOnly
            window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
            for w in window_list:
                title = w.get('kCGWindowName', '')
                owner = w.get('kCGWindowOwnerName', '')
                pid = w.get('kCGWindowOwnerPID', 0)
                display_title = f'{owner} - {title}' if title else (owner if owner else '')
                if display_title and owner not in ['Window Server', 'Dock', 'SystemUIServer']:
                    windows.append({'title': display_title, 'pid': pid, 'owner': owner, 'name': title})
        except Exception as e:
            print('Mac list error:', e)
    return windows

def bring_window_to_front(window_info):
    if not window_info:
        return
    if sys.platform == 'win32':
        try:
            import win32gui
            hwnd = window_info.get('hwnd')
            if hwnd:
                win32gui.ShowWindow(hwnd, 9)
                win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            print('Win bring to front error:', e)
    elif sys.platform == 'darwin':
        try:
            from AppKit import NSRunningApplication, NSApplicationActivateIgnoringOtherApps
            pid = window_info.get('pid')
            if pid:
                app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
                if app:
                    app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        except Exception as e:
            print('Mac bring to front error:', e)
