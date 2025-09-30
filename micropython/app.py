# app.py - Person Clicker app state machine (skeleton)
import time
import json
import random

from api_client import A1111Client
from storage import atomic_write, read_binary
from buttons import Buttons


class PersonClickerApp:
    def __init__(self, cfg, demos, secrets, display, wifi):
        self.cfg = cfg or {}
        self.demos = demos or {}
        self.secrets = secrets or {}
        self.display = display
        self.wifi = wifi
        api_base = self.cfg.get('api_base_url', '')
        user = (self.secrets.get('automatic1111') or {}).get('user')
        password = (self.secrets.get('automatic1111') or {}).get('password')
        api_key = (self.secrets.get('automatic1111') or {}).get('api_key') or self.secrets.get('SERVICE_API_KEY') if self.secrets else None
        disp_cfg = self.cfg.get('display', {})
        img_w = disp_cfg.get('width', 240)
        img_h = disp_cfg.get('height', 240)
        # Allow requesting a different size from upstream A1111 (e.g. 512)
        req_size = self.cfg.get('image_request_size') or None
        if req_size:
            try:
                req_w = req_h = int(req_size)
            except Exception:
                req_w = img_w
                req_h = img_h
        else:
            req_w = img_w
            req_h = img_h

        self.client = A1111Client(
            api_base,
            user,
            password,
            api_path=self.cfg.get('api_txt2img_path', '/sdapi/v1/txt2img'),
            timeout=self.cfg.get('timeouts', {}).get('api_timeout_seconds', 30),
            image_width=req_w,
            image_height=req_h,
        )
        # Tell client the actual Pico display size so it can validate/raw-detect responses
        try:
            self.client.target_width = img_w
            self.client.target_height = img_h
        except Exception:
            pass
        # attach API key to client for passthrough authorization if available
        try:
            if api_key:
                self.client.api_key = api_key
        except Exception:
            pass
        self.current_selection = {'A': None, 'B': None, 'X': None, 'Y': None}
        self.request_id = 0

    def run(self):
        # simple loop sample; real implementation should poll buttons and wifi events
        # Show last image if available
        # Prefer raw RGB565 image saved by passthrough: images/last.raw
        data = read_binary('images/last.raw')
        if data:
            try:
                # draw raw RGB565 directly
                self.display.draw_rgb565_raw('images/last.raw')
            except Exception:
                self.display.show_placeholder()
        else:
            # fall back to any PNG saved previously for compatibility
            data = read_binary('images/last.png')
            if data:
                try:
                    self.display.draw_scaled_png('images/last.png')
                except Exception:
                    self.display.show_placeholder()
            else:
                self.display.show_placeholder()
        # main event loop (skeleton)
        print('PersonClickerApp: ready, entering main loop')
        hb_count = 0

        # Setup buttons (if any) using pins from config
        try:
            pins = self.cfg.get('pins') if self.cfg else None
            self.buttons = Buttons(pins)
        except Exception:
            self.buttons = None

        while True:
            try:
                # Poll buttons and handle presses
                if self.buttons:
                    try:
                        # For simple compatibility, support both Buttons.poll_events() and Buttons.update()/is_pressed()
                        if hasattr(self.buttons, 'poll_events'):
                            events = self.buttons.poll_events() or {}
                            # events: dict of name -> pressed bool
                            for name, pressed in events.items():
                                if not pressed:
                                    continue
                                if name in ('A', 'B', 'X', 'Y'):
                                    # map to category keys
                                    cat = name
                                    val = self.pick_new_for_category(cat)
                                    print('Button', name, 'pressed ->', val)
                                    # request image with new params
                                    self.request_image(seed=None)
                                elif name in ('CTRL', 'joystick', 'JOYSTICK'):
                                    # remix: same params, new random seed
                                    seed = random.getrandbits(31)
                                    print('Remix press -> seed', seed)
                                    self.request_image(seed=seed)
                        else:
                            # older Buttons API
                            self.buttons.update()
                            for key in ('A', 'B', 'X', 'Y'):
                                if self.buttons.is_pressed(key):
                                    val = self.pick_new_for_category(key)
                                    print('Button', key, 'pressed ->', val)
                                    self.request_image(seed=None)
                            if self.buttons.is_pressed('CTRL'):
                                seed = random.getrandbits(31)
                                print('Remix press -> seed', seed)
                                self.request_image(seed=seed)
                    except Exception as e:
                        print('Button poll failed', e)

                # Heartbeat: every ~5 seconds print a short status so testers know the app is alive
                time.sleep(0.1)
                hb_count += 1
                if hb_count >= 50:
                    hb_count = 0
                    try:
                        # advance wifi state machine before reading status
                        try:
                            if self.wifi:
                                self.wifi.poll()
                        except Exception:
                            pass
                        status = self.wifi.status() if self.wifi else 'no-wifi'
                    except Exception:
                        status = 'status-error'
                    print('heartbeat: wifi=', status)
            except KeyboardInterrupt:
                # Allow a manual interrupt during testing
                print('PersonClickerApp: interrupted')
                raise

    def pick_new_for_category(self, cat_key):
        cat = (self.demos.get('categories') or {}).get(cat_key)
        if not cat:
            return None
        values = cat.get('values') or []
        if not values:
            return None
        current = self.current_selection.get(cat_key)
        max_retry = self.cfg.get('selection', {}).get('max_retry_pick_different', 5)
        for _ in range(max_retry):
            cand = random.choice(values)
            if cand != current:
                self.current_selection[cat_key] = cand
                return cand
        # fallback: pick the first different value deterministically
        for v in values:
            if v != current:
                self.current_selection[cat_key] = v
                return v
        return current

    def build_prompt(self):
        # Simple prompt builder: concatenate selected category values only
        parts = []
        cats = self.demos.get('categories') or {}
        for k in ['A', 'B', 'X', 'Y']:
            val = self.current_selection.get(k)
            # Only include the raw value (no category name)
            if val:
                parts.append(val)
        body = ', '.join(parts)

        # Optional prefix/suffix from configuration
        prefix = (self.cfg.get('prompt_prefix') or '').strip()
        suffix = (self.cfg.get('prompt_suffix') or '').strip()

        # Assemble prompt carefully to avoid extra spaces
        prompt = body
        if prefix and body:
            prompt = '{} {}'.format(prefix, body)
        elif prefix:
            prompt = prefix
        if suffix:
            if prompt:
                prompt = '{} {}'.format(prompt, suffix)
            else:
                prompt = suffix

        return prompt

    def request_image(self, seed=None):
        prompt = self.build_prompt()
        self.request_id += 1
        rid = self.request_id
        # call API synchronously for now
        result = self.client.txt2img(prompt, seed=seed, steps=self.cfg.get('generation', {}).get('steps'), cfg_scale=self.cfg.get('generation', {}).get('cfg_scale'), sampler_name=self.cfg.get('generation', {}).get('sampler_name'))
        if not result:
            print('No image bytes received')
            self.display.show_text('API Error')
            return

        # If the client returned a file path (streamed raw data), display directly
        if isinstance(result, str):
            path = result
            if rid == self.request_id:
                try:
                    self.display.draw_rgb565_raw(path)
                except Exception as e:
                    print('display raw failed', e)
                    self.display.show_text('Display Error')
            return

        # Otherwise result is raw bytes (PNG or raw rgb565 in memory)
        img_bytes = result
        expected_size = (self.display.width * self.display.height * 2) if (hasattr(self.display, 'width') and hasattr(self.display, 'height')) else None
        if expected_size and len(img_bytes) == expected_size:
            # Save raw file atomically
            if atomic_write('images/last.raw', img_bytes):
                if rid == self.request_id:
                    try:
                        self.display.draw_rgb565_raw('images/last.raw')
                    except Exception as e:
                        print('display raw failed', e)
                        self.display.show_text('Display Error')
            return

        # Fallback: save as PNG for backward compatibility
        if atomic_write('images/last.png', img_bytes):
            if rid == self.request_id:
                try:
                    self.display.draw_scaled_png('images/last.png')
                except Exception as e:
                    print('display png failed', e)
                    self.display.show_text('Display Error')
        else:
            print('No image bytes received')
            self.display.show_text('API Error')
