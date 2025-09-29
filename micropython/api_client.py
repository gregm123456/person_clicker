# api_client.py - minimal Automatic1111 sdapi client for MicroPython
import ubinascii
import ujson as json

try:
    import usocket as socket
    import urequests as requests
except Exception:
    # In desktop Python, fallback to requests (not used on Pico)
    import requests


class A1111Client:
    def __init__(self, base_url, user=None, password=None, api_path='/sdapi/v1/txt2img', timeout=30, image_width=512, image_height=512):
        self.base_url = base_url.rstrip('/')
        self.api_path = api_path
        self.timeout = timeout
        # target image size for requests
        self.image_width = int(image_width) if image_width else 512
        self.image_height = int(image_height) if image_height else 512
        self.auth_header = None
        if user is not None and password is not None:
            creds = '{}:{}'.format(user, password)
            try:
                # ubinascii in micropython
                self.auth_header = 'Basic ' + ubinascii.b2a_base64(creds.encode()).decode().strip()
            except Exception:
                import base64
                self.auth_header = 'Basic ' + base64.b64encode(creds.encode()).decode()

    def build_payload(self, prompt, seed=None, steps=20, cfg_scale=7.0, sampler_name='Euler', width=None, height=None):
        w = int(width) if width else self.image_width
        h = int(height) if height else self.image_height
        payload = {
            'prompt': prompt,
            'sampler_name': sampler_name,
            'steps': steps,
            'cfg_scale': cfg_scale,
            'width': w,
            'height': h
        }
        if seed is not None:
            payload['seed'] = seed
        return payload

    def txt2img(self, prompt, seed=None, steps=None, cfg_scale=None, sampler_name=None, width=None, height=None):
        url = self.base_url + self.api_path
        payload = self.build_payload(
            prompt,
            seed=seed,
            steps=(steps if steps is not None else 20),
            cfg_scale=(cfg_scale if cfg_scale is not None else 7.0),
            sampler_name=(sampler_name if sampler_name is not None else 'Euler'),
            width=width,
            height=height,
        )
        headers = {'Content-Type': 'application/json'}
        if self.auth_header:
            headers['Authorization'] = self.auth_header
        try:
            # urequests on MicroPython supports timeout param
            r = requests.post(url, data=json.dumps(payload), headers=headers, timeout=self.timeout)
            if r.status_code != 200:
                print('API error', r.status_code)
                return None
            # Automatic1111 returns base64-encoded images in JSON by default under "images"
            data = r.json()
            images = data.get('images')
            if images and len(images) > 0:
                # images[0] is base64 PNG
                b64 = images[0]
                try:
                    img_bytes = ubinascii.a2b_base64(b64)
                    return img_bytes
                except Exception:
                    import base64
                    return base64.b64decode(b64)
            else:
                print('No images in response')
                return None
        except Exception as e:
            print('txt2img request failed:', e)
            return None
