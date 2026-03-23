import time
import json
import sys
import ctypes
from ctypes import wintypes

sys.stdout.reconfigure(line_buffering=True)
user32 = ctypes.windll.user32

class rect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long)
    ]

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", rect),
        ("rcWork", rect),
        ("dwFlags", wintypes.DWORD)
    ]

def is_fullscreen():
    hwnd = user32.GetForegroundWindow()
    if not hwnd: return False
    
    r = rect()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    
    # Получаем информацию о мониторе, на котором открыто окно
    MONITOR_DEFAULTTONEAREST = 2
    hmonitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(hmonitor, ctypes.byref(mi))
    
    mw = mi.rcMonitor.right - mi.rcMonitor.left
    mh = mi.rcMonitor.bottom - mi.rcMonitor.top
    
    w = r.right - r.left
    h = r.bottom - r.top
    
    # Если размеры окна равны или больше размера монитора (и это не рабочий стол)
    if w >= mw and h >= mh:
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        if class_name.value in ("Progman", "WorkerW"): # Игнорируем рабочий стол
            return False
        return True
    return False

if __name__ == "__main__":
    last_state = False
    while True:
        current_state = is_fullscreen()
        if current_state != last_state:
            try:
                print(json.dumps({"type": "fullscreen", "isFullscreen": current_state}), flush=True)
                last_state = current_state
            except OSError:
                break # Выходим из скрипта, если Electron закрыл соединение
        time.sleep(1)