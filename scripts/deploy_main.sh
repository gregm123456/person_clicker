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