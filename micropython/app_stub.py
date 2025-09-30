"""app_stub.py - helper for testing app logic in host environment (not used on Pico)

This stub avoids importing MicroPython-only modules by providing a minimal fake
API client. It's intended only to exercise PersonClickerApp.build_prompt() and
related selection logic on a host Python interpreter.
"""
import json
import types
import sys

# Provide a fake api_client.A1111Client module/class to satisfy imports in app.py
fake_api = types.SimpleNamespace()
class FakeClient:
	def __init__(self, *a, **k):
		pass
	def txt2img(self, *a, **k):
		return None
fake_api.A1111Client = FakeClient
sys.modules['api_client'] = fake_api

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
