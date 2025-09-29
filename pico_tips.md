
# Pico tips: reliable mpremote workflows (macOS)

This short tip sheet collects the reliable, repeatable commands and small scripts I use on macOS when working with a Raspberry Pi Pico / Pico2 running MicroPython (for example, with a Waveshare LCD 1.3). It focuses on practical checks and robust file-install methods so you don't face intermittent upload/sync problems.

## Principles
- Use the explicit device node (e.g. `/dev/cu.usbmodem1301`) with `mpremote` on macOS. That avoids ambiguous auto-detection behavior.
- Prefer a self-contained `main.py` on the device for persistent demos (it will run automatically on power-up). For iterative development, run code with `mpremote run`.
- If `mpremote fs put` behaves inconsistently on a machine, use the `mpremote exec` fallback which writes files from inside the running MicroPython interpreter.

## Quick diagnostics checklist
Run these to verify device visibility and basic reachability.

1) Find the device node:

```bash
ls /dev/cu.* | grep usb
# e.g. /dev/cu.usbmodem11301
```

2) Confirm the Pico is responsive:

```bash
python -m mpremote connect /dev/cu.usbmodem11301 exec "print('Hello from Pico')"
```

3) Check who (if anyone) has the serial device open (optional):

```bash
sudo lsof /dev/cu.usbmodem11301 || true
```

4) Start an interactive REPL to inspect device-side state:

```bash
python -m mpremote connect /dev/cu.usbmodem11301 repl
# Ctrl-C to interrupt running code, Ctrl-D to soft-reboot
```

## Reliable upload methods

1) Standard: `fs put` (explicit remote path)

```bash
# upload a single file (explicit destination)
python -m mpremote connect /dev/cu.usbmodem11301 fs put micropython/main.py :/main.py

# verify
python -m mpremote connect /dev/cu.usbmodem11301 fs ls :/
python -m mpremote connect /dev/cu.usbmodem11301 fs cat :/main.py | head -n 20
```

Notes:
- Use the `:/` prefix to make the remote path explicit. Some mpremote variants accept slightly different forms; being explicit helps.
- If `fs put` reports success but `fs ls` does not show files, skip to the `exec` fallback below.

2) Fallback (most robust): write the file from inside MicroPython using `exec`

This method opens and writes the destination file on the Pico from the running interpreter. It's the most reliable across platforms and mpremote versions.

```bash
python - <<'PY'
from pathlib import Path
import subprocess
content = Path('micropython/main.py').read_text()
exec_cmd = "with open('main.py','w') as f: f.write({!r}); print('installed main.py')".format(content)
subprocess.run(['python','-m','mpremote','connect','/dev/cu.usbmodem11301','exec', exec_cmd], check=True)
PY

# verify
python -m mpremote connect /dev/cu.usbmodem11301 fs ls :/
python -m mpremote connect /dev/cu.usbmodem11301 exec "print(open('main.py').read()[:200])"
```

3) Directory sync

If you use `fs sync` to push entire directories, ensure the current working directory (the source) is correct before running the command and use verbose mode on first runs to confirm behavior:

```bash
# from the project root (example)
python -m mpremote connect /dev/cu.usbmodem11301 fs sync . /
```

If `fs sync` does not produce expected files, break the upload into single-file `fs put` calls or the `exec` fallback until you identify the problematic file.

## Small deploy helper script

Save this as `scripts/deploy_main.sh` in your project, make it executable (`chmod +x scripts/deploy_main.sh`), and invoke it with your device node.

```bash
#!/usr/bin/env bash
set -euo pipefail
DEVICE="$1"
SRC="micropython/main.py"

if [ ! -f "$SRC" ]; then
	echo "Source file $SRC not found" >&2
	exit 2
fi

python - <<PY
from pathlib import Path
import subprocess
content = Path('$SRC').read_text()
exec_cmd = "with open('main.py','w') as f: f.write({!r}); print('installed main.py')".format(content)
subprocess.run(['python','-m','mpremote','connect', '$DEVICE', 'exec', exec_cmd], check=True)
PY

echo "Done: main.py written to device $DEVICE"
python -m mpremote connect "$DEVICE" fs ls :/
```

Usage:

```bash
./scripts/deploy_main.sh /dev/cu.usbmodem11301
```

The script ensures the file is written using the exec fallback and lists the remote filesystem afterwards.

## Troubleshooting quick hits
- If `mpremote` sometimes fails: make sure you're calling the same `mpremote` each time. If you use a venv, activate it and use `python -m mpremote` or the venv's `mpremote` executable to avoid PATH/permission inconsistencies.
- If uploads repeatedly vanish: try a different USB cable (data-capable), reconnect the Pico, and re-run the `exec` fallback method.
- If you see permission errors on macOS when opening `/dev/cu.*`: check security settings and whether another app holds the port (`sudo lsof /dev/cu...`).

## When to use each approach
- `mpremote fs put` — simple, direct copies; use when it works and you can confirm files show in `fs ls`.
- `mpremote fs sync` — directory sync; use carefully and verify the source path.
- `mpremote exec` write — robust fallback; recommended when `fs` operations are flaky on your machine.

## Want me to add this to your deploy script?
I can (a) create `scripts/deploy_main.sh` in this repo and commit it, or (b) open and patch the deploy script in your other project to use the exec write fallback. Tell me which project/script and I will edit it.

