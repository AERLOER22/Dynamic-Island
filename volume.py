import sys
import json
import time

# Жестко заставляем Python отправлять текст моментально
sys.stdout.reconfigure(line_buffering=True)

def watch_volume():
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    except ImportError:
        return

    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        last_vol = round(volume.GetMasterVolumeLevelScalar() * 100)
        last_mute = volume.GetMute()
        
        while True:
            time.sleep(0.05) # Опрос 20 раз в секунду для идеальной плавности
            current_vol = round(volume.GetMasterVolumeLevelScalar() * 100)
            current_mute = volume.GetMute()
            
            if current_vol != last_vol or current_mute != last_mute:
                last_vol = current_vol
                last_mute = current_mute
                print(json.dumps({"type": "volume", "volume": current_vol, "muted": current_mute}), flush=True)
    except Exception:
        pass

if __name__ == "__main__":
    sys.stderr = open('nul', 'w') if sys.platform == 'win32' else open('/dev/null', 'w')
    watch_volume()