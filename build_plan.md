## Person Clicker — Build Plan and Strategy

This document records the agreed design, file layout, configuration strategy, behaviors, and acceptance criteria for the `person_clicker` MicroPython app that will run on a Raspberry Pi Pico 2WH connected to a Waveshare 1.3" ST7789 display.

Do NOT start any build from this document. This is a planning artifact only and will be used to validate scope before implementation.

---

## Goals (summary)
- Build a MicroPython app that runs on Pico 2WH + Waveshare 1.3" ST7789 that displays AI-generated portrait images.
- Four small hardware buttons (A, B, X, Y) each select a demographic category value. The joystick press (CTRL/GPIO3) is the Remix button.
- Pressing a category button picks a new value (never the exact same as current) and requests a new image from an Automatic1111 stable-diffusion server via the sdapi (HTTP POST /sdapi/v1/txt2img) using HTTP Basic Auth credentials.
- Remix requests a new image with the same demographic parameters but a new random seed.
- All app configuration is stored in text files on-device (JSON): `config.json`, `secrets.json` (separate, user-filled), and `demographics.json`.
- On boot, display the last saved generated image if present; otherwise use the placeholder `unknown_portrait.png` copied from the `notyou/` sample.
- Images returned by the server (commonly 512×512 PNG) are saved on-device as `/images/last.png` and scaled for display to the 240×240 LCD.
- Rapid/fast inputs: app assigns monotonic request IDs and ignores any earlier/late responses — matching `notyou/` semantics.

---

## High-level architecture
- Runtime: MicroPython on Pico 2WH.
- Network: connect to WiFi using credentials in `secrets.json` (WiFi handling patterns taken from `Pico2Wtest/`).
- Display: use ST7789 driver patterns from `pico2W_lcd1.3/` submodule; provide wrapper to draw and scale PNGs.
- Input: `buttons.py` reads hardware A, B, X, Y and joystick-press; supports debounce and edge detection.
- API: `api_client.py` performs Basic Auth POST to Automatic1111 `/sdapi/v1/txt2img`, supporting seed and generation params from `config.json`.
- Storage: atomic save/load of last image (write temp then rename).
- App: `app.py` manages category selection (values loaded from `demographics.json`), prompt building, request lifecycle (request IDs), saving and displaying images, and error/status screens.

---

## Planned repository layout (new `micropython/` tree)
This tree will be created at the repository root and is intended to be the deployable folder synced to the Pico via `mpremote`.

micropython/
- main.py                 # autostart entrypoint that boots WiFi and runs the app
- app.py                  # state machine: handle button events, requests, save/display
- api_client.py           # Automatic1111 sdapi client (Basic Auth, prompt, seed)
- wifi.py                 # WiFi connection logic (exponential backoff)
- display.py              # ST7789 wrapper, draw_scaled_png(path)
- buttons.py              # debounced edge-detected reader for A/B/X/Y and joystick press
- storage.py              # atomic file write/read utilities
- config.json             # non-sensitive app settings and defaults
- secrets.json.template   # template for WiFi and Automatic1111 user/pass (user fills to secrets.json)
- secrets.local.json      # OPTIONAL local secrets file (gitignored) used for deploy-only workflow
- demographics.json       # Category A/B/X/Y mapping and value lists (long country list included)
- assets/
	- unknown_portrait.png  # placeholder copied from notyou/
- images/
	- last.png              # runtime-created last image (saved by app)
- README.md               # deploy instructions, editing config, mpremote steps

Files intended to be edited on-device: `config.json`, `demographics.json` (if desired), and `secrets.json` (secrets.json is not added to VCS; template only).

Note about local secrets for deploy-only workflow: in addition to the `secrets.json.template` kept in the repo, the project will support a developer-managed `secrets.local.json` file that is listed in `.gitignore` and is never committed. This local secrets file allows fully-configured deployments (no manual edits on the Pico) by keeping credentials off VCS while still allowing `mpremote fs put` to push the file to the device. The README will describe how to create `secrets.local.json` from the template and how to exclude it from git.

---

## Configuration files and formats
- `config.json` (JSON, non-sensitive)
	- api_base_url (e.g., "http://192.168.1.100:7860")
	- api_txt2img_path (default: "/sdapi/v1/txt2img")
	- image_request_size (suggest default 512)
	- generation params: steps, cfg_scale, sampler_name, etc.
	- pin mapping defaults for A/B/X/Y and joystick press (GP numbers from `pico2W_lcd1.3/` samples)
	- timeouts, retry limits, and request behavior settings

- `secrets.json` (JSON, not committed)
	- wifi: ssid, password
	- automatic1111: user, password

- `secrets.local.json` (JSON, optional, gitignored)
  - Same structure as `secrets.json` but intended to live only on developer machine. The README will document creating this file from `secrets.json.template` and ensuring it is added to `.gitignore`. Deployment commands will explicitly include this file when syncing to the Pico.

- `demographics.json` (JSON)
	- mapping for Category A/B/X/Y to real category names and value arrays
	- Example structure: { "categories": { "A": {"name": "sex", "values": ["male","female","non-binary"]}, ... } }

Security note: `secrets.json` is plain text on the Pico per project requirement. Do not share or commit it.

---

## Behavior details and edge cases
- Button selection
	- Buttons are presented in code as "Category A", "Category B", "Category X", "Category Y"; real category names/values come only from `demographics.json`.
	- On press: pick a new value different from the current. Retry random selection up to 5 times; if still same, pick the nearest different value deterministically.

- Remix (joystick press)
	- Sends a new request using the same demographic parameters but a different random seed. Seed param must be supported by the Automatic1111 API.

- Fast inputs
	- Each outgoing request increments `request_id`. Incoming responses include the `request_id`. App ignores responses with `request_id` < current latest id. This mirrors `notyou/` semantics.

- Image saving and display
	- Raw PNG returned by the API is written atomically to `/images/last.png` (use temp+rename).
	- Display code loads PNG and scales (down or up) to 240×240 for ST7789.
	- If display or memory errors occur, show a textual status screen describing the problem.

- Network/API errors
	- WiFi connection uses exponential backoff and shows status on the screen.
	- API timeouts and HTTP errors are shown as textual errors and retried according to `config.json`.

---

## Acceptance criteria (per feature)
- Boot behavior: when `images/last.png` exists and is a valid PNG, the device displays it on boot. If missing or invalid, the placeholder `assets/unknown_portrait.png` is shown.
- Buttons: pressing any Category button always changes that category's selected value and starts a new image request.
- Remix: joystick press sends a new request with same params but different seed.
- Fast inputs: if multiple rapid presses occur, only the latest response is used and older responses are discarded.
- Config-driven: no demographic category names are hard-coded in the source; they are loaded from `demographics.json` (code uses labels Category A/B/X/Y only).
- Storage: `images/last.png` is only replaced via an atomic write.

---

## Testing strategy and smoke checks
- Unit / static checks (local dev)
	- Verify JSON configs are valid JSON and that `demographics.json` includes the four Category slots.

- Integration / device smoke tests (manual)
	1. Create `secrets.json` from template and fill WiFi + Automatic1111 user/pass.
	2. Deploy the entire `micropython/` tree to the Pico via `mpremote` (commands included in README).
	3. Boot the Pico; verify WiFi connects (status on screen). If not, inspect textual error screen.
	4. On boot verify placeholder or saved image displays.
	5. Press Category buttons and confirm new requests are sent to Automatic1111 and the returned image eventually appears (or an error is shown).
	6. Press the joystick (Remix) and verify new image generated with same params but different seed.
	7. Rapidly press several buttons to validate request-id semantics (only latest result shows).

---

## Deployment workflow (mpremote, macOS)
- Prepare: copy `micropython/secrets.json.template` → `micropython/secrets.json` and fill credentials.
- Sync entire tree to Pico (recommended):

Optional secure deploy workflow (no on-device editing):
- Maintain `micropython/secrets.local.json` on your development machine (create from template). Add `micropython/secrets.local.json` to the repository `.gitignore` so it is never committed.
- When deploying, use the `mpremote fs put` workflow to push the repo files plus the local secrets file to the Pico in one operation. Example (macOS / bash):

```bash
# from repo root
# copy repo micropython tree, then overwrite secrets on device from local file
mpremote connect serial://auto fs put micropython/:/
mpremote connect serial://auto fs put micropython/secrets.local.json :/secrets.json
```

This ensures the device receives the fully-configured app but the sensitive file remains out of git history.

```bash
# from repo root (macOS / bash)
mpremote connect serial://auto fs put micropython/:/
```

- Run immediately (optional):

```bash
mpremote connect serial://auto run :/main.py
```

Notes: exact serial path may be platform-specific; the commands above mirror the `pico2W_lcd1.3/` submodule workflow.

## Documentation requirement
The project will include comprehensive documentation for Pico 2WH deployment and device management modeled after the `pico2W_lcd1.3` submodule's `README.md`. The docs will cover:
- Preparing the development machine (mpremote installation, Python environment if needed).
- Creating `secrets.local.json` from the template and adding it to `.gitignore`.
- Full `mpremote` sync and run commands (examples for macOS bash).
- Recovery procedures (how to reset the Pico, safe mode, reinstall firmware if needed).
- How to remove the included submodules safely after migration.

The README in `micropython/` will contain these instructions verbatim and reference any supporting scripts or helper commands included in the repo.

---

## Removal of submodules (post-build)
- After validating the pico-target micropython app and migrating any useful snippets, we will remove the `notyou/`, `pico2W_lcd1.3/`, and `Pico2Wtest/` submodules from the repository. The `micropython/` tree will be self-contained and the README will explain what was removed and why.

---

## Next steps once plan is approved
1. Confirm this build plan (contents, file layout, config choices).
2. After your approval I will create the `micropython/` tree and the files listed in this plan and push them to the repository (this change will be done only after you explicitly say “go ahead” — no build/deploy steps will start until then).

If you approve, please reply with “go ahead” and I will start creating the planned files. If you want changes to the plan first, list them and I will update this document.

