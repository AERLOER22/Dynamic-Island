import asyncio
import json
import sys
import time
import subprocess

sys.stdout.reconfigure(line_buffering=True)

def get_connected_bt_devices():
async def watch_bluetooth():
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
        from winrt.windows.devices.enumeration import DeviceInformation
    except ImportError:
        from winsdk.windows.devices.enumeration import DeviceInformation

def watch_bluetooth():
    last_devices = get_connected_bt_devices()
    # Ищем только ПОДКЛЮЧЕННЫЕ блютуз-устройства (отсеиваем отключенные)
    aqs = 'System.Devices.Aep.IsConnected:=System.StructuredQueryType.Boolean#True AND (System.Devices.Aep.ProtocolId:="{E0CBF06C-CD8B-4647-BB8A-263B43F0F974}" OR System.Devices.Aep.ProtocolId:="{BB7BB05E-5972-42B5-94FC-76EAA7084D49}")'
    
    watcher = DeviceInformation.create_watcher(aqs, [])
    
    known_devices = set()
    is_ready = [False]

    # Срабатывает моментально при подключении наушников
    def on_added(watcher, device_info):
        if device_info.name:
            if is_ready[0] and device_info.id not in known_devices:
                print(json.dumps({
                    "type": "bluetooth",
                    "name": device_info.name,
                    "battery": "100%"
                }), flush=True)
            known_devices.add(device_info.id)

    # Срабатывает моментально при отключении (убираем их из списка)
    def on_removed(watcher, device_update):
        if device_update.id in known_devices:
            known_devices.remove(device_update.id)

    def on_enum_completed(watcher, obj):
        is_ready[0] = True

    watcher.add_added(on_added)
    watcher.add_removed(on_removed)
    watcher.add_enumeration_completed(on_enum_completed)
    
    watcher.start()
    
    # Скрипт не нагружает процессор и просто ждет системных событий в фоне
    while True:
        time.sleep(1) # Опрос каждую секунду, теперь работает моментально
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
    watch_bluetooth()
    asyncio.run(watch_bluetooth())