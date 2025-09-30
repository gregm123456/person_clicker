Person Clicker — Micropython Deployment

This folder contains the MicroPython application that runs on the Raspberry Pi Pico 2WH + Waveshare 1.3" ST7789 display.

Overview
- Copy `secrets.local.json` (created from `secrets.json.template`) into this folder locally. Ensure `secrets.local.json` is in the repo root `.gitignore` (it is included by default in this project).
- Edit `config.json` and `demographics.json` as needed.
- Deploy the full folder to the Pico using the helper script `scripts/deploy_pico.sh` or via `mpremote` directly. The `secrets.local.json` file will be pushed to the Pico as `/secrets.json` during deployment.

Virtualenv & prerequisites
- We recommend using a Python virtual environment to install `mpremote` and keep your system clean. From the project root you can create and activate a venv with:

```bash
./scripts/setup_venv.sh
source .venv/bin/activate
```

Deploy example (macOS / bash) using the helper script:

```bash
# from repo root (serial device defaults to serial://auto; or specify /dev/tty.* path)
./scripts/deploy_pico.sh
# to run immediately after deploy:
python -m mpremote connect serial://auto run :/main.py
```

Manual mpremote commands (alternative):

```bash
python -m mpremote connect serial://auto fs put micropython/:/
python -m mpremote connect serial://auto fs put micropython/secrets.local.json :/secrets.json
python -m mpremote connect serial://auto run :/main.py
```

Files in this folder
- `main.py` - entrypoint and bootstrap
- `app.py` - main application state machine
- `wifi.py` - WiFi connection logic
- `buttons.py` - button/joystick handling
- `display.py` - ST7789 wrapper & draw utilities
- `api_client.py` - Automatic1111 sdapi client
- `storage.py` - atomic file writes and reads
- `config.json`, `demographics.json` - editable configs
- `secrets.json.template` - template for secrets; copy to `secrets.local.json` locally and fill credentials

See the project root `build_plan.md` for full design and acceptance criteria.

Notes on simplified passthrough usage
- The device now expects the Automatic1111 passthrough to return a raw RGB565 framebuffer for the Pico display.
- The expected format is exactly 240x240 pixels, 2 bytes per pixel (RGB565), i.e. 240 * 240 * 2 = 115200 bytes.
- When the passthrough returns `application/octet-stream`, the client will save the bytes to `images/last.raw` and the display will write them directly to the ST7789 with no PNG decoding or conversion.

