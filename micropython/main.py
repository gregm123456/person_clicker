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

    print("Initializing display...")
    disp = Display(cfg.get('display', {}))
    disp.init()
    print("Display initialized")
    # Show placeholder (this will try the packaged /assets image, then fallback to red)
    disp.show_placeholder()

    print("Initializing WiFi...")
    wifi = WifiManager(secrets.get('wifi') if secrets else None, cfg)
    wifi.connect(blocking=False)
    print("WiFi connection initiated")

    print("Starting PersonClickerApp...")
    app = PersonClickerApp(cfg, demos, secrets, disp, wifi)
    try:
        app.run()
    except Exception as e:
        # Very simple error display fallback
        disp.show_text('Fatal error')
        print('Fatal error in app:', e)


if __name__ == '__main__':
    main()
