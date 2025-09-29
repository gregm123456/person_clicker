# buttons.py - Button and joystick reader for Waveshare Pico LCD 1.3

import time
try:
    from machine import Pin
    MICROPYTHON = True
except ImportError:
    MICROPYTHON = False
    Pin = None


class ButtonReader:
    def __init__(self, pin, pull_up=True, debounce_ms=50):
        self.pin = pin
        self.debounce_ms = debounce_ms
        self.last_state = 1 if pull_up else 0  # assume not pressed initially
        self.last_change_time = 0
        self.pressed = False
        self.released = False

    def update(self):
        """Call this regularly to update button state"""
        if not MICROPYTHON:
            return
        
        current_time = time.ticks_ms()
        current_state = self.pin.value()
        
        # Reset edge detection flags
        self.pressed = False
        self.released = False
        
        # Check if state changed and debounce period has passed
        if current_state != self.last_state:
            if time.ticks_diff(current_time, self.last_change_time) > self.debounce_ms:
                # Valid state change
                if current_state == 0 and self.last_state == 1:  # Falling edge (pressed for active-low)
                    self.pressed = True
                elif current_state == 1 and self.last_state == 0:  # Rising edge (released for active-low)
                    self.released = True
                
                self.last_state = current_state
                self.last_change_time = current_time

    def is_pressed(self):
        """Returns True if button was just pressed (edge detection)"""
        return self.pressed

    def is_released(self):
        """Returns True if button was just released (edge detection)"""
        return self.released

    def is_held(self):
        """Returns True if button is currently being held down"""
        return self.last_state == 0  # Active-low buttons


class Buttons:
    def __init__(self, cfg):
        self.cfg = cfg or {}
        self.readers = {}
        
        if not MICROPYTHON:
            print('Buttons: machine module not available, buttons disabled')
            return
        
        # Waveshare Pico LCD 1.3 default pins (active-low with pull-up)
        button_pins = {
            'A': self.cfg.get('button_a_pin', 15),  # GP15
            'B': self.cfg.get('button_b_pin', 17),  # GP17  
            'X': self.cfg.get('button_x_pin', 19),  # GP19 (if available)
            'Y': self.cfg.get('button_y_pin', 21),  # GP21 (if available)
            'CTRL': self.cfg.get('joystick_press_pin', 3),  # GP3 (joystick press)
        }
        
        try:
            for name, pin_num in button_pins.items():
                if pin_num is not None:
                    pin = Pin(pin_num, Pin.IN, Pin.PULL_UP)
                    self.readers[name] = ButtonReader(pin, pull_up=True, 
                                                    debounce_ms=self.cfg.get('debounce_ms', 50))
                    print(f'Button {name} initialized on GP{pin_num}')
        except Exception as e:
            print('Button initialization failed:', e)

    def update(self):
        """Update all button states - call this regularly"""
        for reader in self.readers.values():
            reader.update()

    def is_pressed(self, button_name):
        """Check if a button was just pressed"""
        reader = self.readers.get(button_name)
        return reader.is_pressed() if reader else False

    def is_released(self, button_name):
        """Check if a button was just released"""
        reader = self.readers.get(button_name)
        return reader.is_released() if reader else False

    def is_held(self, button_name):
        """Check if a button is currently being held"""
        reader = self.readers.get(button_name)
        return reader.is_held() if reader else False

    def get_pressed_buttons(self):
        """Return list of button names that were just pressed"""
        pressed = []
        for name, reader in self.readers.items():
            if reader.is_pressed():
                pressed.append(name)
        return pressed

    def any_pressed(self):
        """Return True if any button was just pressed"""
        return len(self.get_pressed_buttons()) > 0
import time

class ButtonReader:
    def __init__(self, pin_obj, name, debounce_ms=50):
        self.pin = pin_obj
        self.name = name
        self.debounce_ms = debounce_ms
        self.last_state = self.pin.value()
        self.last_time = time.ticks_ms()

    def read(self):
        current = self.pin.value()
        now = time.ticks_ms()
        if current != self.last_state:
            # debounce
            if time.ticks_diff(now, self.last_time) > self.debounce_ms:
                self.last_state = current
                self.last_time = now
                return current
        return None


# A simple wrapper for Pico: this file expects the app to import machine.Pin and
# pass pin objects for each button. We keep logic minimal here to avoid
# hardware-specific imports at repo-level testing.

class Buttons:
    def __init__(self, pin_map, PinClass):
        # pin_map: { 'button_a': GP#, ... }
        self.Pin = PinClass
        self.pins = {}
        for key, gp in pin_map.items():
            try:
                p = self.Pin(gp, self.Pin.IN, self.Pin.PULL_UP)
            except Exception:
                # provide a mock-like object in host environments
                p = self.MockPin()
            self.pins[key] = ButtonReader(p, key)

    class MockPin:
        def __init__(self):
            self._v = 1
        def value(self):
            return self._v

    def poll_events(self):
        # returns dict of button_name -> pressed (True/False)
        events = {}
        for name, reader in self.pins.items():
            val = reader.read()
            if val is not None:
                # active low buttons: 0 means pressed
                pressed = (val == 0)
                events[name] = pressed
        return events
