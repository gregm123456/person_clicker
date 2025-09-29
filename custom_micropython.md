
## Custom MicroPython firmware plan (add uzlib)

Goal
------
Build and flash a MicroPython UF2 for the Raspberry Pi Pico W (Pico 2WH) that includes the `uzlib` module so the on-device PNG decoder in `micropython/display.py` can run without error. This document records the exact, reversible plan — do not run these steps until you've reviewed and approved them.

Why
----
- Current MicroPython on the device lacks `uzlib`, causing PNG decompression to fail.
- The cleanest fix (option B) is to build a MicroPython firmware that includes `uzlib` and any other useful modules we might need (for example, `uzlib`, `urequests` improvements, etc.).

High-level approach
-------------------
1. Clone the official MicroPython repository locally and initialise submodules.
2. Build `mpy-cross` (required for building the port).
3. Edit the rp2 port configuration so `MICROPY_PY_UZLIB` is enabled (and any other needed flags).
4. Build the RP2 port for `PICO_W` to produce a UF2 file.
5. Flash the resulting UF2 to the Pico W via BOOTSEL copy.
6. Verify `import uzlib` and run the app.

Prerequisites (host machine)
----------------------------
- Git
- Python 3 (for build scripts)
- Build tools dependent on host OS.

macOS (recommended brew packages)

```bash
brew install cmake pkg-config python3 git
# arm-none-eabi toolchain (needed on macOS - optional depending on how you build)
brew tap ArmMbed/homebrew-formulae
brew install arm-none-eabi-gcc
```

Ubuntu / Debian

```bash
sudo apt update
sudo apt install build-essential git libffi-dev pkg-config cmake python3 python3-venv gcc-arm-none-eabi
```

Notes:
- The rp2 build uses standard Makefiles in `ports/rp2`. `arm-none-eabi-gcc` is required for some host toolchains; if your distro provides it as a package, use that.

Detailed build steps
---------------------
These are the steps to produce a `firmware.uf2` with `uzlib` enabled.

1) Clone MicroPython and init submodules

```bash
git clone https://github.com/micropython/micropython.git
cd micropython
git submodule update --init
```

2) Build mpy-cross (cross-compiler used by some builds)

```bash
cd mpy-cross
make
cd ..
```

3) Prepare the rp2 port

```bash
cd ports/rp2
make submodules
```

4) Enable `uzlib` in the port configuration

- Edit `ports/rp2/mpconfigport.h` (or the relevant port config file) and ensure the following macro is defined (or set to 1):

```c
// in ports/rp2/mpconfigport.h
#define MICROPY_PY_UZLIB (1)
```

- If this macro already exists and is `0`, change it to `1`. If it doesn't exist, add it near other `MICROPY_PY_*` options. Optionally also enable other helpers you need.

5) Build the firmware for the Pico W

```bash
# From ports/rp2
make BOARD=PICO_W

# The build output should be in build-PICO_W/firmware.uf2
```

If the build succeeds you'll find `build-PICO_W/firmware.uf2` (or similarly named path) containing the UF2 that you can flash.

Flashing the Pico W
--------------------
1. Save the build artifact (copy `firmware.uf2` to a safe place).
2. Put the Pico W into bootloader mode by double-tapping the BOOTSEL button; it will mount as a USB mass storage device on your host.
3. Copy the UF2 file onto the mounted drive (just drag-and-drop or `cp` from the shell). The Pico will reboot automatically into the new firmware.

Verification
------------
After flashing and the Pico has rebooted, verify from the host:

```bash
python -m mpremote connect /dev/cu.usbmodemXXXX exec "import uzlib; print('uzlib OK')"

# Or test running the app:
python -m mpremote connect /dev/cu.usbmodemXXXX exec "import main; main.main()"
```

If `import uzlib` succeeds the on-device PNG decoder should be able to run.

Reverting to the default MicroPython firmware
--------------------------------------------
If you need to revert to the stock MicroPython image (or undo the custom firmware), do one of the following:

- Re-flash the official MicroPython RP2 UF2:
	1. Download the official `firmware.uf2` for Pico W from https://micropython.org/download/rp2-pico-w/
	2. Put the Pico into BOOTSEL mode (double-tap BOOTSEL).
	3. Copy the official `firmware.uf2` onto the mounted mass-storage device.

- If you saved the previous custom UF2 produced earlier, copy that back the same way.

Notes and caveats
------------------
- Building MicroPython requires a working toolchain. On macOS/Ubuntu the above packages are usually enough, but your environment may differ.
- Changing the firmware will affect any packages/modules previously installed on the device's filesystem (they will remain on flash but may need rebuilding if they depend on C modules). You should backup any important files (for example, `:/secrets.json`) before flashing.
- This build approach changes only the interpreter firmware; it does not modify your repo's Python sources.
- If you need a more automated approach, I can add a helper script that edits `mpconfigport.h`, builds the UF2 and optionally copies it to the Pico if you confirm.

Estimated effort
-----------------
- Host setup & build: 20–60 minutes (depends on whether build tools already present).
- Build time: a few minutes on a modern laptop.
- Flash and verify: 5 minutes.

Decision & next step
---------------------
If you approve, I'll proceed to implement the build/flash steps and provide an automated build script and exact command list for your macOS environment. I will NOT run any flashing or building operations until you explicitly instruct me to proceed.

If you want, I can also provide a small pre-built UF2 (from a known-good commit) that includes `uzlib` so you can flash immediately — but I recommend building locally to match the exact MicroPython commit and keep control of security/trust.

