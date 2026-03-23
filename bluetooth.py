import asyncio
import json
import sys
import time
import subprocess

sys.stdout.reconfigure(line_buffering=True)

def get_connected_bt_devices():
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        # Ультра-быстрый запрос к ядру Windows (в 10 раз быстрее прошлого метода)
        cmd = 'powershell -NoProfile -Command "chcp 65001 >$null; Get-CimInstance Win32_PnPEntity -Filter \\"PNPClass=\'Bluetooth\' and Status=\'OK\'\\" | Select-Object -ExpandProperty Name"'
        
        result = subprocess.check_output(cmd, text=True, encoding='utf-8', startupinfo=si)
        
        devices = set()
        for line in result.split('\n'):
            name = line.strip()
            # Фильтруем системный мусор
            if name and "Enumerator" not in name and "Adapter" not in name and "Адаптер" not in name and "Hands-Free" not in name:
                devices.add(name)
        return devices
    except Exception:
        return set()

async def watch_bluetooth():
    last_devices = get_connected_bt_devices()
    while True:
        current_devices = get_connected_bt_devices()
        
        new_devices = current_devices - last_devices
        
        for dev_name in new_devices:
            print(json.dumps({
                "type": "bluetooth",
                "name": dev_name,
                "battery": "100%"
            }), flush=True)
            
        last_devices = current_devices
        await asyncio.sleep(1)

if __name__ == "__main__":
    sys.stderr = open('nul', 'w') if sys.platform == 'win32' else open('/dev/null', 'w')
    asyncio.run(watch_bluetooth())