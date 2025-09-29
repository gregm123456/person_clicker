# storage.py - atomic file writes for MicroPython
import os

def atomic_write(path, data_bytes):
    tmp = path + '.tmp'
    try:
        with open(tmp, 'wb') as f:
            f.write(data_bytes)
        # remove existing target if present, then rename
        try:
            os.remove(path)
        except Exception:
            pass
        os.rename(tmp, path)
        return True
    except Exception as e:
        print('atomic_write failed:', e)
        try:
            os.remove(tmp)
        except Exception:
            pass
        return False


def read_binary(path):
    try:
        with open(path, 'rb') as f:
            return f.read()
    except OSError as e:
        # Suppress noisy ENOENT (file not found) messages; return None so callers
        # can handle missing optional binaries (like images/last.png).
        # MicroPython OSError often exposes errno as e.args[0].
        try:
            err_code = e.args[0]
        except Exception:
            err_code = None
        if err_code == 2:
            return None
        # For other OS errors, print for debugging and return None.
        print('read_binary failed:', e)
        return None
    except Exception as e:
        print('read_binary failed:', e)
        return None
