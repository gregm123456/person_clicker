# api_client.py - minimal Automatic1111 sdapi client for MicroPython
import ubinascii
import ujson as json

try:
    import usocket as socket
    import urequests as requests
except Exception:
    # In desktop Python, fallback to requests (not used on Pico)
    import requests

try:
    # local helper to atomically move tmp file to final path
    import uos as os
except Exception:
    import os


class A1111Client:
    def __init__(self, base_url, user=None, password=None, api_path='/sdapi/v1/txt2img', timeout=30, image_width=240, image_height=240):
        self.base_url = base_url.rstrip('/')
        self.api_path = api_path
        self.timeout = timeout
        # target image size for requests - default to 240x240 for Pico LCD
        self.image_width = int(image_width) if image_width else 240
        self.image_height = int(image_height) if image_height else 240
        self.auth_header = None
        self.api_key = None
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
        headers = {'Content-Type': 'application/json', 'Accept': 'application/octet-stream'}
        if self.auth_header:
            headers['Authorization'] = self.auth_header
        # If an API key is configured on the passthrough, include it as X-API-Key
        if hasattr(self, 'api_key') and self.api_key:
            try:
                headers['X-API-Key'] = self.api_key
            except Exception:
                pass
        try:
            # Debug: print payload that will be sent
            try:
                print('A1111Client: sending payload:', json.dumps(payload))
            except Exception:
                print('A1111Client: sending payload (non-serializable)')

            # urequests on MicroPython supports timeout param
            r = requests.post(url, data=json.dumps(payload), headers=headers, timeout=self.timeout)
            if r.status_code != 200:
                print('API error', r.status_code)
                # Try to print response body for debugging
                try:
                    body = r.text if hasattr(r, 'text') else (r.content if hasattr(r, 'content') else None)
                    print('API response body preview:', (body[:200] if body else None))
                except Exception:
                    pass
                return None

            # If the passthrough returns a binary RGB565 stream (application/octet-stream),
            # return raw bytes directly. Otherwise fall back to JSON image data (base64 PNG).
            ctype = None
            try:
                ctype = r.headers.get('Content-Type')
            except Exception:
                pass

            # If headers explicitly indicate binary, stream to file.
            if ctype and 'application/octet-stream' in ctype:
                # Stream binary response to file in chunks to avoid high memory usage
                tmp_path = 'images/last.raw.tmp'
                final_path = 'images/last.raw'
                try:
                    # Attempt to read in chunks from raw stream if available
                    try:
                        raw_stream = r.raw
                        with open(tmp_path, 'wb') as outf:
                            while True:
                                chunk = raw_stream.read(4096)
                                if not chunk:
                                    break
                                outf.write(chunk)
                    except Exception:
                        # Fallback: some request libs provide .content as full bytes
                        data = r.content if hasattr(r, 'content') else None
                        if data is None:
                            # Try reading .raw.read() fully
                            try:
                                data = r.raw.read()
                            except Exception:
                                data = None
                        if data is not None:
                            with open(tmp_path, 'wb') as outf:
                                outf.write(data)

                    # Rename tmp to final atomically
                    try:
                        # remove existing final if present
                        try:
                            os.remove(final_path)
                        except Exception:
                            pass
                        os.rename(tmp_path, final_path)
                    except Exception as e:
                        print('Failed to rename streamed file:', e)
                        # best-effort: leave tmp file and return None
                        return None

                    # Return the path so caller can display file directly
                    return final_path
                except Exception as e:
                    print('Streaming binary response failed:', e)
                    # cleanup tmp
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                    return None

            # Automatic1111 returns base64-encoded images in JSON by default under "images"
            # If headers did not indicate binary, do a safe probe of the body to
            # decide whether to treat it as JSON or binary. Some urequests builds
            # don't expose headers reliably, so we peek at the first chunk.
            try:
                probe_ok = False
                probe = None
                try:
                    # Try to read a small chunk from the raw stream
                    if hasattr(r, 'raw'):
                        probe = r.raw.read(512)
                    elif hasattr(r, 'content'):
                        probe = r.content[:512]
                except Exception:
                    probe = None

                if probe:
                    # Check for JSON-like start (whitespace then '{' or '[')
                    s = probe.lstrip()[:1]
                    if s in (b'{', b'[') if isinstance(s, bytes) else s in ('{', '['):
                        probe_ok = 'json'
                    else:
                        # If starts with PNG signature or non-text bytes, treat as binary
                        if isinstance(probe, (bytes, bytearray)) and probe.startswith(b'\x89PNG'):
                            probe_ok = 'binary'
                        else:
                            # Heuristic: if many non-ASCII bytes in probe, assume binary
                            non_ascii = sum(1 for c in probe if isinstance(c, int) and (c < 32 or c > 127))
                            if non_ascii > 50:
                                probe_ok = 'binary'
                            else:
                                probe_ok = 'json'

                # If probe decided binary, stream the remaining content plus probe to file
                if probe_ok == 'binary':
                    try:
                        tmp_path = 'images/last.raw.tmp'
                        final_path = 'images/last.raw'
                        with open(tmp_path, 'wb') as outf:
                            if probe:
                                outf.write(probe)
                            # attempt to drain rest of stream
                            try:
                                if hasattr(r, 'raw'):
                                    while True:
                                        chunk = r.raw.read(4096)
                                        if not chunk:
                                            break
                                        outf.write(chunk)
                                elif hasattr(r, 'content'):
                                    outf.write(r.content[len(probe) if probe else 0:])
                            except Exception:
                                pass
                        try:
                            try:
                                os.remove(final_path)
                            except Exception:
                                pass
                            os.rename(tmp_path, final_path)
                        except Exception as e:
                            print('Failed to rename streamed file (probe):', e)
                            return None
                        return final_path
                    except Exception as e:
                        print('Probe-based streaming failed:', e)
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                        return None
            except Exception:
                pass

            # If we get here, treat the response as JSON and attempt to decode it
            try:
                data = r.json()
            except Exception as e:
                print('Failed to decode JSON from response:', e)
                try:
                    body = r.text if hasattr(r, 'text') else (r.content if hasattr(r, 'content') else None)
                    print('Raw response preview:', (body[:400] if body else None))
                except Exception:
                    pass
                return None
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
