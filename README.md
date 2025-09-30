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

## Demo video

Here's a short demo of the project. If your Markdown renderer supports iframes it will show the video inline; otherwise a clickable thumbnail will open the short on YouTube.

<iframe width="320" height="180" src="https://www.youtube.com/embed/saOANpPcf6s" title="Person Clicker demo (YouTube Short)" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>

[![Person Clicker demo](https://img.youtube.com/vi/saOANpPcf6s/hqdefault.jpg)](https://www.youtube.com/shorts/saOANpPcf6s)

Note: GitHub strips iframes from README previews, so click the thumbnail above if the embedded player doesn't appear.