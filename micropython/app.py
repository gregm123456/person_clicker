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
        # Persistent random seed used for generation. It remains the same
        # across category changes until the joystick/randomizer (CTRL)
        # explicitly requests a new seed.
        try:
            self.current_seed = random.getrandbits(31)
        except Exception:
            # Fallback in case random is not available for some reason
            self.current_seed = 1234
        # Control whether to show the previously cached image on boot.
        # Default: False (show placeholder/unknown_portrait.png until first button press)
        self.show_cached_on_boot = bool((self.cfg.get('behavior') or {}).get('show_cached_on_boot', False))
        # Config key: whether category button presses should change the persistent seed.
        # Default: False (category presses do NOT change seed). We no longer support
        # the legacy `remix_changes_seed_only` key — it has been removed to avoid
        # confusing semantics. If you need backward-compat configs, update them to
        # use `category_presses_change_seed` explicitly.
        behavior_cfg = (self.cfg.get('behavior') or {})
        self.category_presses_change_seed = bool(behavior_cfg.get('category_presses_change_seed', False))
        # Internal flag to indicate we've seen the first user interaction
        self._first_interaction_seen = False
        # Track if we're in an API error state to show "Retrying..." on next button press
        self._api_error_state = False
        # Attempt to load persisted state (last selections + seed)
        try:
            self._load_persistent_state()
        except Exception:
            # If loading fails for any reason, proceed with defaults
            pass

    def run(self):
        # Main event loop - initialization phases happen here before entering the loop
        print('PersonClickerApp: starting initialization phases...')
        hb_count = 0

        # Show button initialization phase
        try:
            self.display.show_boot_phase("Buttons: starting", bg_color=(128, 64, 0), fg_color=(255, 255, 255), scale=2)
            import time
            time.sleep(1)
        except Exception as e:
            print(f"Button init phase display failed: {e}")

        # Setup buttons (if any) using pins from config
        try:
            pins = self.cfg.get('pins') if self.cfg else None
            self.buttons = Buttons(pins)
            print('Buttons initialized successfully')
        except Exception as e:
            print(f'Button initialization failed: {e}')
            self.buttons = None

        # All initialization complete - now render the portrait for the first and only time
        print("All initialization complete, rendering portrait...")
        
        # Show the appropriate image based on configuration
        if self.show_cached_on_boot:
            # Show cached image if available
            data = read_binary('images/last.raw')
            if data:
                try:
                    self.display.draw_rgb565_raw('images/last.raw')
                    print("Displayed cached raw image")
                except Exception as e:
                    print(f"Cached raw failed: {e}, falling back to placeholder")
                    try:
                        self.display.show_placeholder()
                        print("Displayed placeholder (cached raw failed)")
                    except Exception as e2:
                        print(f"Placeholder fallback failed: {e2}")
            else:
                data = read_binary('images/last.png')
                if data:
                    try:
                        self.display.draw_scaled_png('images/last.png')
                        print("Displayed cached PNG image")
                    except Exception as e:
                        print(f"Cached PNG failed: {e}, falling back to placeholder")
                        try:
                            self.display.show_placeholder()
                            print("Displayed placeholder (cached PNG failed)")
                        except Exception as e2:
                            print(f"Placeholder fallback failed: {e2}")
                else:
                    try:
                        self.display.show_placeholder()
                        print("Displayed placeholder (no cached image)")
                    except Exception as e:
                        print(f"Placeholder display failed: {e}")
        else:
            # Show placeholder/unknown portrait
            try:
                self.display.show_placeholder()
                print("Displayed placeholder portrait")
            except Exception as e:
                print(f"Placeholder display failed: {e}")
                # Try a simple fallback - fill with a color
                try:
                    self.display.driver.fill(0x0000)  # Black screen
                    self.display.driver.text("Portrait failed", 10, 100, 0xFFFF)
                    print("Displayed error message")
                except Exception as e2:
                    print(f"Error message display failed: {e2}")

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
                                # Mark that we've received the first user interaction
                                if not self._first_interaction_seen:
                                    self._first_interaction_seen = True
                                    # If we were deferring showing cached image on boot,
                                    # allow the first button press to trigger a selection
                                    # and image request as normal. No extra action needed.
                                if name in ('A', 'B', 'X', 'Y'):
                                    # map to category keys
                                    cat = name
                                    val = self.pick_new_for_category(cat)
                                    print('Button', name, 'pressed ->', val)
                                    # Show "Retrying..." if we're in an error state
                                    if self._api_error_state:
                                        try:
                                            self.display.show_text('Retrying...', bg_color=(0, 100, 0))
                                            print('Showing retry message after API error')
                                            time.sleep(1)
                                        except Exception as e:
                                            print('Failed to show retry message:', e)
                                    # request image with new params
                                    if not self.category_presses_change_seed:
                                        # keep persistent seed: category changes do not remix
                                        self.request_image(seed=None)
                                    else:
                                        # treat category press as a remix: generate and use new seed
                                        seed = random.getrandbits(31)
                                        print('Category press -> new seed', seed)
                                        self.request_image(seed=seed)
                                elif name in ('CTRL', 'joystick', 'JOYSTICK'):
                                    # Show "Retrying..." if we're in an error state
                                    if self._api_error_state:
                                        try:
                                            self.display.show_text('Retrying...', bg_color=(0, 100, 0))
                                            print('Showing retry message after API error (remix)')
                                            time.sleep(1)
                                        except Exception as e:
                                            print('Failed to show retry message (remix):', e)
                                    # remix: same params, new random seed
                                    seed = random.getrandbits(31)
                                    print('Remix press -> seed', seed)
                                    self.request_image(seed=seed)
                        else:
                            # older Buttons API
                            self.buttons.update()
                            for key in ('A', 'B', 'X', 'Y'):
                                if self.buttons.is_pressed(key):
                                    if not self._first_interaction_seen:
                                        self._first_interaction_seen = True
                                    val = self.pick_new_for_category(key)
                                    print('Button', key, 'pressed ->', val)
                                    # Show "Retrying..." if we're in an error state
                                    if self._api_error_state:
                                        try:
                                            self.display.show_text('Retrying...', bg_color=(0, 100, 0))
                                            print('Showing retry message after API error')
                                            time.sleep(1)
                                        except Exception as e:
                                            print('Failed to show retry message:', e)
                                    if not self.category_presses_change_seed:
                                        self.request_image(seed=None)
                                    else:
                                        seed = random.getrandbits(31)
                                        print('Category press -> new seed', seed)
                                        self.request_image(seed=seed)
                            if self.buttons.is_pressed('CTRL'):
                                # Show "Retrying..." if we're in an error state
                                if self._api_error_state:
                                    try:
                                        self.display.show_text('Retrying...', bg_color=(0, 100, 0))
                                        print('Showing retry message after API error (remix)')
                                    except Exception as e:
                                        print('Failed to show retry message (remix):', e)
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
                # Persist selection change immediately so reboot preserves it
                try:
                    self._save_persistent_state()
                except Exception:
                    pass
                return cand
        # fallback: pick the first different value deterministically
        for v in values:
            if v != current:
                self.current_selection[cat_key] = v
                try:
                    self._save_persistent_state()
                except Exception:
                    pass
                return v
        return current

    def _load_persistent_state(self):
        """Load persisted state from 'state.json' if present.

        Expected shape: {"current_selection": {A:B,...}, "current_seed": 1234}
        """
        try:
            with open('state.json', 'r') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return
            sel = data.get('current_selection')
            if isinstance(sel, dict):
                # Only assign known keys to avoid unexpected data pollution
                for k in ('A', 'B', 'X', 'Y'):
                    if k in sel:
                        self.current_selection[k] = sel.get(k)
            seed = data.get('current_seed')
            if seed is not None:
                try:
                    # ensure int type
                    self.current_seed = int(seed)
                except Exception:
                    pass
        except Exception:
            # Missing file or bad JSON: ignore and continue
            pass

    def _save_persistent_state(self):
        """Atomically write state.json containing current_selection and current_seed.

        Uses atomic_write for safe writes when available; falls back to simple write.
        """
        payload = {
            'current_selection': self.current_selection,
            'current_seed': getattr(self, 'current_seed', None)
        }
        try:
            b = json.dumps(payload).encode('utf-8')
            # Prefer atomic_write helper if available
            try:
                atomic_write('state.json', b)
                return True
            except Exception:
                # Fallback to simple write
                with open('state.json', 'wb') as f:
                    f.write(b)
                return True
        except Exception:
            return False

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
        # Determine which seed to use. If caller provided an explicit seed
        # (e.g. joystick/randomizer), adopt it and store as the current seed.
        # Otherwise reuse the persistent seed so category changes are
        # deterministic until a remix occurs.
        if seed is None:
            # ensure we have a persistent seed
            if not hasattr(self, 'current_seed') or self.current_seed is None:
                try:
                    self.current_seed = random.getrandbits(31)
                except Exception:
                    self.current_seed = 0
            seed_to_use = self.current_seed
        else:
            # new seed supplied (remix); store it for future requests
            try:
                self.current_seed = seed
                # Persist the new seed so subsequent boots reuse it
                try:
                    self._save_persistent_state()
                except Exception:
                    pass
            except Exception:
                pass
            seed_to_use = seed

        # call API synchronously for now
        result = self.client.txt2img(
            prompt,
            seed=seed_to_use,
            steps=self.cfg.get('generation', {}).get('steps'),
            cfg_scale=self.cfg.get('generation', {}).get('cfg_scale'),
            sampler_name=self.cfg.get('generation', {}).get('sampler_name'),
        )
        if not result:
            print('No image bytes received')
            self.display.show_text('API Error')
            # Set API error state so next button press shows "Retrying..."
            self._api_error_state = True
            return

        # If the client returned a file path (streamed raw data), display directly
        if isinstance(result, str):
            path = result
            if rid == self.request_id:
                try:
                    self.display.draw_rgb565_raw(path)
                    # Clear API error state on successful display
                    self._api_error_state = False
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
                        # Clear API error state on successful display
                        self._api_error_state = False
                    except Exception as e:
                        print('display raw failed', e)
                        self.display.show_text('Display Error')
            return

        # Fallback: save as PNG for backward compatibility
        if atomic_write('images/last.png', img_bytes):
            if rid == self.request_id:
                try:
                    self.display.draw_scaled_png('images/last.png')
                    # Clear API error state on successful display
                    self._api_error_state = False
                except Exception as e:
                    print('display png failed', e)
                    self.display.show_text('Display Error')
        else:
            print('No image bytes received')
            self.display.show_text('API Error')
            # Set API error state since we failed to get image data
            self._api_error_state = True
