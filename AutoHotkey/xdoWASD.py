import keyboard
import subprocess
import time
import threading

remap_enabled = True
target_window_id = None

# Track internal key state
keys = {
    "w": False, "a": False, "s": False, "d": False,
    "space": False, "m": False, "n": False, ",": False
}

# Fixed xdotool key names (case-sensitive!)
key_map = {
    "w": "Up",
    "a": "Left",
    "s": "Down",
    "d": "Right",
    "space": "z",
    "m": "x",
    "n": "z",
    ",": "c"
}

def get_active_window_id():
    try:
        output = subprocess.check_output(["xdotool", "getactivewindow"])
        return output.decode().strip()
    except Exception:
        return None

def send_key(key, direction):
    try:
        subprocess.run(["xdotool", f"key{direction}", key])
    except Exception as e:
        print(f"Error sending key {key} {direction}: {e}")

def check_keys_loop():
    global remap_enabled, target_window_id
    while True:
        if remap_enabled and target_window_id:
            active_win = get_active_window_id()
            if active_win == target_window_id:
                for key, held in keys.items():
                    if keyboard.is_pressed(key):
                        if not keys[key]:
                            keys[key] = True
                            send_key(key_map[key], "down")
                    else:
                        if keys[key]:
                            keys[key] = False
                            send_key(key_map[key], "up")
        time.sleep(0.01)

def toggle_remap():
    global remap_enabled
    remap_enabled = not remap_enabled
    subprocess.run(["notify-send", "WASD Remap", "Enabled" if remap_enabled else "Disabled"])

def bind_target_window():
    global target_window_id
    target_window_id = get_active_window_id()
    subprocess.run(["notify-send", "WASD Remap", f"Window bound: {target_window_id}"])

# Start the background key check loop
threading.Thread(target=check_keys_loop, daemon=True).start()

# Set hotkeys
keyboard.add_hotkey('f1', toggle_remap)
keyboard.add_hotkey('ctrl+space', bind_target_window)

# Block forever
keyboard.wait()
