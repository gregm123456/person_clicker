# micropython/main.py
# Entry point for the Person Clicker app on Pico 2WH.

import time
import ujson as json
from wifi import WifiManager
from display import Display
from app import PersonClickerApp

CONFIG_PATH = 'config.json'
SECRETS_PATH = 'secrets.json'
DEMOS_PATH = 'demographics.json'


def load_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print('Failed to load', path, e)
        return None


def main():
    print("Starting Person Clicker app...")
    cfg = load_json(CONFIG_PATH) or {}
    print("Config loaded:", bool(cfg))
    demos = load_json(DEMOS_PATH) or {}
    print("Demographics loaded:", bool(demos))
    # secrets might be absent on dev repo; app will show error if not present
    secrets = load_json(SECRETS_PATH)
    print("Secrets loaded:", bool(secrets))

    # Initialize display early so we can show boot-phase messages.
    print("Initializing display...")
    disp = Display(cfg.get('display', {}))
    disp.init()
    print("Display initialized")
    
    # Show a boot-phase message immediately after init (display-ready)
    try:
        disp.show_boot_phase("Display: ready", bg_color=(0, 48, 96), fg_color=(255, 255, 255), scale=2)
        print("Showing 'Display: ready' phase")
        time.sleep(1)  # Hold for 1 second to make it visible
    except Exception as e:
        print("Display ready (boot-phase message failed):", e)

    # Initialize WiFi and show its boot phase messages
    print("Initializing WiFi...")
    try:
        disp.show_boot_phase("WiFi: starting", bg_color=(200, 120, 0), fg_color=(0, 0, 0), scale=2)
        print("Showing 'WiFi: starting' phase")
        time.sleep(1)  # Hold for 1 second
    except Exception as e:
        print("WiFi starting phase failed:", e)

    wifi = WifiManager(secrets.get('wifi') if secrets else None, cfg)
    wifi.connect(blocking=False)

    try:
        disp.show_boot_phase("WiFi: connecting", bg_color=(200, 200, 0), fg_color=(0, 0, 0), scale=2)
        print("Showing 'WiFi: connecting' phase") 
        time.sleep(1)  # Hold for 1 second
    except Exception as e:
        print("WiFi connecting phase failed:", e)

    print("WiFi connection initiated")

    # Start the app and show app-start boot phase
    print("Starting PersonClickerApp...")
    try:
        disp.show_boot_phase("App: starting", bg_color=(0, 128, 64), fg_color=(255, 255, 255), scale=2)
        print("Showing 'App: starting' phase")
        time.sleep(1)  # Hold for 1 second
    except Exception as e:
        print("App starting phase failed:", e)

    app = PersonClickerApp(cfg, demos, secrets, disp, wifi)

    print("Starting main app loop...")
    try:
        app.run()
    except Exception as e:
        # Very simple error display fallback
        try:
            disp.show_text('Fatal error')
        except Exception:
            pass
        print('Fatal error in app:', e)


if __name__ == '__main__':
    main()
