import asyncio
import json
import sys
import base64
import time

async def get_media_info():
    try:
        import winrt.windows.media.control as wmc
        import winrt.windows.storage.streams as streams
    except ImportError:
        import winsdk.windows.media.control as wmc
        import winsdk.windows.storage.streams as streams

    manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
    last_title = ""

    last_system_position = -1
    last_system_update_time = time.perf_counter()

    while True:
        try:
            sessions = manager.get_sessions()
            session = None
            
            # Черный список: игнорируем браузеры и локальные видеоплееры
            ignored_apps = [
                "chrome", "msedge", "firefox", "opera", "brave", "vivaldi", "yandexbrowser",
                "vlc", "zunevideo", "wmplayer", "mpc", "potplayer", "kmplayer"
            ]
            
            if sessions:
                for s in sessions:
                    app_id = (s.source_app_user_model_id or "").lower()
                    if not any(bad in app_id for bad in ignored_apps):
                        session = s
                        break

            if session is None:
                print(json.dumps({"type": "media", "playing": False, "title": ""}), flush=True)
                await asyncio.sleep(1)
                continue

            props = await session.try_get_media_properties_async()
            timeline = session.get_timeline_properties()
            playback = session.get_playback_info()

            title = props.title if props else ""
            artist = props.artist if props else ""
            
            position = timeline.position.total_seconds() if timeline else 0
            end_time = timeline.end_time.total_seconds() if timeline else 0

            # 4 означает состояние "Playing" (играет)
            playing = False
            if playback and playback.playback_status:
                playing = (playback.playback_status.value == 4) 

            # Умный таймер: Windows отдает время только при переключении/паузе,
            # поэтому мы сами "досчитываем" секунды, пока трек играет.
            if position != last_system_position:
                last_system_position = position
                last_system_update_time = time.perf_counter()
            
            current_position = position
            if playing:
                current_position = position + (time.perf_counter() - last_system_update_time)
            else:
                last_system_update_time = time.perf_counter()
            
            current_position = max(0, min(current_position, end_time))

            base64_img = "same"
            if title != last_title:
                base64_img = "none"
                if props and props.thumbnail:
                    try:
                        stream = await props.thumbnail.open_read_async()
                        reader = streams.DataReader(stream)
                        await reader.load_async(stream.size)
                        buf = bytearray(stream.size)
                        reader.read_bytes(buf)
                        base64_img = base64.b64encode(buf).decode('utf-8')
                    except Exception:
                        base64_img = "none"
            
            last_title = title

            out = {
                "type": "media",
                "playing": playing,
                "title": title,
                "artist": artist,
                "position": int(current_position),
                "endTime": int(end_time),
                "image": base64_img
            }
            print(json.dumps(out), flush=True)
        except Exception:
            pass
        
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(get_media_info())