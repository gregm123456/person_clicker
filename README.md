# Person Clicker

A simple, portable "person clicker" image generator designed to run on a Raspberry Pi Pico 2WH with a Waveshare 1.3" ST7789 display, and optionally integrate with an Automatic1111 Stable Diffusion passthrough service for image generation.

This repository contains two main runtime targets:
- A MicroPython deployment that runs on the Pico device (folder: `micropython/`).
- A host-side helper and development tooling used for testing, packaging, and deploying to the Pico.

## Highlights
- Lightweight UI and simple category-based prompt building for generating portrait-style images.
- Automatic1111 passthrough support: the device can request images from a host server and receive either PNG images or a raw RGB565 framebuffer for direct display.
- Atomic file writes and simple offline-first behavior to work smoothly on the Pico.

## Quick start (development)
1. Read the MicroPython deployment docs in `micropython/README.md` for device preparation and deployment instructions.
2. Create a Python venv for host tools (optional but recommended):

	./scripts/setup_venv.sh
	source .venv/bin/activate

3. Use `./scripts/deploy_pico.sh` to copy the `micropython/` folder to your Pico. See `micropython/README.md` for examples and mpremote commands.

## Contributing
Bug reports and pull requests welcome. For device-specific issues include the Pico serial output and the version of MicroPython used on the device.

For details about configuring the passthrough / Automatic1111 service and secrets, see `micropython/README.md`.