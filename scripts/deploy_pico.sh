WIPE=0
FIRST_ARG=${1:-}
if [ "${FIRST_ARG}" = "--wipe" ]; then
    WIPE=1
    # shift positional args so caller can pass serial as second arg
    shift
fi

SERIAL=${1:-serial://auto}
#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/deploy_pico.sh [serial_port]
SERIAL=${1:-serial://auto}

if [ ! -d micropython ]; then
  echo "micropython/ folder not found. Run from repo root."
  exit 1
fi

echo "Deploying micropython/ to $SERIAL using robust exec method from pico_tips.md"

# Function to upload a file using the robust exec fallback
upload_file() {
    local src_file="$1"
    local dest_file="$2"
    echo "Uploading $src_file as $dest_file"
    python - <<PY
from pathlib import Path
import subprocess
content = Path('$src_file').read_text()
exec_cmd = "with open('$dest_file','w') as f: f.write({!r}); print('installed $dest_file')".format(content)
subprocess.run(['python','-m','mpremote','connect','$SERIAL','exec', exec_cmd], check=True)
PY
}

if [ "$WIPE" -eq 1 ]; then
    echo "Wiping device filesystem (optional) on $SERIAL"
    # Run a conservative wipe: attempt to remove everything under /, but ignore errors.
    # This runs a small Python snippet on the device to delete known top-level entries
    # and recursively remove directories. We ignore failures so this is safe to run
    # on a device with limited FS permissions.
    python -m mpremote connect $SERIAL exec "import os,sys
def rmpath(p):
    try:
        if p in ('/flash', '/'): return
        if not os.path.exists(p): return
        if os.stat(p)[0] & 0o170000 == 0o040000:
            for name in os.listdir(p):
                rmpath(p+'/'+name)
            try:
                os.rmdir(p)
            except Exception:
                pass
        else:
            try:
                os.remove(p)
            except Exception:
                pass
    except Exception as e:
        pass
for n in list(os.listdir('/')):
    if n in ('flash',):
        continue
    rmpath('/'+n)
"
fi

# Upload all Python files
echo "Uploading Python modules..."
for py_file in micropython/*.py; do
    if [ -f "$py_file" ]; then
        basename_file=$(basename "$py_file")
        upload_file "$py_file" "$basename_file"
    fi
done

# Upload JSON config files
echo "Uploading configuration files..."
for json_file in micropython/*.json; do
    if [ -f "$json_file" ] && [[ "$json_file" != *"secrets.local.json" ]]; then
        basename_file=$(basename "$json_file")
        upload_file "$json_file" "$basename_file"
    fi
done

# Create directories
echo "Creating directories..."
python -m mpremote connect $SERIAL exec "
import os
try:
    os.mkdir('assets')
    print('Created assets/ directory')
except OSError as e:
    if e.args[0] == 17:  # EEXIST
        print('assets/ directory already exists')
    else:
        print('Error creating assets/:', e)
try:
    os.mkdir('images')
    print('Created images/ directory')
except OSError as e:
    if e.args[0] == 17:  # EEXIST
        print('images/ directory already exists')
    else:
        print('Error creating images/:', e)
"

# Upload assets (binary files need base64 encoding)
echo "Uploading assets..."
if [ -d "micropython/assets" ]; then
    for asset_file in micropython/assets/*; do
        if [ -f "$asset_file" ]; then
            asset_name=$(basename "$asset_file")
            echo "Uploading binary asset $asset_file as /assets/$asset_name via base64"
            python - <<PY
import base64
import subprocess
from pathlib import Path

asset_path = Path('$asset_file')
if asset_path.exists():
    # Read binary file and base64 encode
    binary_data = asset_path.read_bytes()
    b64_data = base64.b64encode(binary_data).decode('ascii')
    
    # Split into chunks to avoid command line length limits
    chunk_size = 3000
    chunks = [b64_data[i:i+chunk_size] for i in range(0, len(b64_data), chunk_size)]
    
    # Clear any existing file and write chunks
    subprocess.run(['python', '-m', 'mpremote', 'connect', '$SERIAL', 'exec', 
                   "open('/assets/$asset_name.b64', 'w').close()"], check=True)
    
    for i, chunk in enumerate(chunks):
        cmd = f"f = open('/assets/$asset_name.b64', 'a'); f.write({chunk!r}); f.close()"
        subprocess.run(['python', '-m', 'mpremote', 'connect', '$SERIAL', 'exec', cmd], check=True)
    
    # Decode base64 to binary on device
    decode_cmd = f"""
import ubinascii
b64_content = open('/assets/$asset_name.b64', 'r').read()
with open('/assets/$asset_name', 'wb') as f:
    f.write(ubinascii.a2b_base64(b64_content))
print('Binary asset $asset_name installed')
"""
    subprocess.run(['python', '-m', 'mpremote', 'connect', '$SERIAL', 'exec', decode_cmd], check=True)
else:
    print('Asset file not found: $asset_file')
PY
        fi
    done
else
    echo "No assets directory found"
fi

# Upload secrets if present
if [ -f micropython/secrets.local.json ]; then
    echo "Uploading local secrets as secrets.json"
    upload_file "micropython/secrets.local.json" "secrets.json"
else
    echo "No micropython/secrets.local.json found; ensure secrets are present on device before running."
fi

echo "Deployment complete. Files on device:"
python -m mpremote connect $SERIAL fs ls :/
echo ""
echo "To test: python -m mpremote connect $SERIAL exec 'import main'"
echo "To run app: python -m mpremote connect $SERIAL exec 'import main; main.main()'"
