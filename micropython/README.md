Person Clicker — MicroPython deployment and passthrough notes

This folder contains the MicroPython application that runs on the Raspberry Pi Pico 2WH + Waveshare 1.3" ST7789 display. The README below focuses on deployment, recent behavior changes, and examples for macOS (bash).

What's new / important changes
- RGB565 passthrough support: When a passthrough service (for example, an Automatic1111 instance running a simple proxy) returns binary data with content-type `application/octet-stream`, the Pico expects a raw RGB565 framebuffer sized to the display and will write it directly to the ST7789 without PNG decoding. The expected framebuffer format is 240x240, 2 bytes per pixel (RGB565) — total = 115200 bytes.
- Separate request size: The device display remains 240x240, but the app can request larger images from the server (e.g., 512x512) by setting `image_request_size` in `config.json`. The client will request the configured size from the passthrough; if the passthrough returns a raw RGB565 payload the client will validate the expected size against the display dimensions and fall back to PNG handling if it doesn't match.
- Secrets handling: Keep `secrets.local.json` out of source control. The deploy helper pushes `secrets.local.json` to the Pico as `/secrets.json` so you can store local credentials securely (it's already included in `.gitignore`).

Quick checklist before deploy
- Copy `secrets.json.template` -> `secrets.local.json` and fill `wifi` and `automatic1111` credentials.
- Edit `config.json` and `demographics.json` to tune prompts, display size, generation defaults, and pin mappings.

Virtualenv & prerequisites (recommended)
- Create and activate a venv from repo root (macOS / bash):

```bash
./scripts/setup_venv.sh
source .venv/bin/activate
```

Install mpremote into the venv if it's not already installed:

```bash
pip install mpremote
```

Deploy examples (macOS / bash)
1) Helper script (recommended):

```bash
# from repo root. The helper uses serial://auto by default; pass a device path to override
./scripts/deploy_pico.sh

# Example: wipe the device filesystem and deploy to a specific port
./scripts/deploy_pico.sh --wipe /dev/cu.usbmodem114301

# optionally run main immediately after deploy
python -m mpremote connect serial://auto run :/main.py
```

2) Manual mpremote steps (explicit):

```bash
# copy the entire micropython folder to the Pico root
python -m mpremote connect serial://auto fs put micropython/:/
# push secrets (local file) to /secrets.json on the Pico
python -m mpremote connect serial://auto fs put micropython/secrets.local.json :/secrets.json
# run the app
python -m mpremote connect serial://auto run :/main.py
```

Notes about passthrough behavior
- If the passthrough returns `application/octet-stream` and the byte length exactly matches the expected 240*240*2 bytes, the client treats it as an RGB565 framebuffer and writes it directly to the display (saved to `images/last.raw`).
- If the server returns a PNG (image/*, or content negotiation returns a PNG), the Pico will attempt to decode/scale it using the code paths in `display.py` (PIL is used in host testing; on-device decoding uses optimized MicroPython code).
- If you configure `image_request_size` to a value different from the display size, the client will request that size from the passthrough. For raw RGB565 responses the client validates the returned length matches the display frame buffer size; if not, it falls back to PNG handling or rejects the payload.

Files in this folder
- `main.py` - entrypoint and bootstrap
- `app.py` - main application state machine
- `wifi.py` - WiFi connection logic
- `buttons.py` - button/joystick handling
- `display.py` - ST7789 wrapper & draw utilities
- `api_client.py` - Automatic1111 sdapi client (supports octet-stream passthrough and PNG responses)
- `storage.py` - atomic file writes and reads
- `config.json`, `demographics.json` - editable configs
- `secrets.json.template` - template for secrets; copy to `secrets.local.json` locally and fill credentials

See the project root `build_plan.md` for design and acceptance criteria. If you run into issues, collect Pico serial logs and the output of `mpremote` when reporting bugs.

