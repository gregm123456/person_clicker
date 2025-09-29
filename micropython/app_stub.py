# app_stub.py - helper for testing app logic in host environment (not used on Pico)
import json
from app import PersonClickerApp
from display import Display

cfg = json.load(open('micropython/config.json'))
demos = json.load(open('micropython/demographics.json'))
secrets = json.load(open('micropython/secrets.local.json'))

disp = Display(cfg.get('display', {}))
app = PersonClickerApp(cfg, demos, secrets, disp, None)

print('Current prompt (no selection yet):', app.build_prompt())
print('Pick A:', app.pick_new_for_category('A'))
print('Pick X:', app.pick_new_for_category('X'))
print('Prompt now:', app.build_prompt())
