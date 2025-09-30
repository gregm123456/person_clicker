# buttons.py - Button and joystick reader for Waveshare Pico LCD 1.3

import time
try:
    from machine import Pin
    MICROPYTHON = True
except Exception:
    MICROPYTHON = False
    Pin = None


class ButtonReader:
    """Edge-detecting button reader for active-low buttons with pull-up."""
    def __init__(self, pin_obj, debounce_ms=50):
        self.pin = pin_obj
        self.debounce_ms = debounce_ms
        # Assume pull-up: not-pressed == 1
        try:
            self.last_state = self.pin.value()
        except Exception:
            self.last_state = 1
        self.last_time = time.ticks_ms() if MICROPYTHON else int(time.time() * 1000)
        self.pressed = False

    def update(self):
        now = time.ticks_ms() if MICROPYTHON else int(time.time() * 1000)
        try:
            curr = self.pin.value()
        except Exception:
            curr = self.last_state
        if curr != self.last_state:
            if (now - self.last_time) > self.debounce_ms:
                # Active-low buttons: 0 = pressed
                if curr == 0 and self.last_state == 1:
                    self.pressed = True
                self.last_state = curr
                self.last_time = now

    def consume_pressed(self):
        if self.pressed:
            self.pressed = False
            return True
        return False


class Buttons:
    """Wrapper that initializes buttons from a config dict and provides
    polling helpers compatible with the app's expectations.
    Expected config keys (matching `config.json`):
      - button_a, button_b, button_x, button_y, joystick_press
    """
    DEFAULT_PINS = {
        'button_a': 15,
        'button_b': 17,
        'button_x': 19,
        'button_y': 21,
        'joystick_press': 3,
    }

    def __init__(self, cfg=None):
        self.cfg = cfg or {}
        self.readers = {}

        if not MICROPYTHON:
            print('Buttons: running in host mode (no machine.Pin) — inputs disabled/mock)')
            return

        # Build mapping name->GP number using config keys if present
        mapping = {}
        for logical, default_gp in self.DEFAULT_PINS.items():
            gp = self.cfg.get(logical, default_gp)
            mapping[logical] = gp

        try:
            # Map logical names to app-facing labels: A,B,X,Y,CTRL
            logical_to_label = {
                'button_a': 'A',
                'button_b': 'B',
                'button_x': 'X',
                'button_y': 'Y',
                'joystick_press': 'CTRL',
            }
            for logical_name, gp in mapping.items():
                label = logical_to_label.get(logical_name)
                if gp is None or label is None:
                    continue
                pin_obj = Pin(gp, Pin.IN, Pin.PULL_UP)
                reader = ButtonReader(pin_obj, debounce_ms=self.cfg.get('debounce_ms', 50))
                self.readers[label] = reader
                print(f'Button {label} initialized on GP{gp}')
        except Exception as e:
            print('Button initialization failed:', e)

    def poll_events(self):
        """Return dict of label -> pressed (True/False) for any edge-presses.
        This mirrors the expected interface used by `app.py`.
        """
        events = {}
        for label, reader in self.readers.items():
            try:
                reader.update()
                if reader.consume_pressed():
                    events[label] = True
            except Exception:
                pass
        return events

    def update(self):
        # Backwards-compatible method used by older app code
        for reader in self.readers.values():
            reader.update()

    def is_pressed(self, name):
        r = self.readers.get(name)
        return r.consume_pressed() if r else False

