#!/usr/bin/env python3
"""
Edge-Resident No-Code Voice Platform with Adaptive Command Learning
For Smart Home IoT - Raspberry Pi 4
Hardware: 2x IR Sensors, Relay Module, LED, USB Microphone, DC Fan

GPIO Pin Layout:
  IR Sensor 1  --> GPIO 17 (Entry detection)
  IR Sensor 2  --> GPIO 27 (Exit detection)
  Relay Module --> GPIO 22 (Fan control - Active LOW)
  LED          --> GPIO 18 (Light control)
"""

import RPi.GPIO as GPIO
import time
import json
import os
import threading
import queue
import vosk
import pyaudio

# ─────────────────────────────────────────────
#  GPIO PIN CONFIGURATION
# ─────────────────────────────────────────────
IR_SENSOR_1   = 17   # Entry side
IR_SENSOR_2   = 27   # Exit side
RELAY_PIN     = 22   # Fan (Active LOW relay)
LED_PIN       = 18   # Light (LED)

# ─────────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────────
VOSK_MODEL_PATH      = "model"          # Folder name of downloaded Vosk model
CUSTOM_COMMANDS_FILE = "custom_commands.json"
IR_TIME_WINDOW       = 2.0             # Max seconds between IR triggers (entry/exit)
SAMPLE_RATE          = 16000

# ─────────────────────────────────────────────
#  GLOBAL STATE
# ─────────────────────────────────────────────
occupancy_count = 0
fan_state       = False   # True = ON
light_state     = False   # True = ON
occupancy_lock  = threading.Lock()
state_lock      = threading.Lock()

# ─────────────────────────────────────────────
#  CUSTOM COMMANDS DATABASE
#  Format: { "phrase": {"fan": True/False/None, "light": True/False/None} }
# ─────────────────────────────────────────────
custom_commands = {}


# ══════════════════════════════════════════════
#  1. SETUP
# ══════════════════════════════════════════════

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    GPIO.setup(IR_SENSOR_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(IR_SENSOR_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.setup(RELAY_PIN, GPIO.OUT)
    GPIO.setup(LED_PIN,   GPIO.OUT)

    # Initialize both OFF
    GPIO.output(RELAY_PIN, GPIO.HIGH)   # Active LOW relay → HIGH = Fan OFF
    GPIO.output(LED_PIN,   GPIO.LOW)    # LED OFF

    print("[SETUP] GPIO initialized.")


def load_custom_commands():
    global custom_commands
    if os.path.exists(CUSTOM_COMMANDS_FILE):
        with open(CUSTOM_COMMANDS_FILE, "r") as f:
            custom_commands = json.load(f)
        print(f"[SETUP] Loaded {len(custom_commands)} custom command(s).")
    else:
        custom_commands = {}
        print("[SETUP] No custom commands file found. Starting fresh.")


def save_custom_commands():
    with open(CUSTOM_COMMANDS_FILE, "w") as f:
        json.dump(custom_commands, f, indent=2)


# ══════════════════════════════════════════════
#  2. DEVICE CONTROL
# ══════════════════════════════════════════════

def turn_fan_on():
    global fan_state
    with occupancy_lock:
        occ = occupancy_count
    if occ > 0:
        GPIO.output(RELAY_PIN, GPIO.LOW)   # Active LOW → Fan ON
        fan_state = True
        print("[DEVICE] ✅ Fan turned ON")
    else:
        print("[DEVICE] ❌ Fan ON denied — room is empty!")

def turn_fan_off():
    global fan_state
    GPIO.output(RELAY_PIN, GPIO.HIGH)      # Active LOW → Fan OFF
    fan_state = False
    print("[DEVICE] ✅ Fan turned OFF")

def turn_light_on():
    global light_state
    with occupancy_lock:
        occ = occupancy_count
    if occ > 0:
        GPIO.output(LED_PIN, GPIO.HIGH)
        light_state = True
        print("[DEVICE] ✅ Light turned ON")
    else:
        print("[DEVICE] ❌ Light ON denied — room is empty!")

def turn_light_off():
    global light_state
    GPIO.output(LED_PIN, GPIO.LOW)
    light_state = False
    print("[DEVICE] ✅ Light turned OFF")

def print_status():
    with occupancy_lock:
        occ = occupancy_count
    print(f"\n[STATUS] Occupancy: {occ} | Fan: {'ON' if fan_state else 'OFF'} | Light: {'ON' if light_state else 'OFF'}\n")


# ══════════════════════════════════════════════
#  3. OCCUPANCY DETECTION (runs in its own thread)
# ══════════════════════════════════════════════

def occupancy_thread():
    global occupancy_count
    print("[OCCUPANCY] Monitoring IR sensors...")

    s1_trigger_time = None
    s2_trigger_time = None

    while True:
        s1 = GPIO.input(IR_SENSOR_1) == GPIO.LOW   # LOW = triggered (pull-up config)
        s2 = GPIO.input(IR_SENSOR_2) == GPIO.LOW

        now = time.time()

        # S1 triggered first → possible ENTRY
        if s1 and s1_trigger_time is None:
            s1_trigger_time = now

        # S2 triggered first → possible EXIT
        if s2 and s2_trigger_time is None:
            s2_trigger_time = now

        # ENTRY: S1 triggered, then S2 within time window
        if s1_trigger_time and s2:
            if (now - s1_trigger_time) <= IR_TIME_WINDOW:
                with occupancy_lock:
                    occupancy_count += 1
                    occ = occupancy_count
                print(f"[OCCUPANCY] ➡️  ENTRY detected. Count = {occ}")
                s1_trigger_time = None
                s2_trigger_time = None
                time.sleep(1.5)   # Debounce
                continue

        # EXIT: S2 triggered, then S1 within time window
        if s2_trigger_time and s1:
            if (now - s2_trigger_time) <= IR_TIME_WINDOW:
                with occupancy_lock:
                    if occupancy_count > 0:
                        occupancy_count -= 1
                    occ = occupancy_count
                print(f"[OCCUPANCY] ⬅️  EXIT detected. Count = {occ}")
                # Auto turn off devices if room empty
                if occ == 0:
                    turn_fan_off()
                    turn_light_off()
                    print("[OCCUPANCY] Room empty — devices turned OFF automatically.")
                s1_trigger_time = None
                s2_trigger_time = None
                time.sleep(1.5)
                continue

        # Reset stale triggers
        if s1_trigger_time and (now - s1_trigger_time) > IR_TIME_WINDOW:
            s1_trigger_time = None
        if s2_trigger_time and (now - s2_trigger_time) > IR_TIME_WINDOW:
            s2_trigger_time = None

        time.sleep(0.05)


# ══════════════════════════════════════════════
#  4. RULE CONFLICT DETECTION
# ══════════════════════════════════════════════

def check_conflict(fan_action, light_action):
    """
    Check if the new command conflicts with any existing custom commands
    that are already scheduled to run opposite actions on same device.
    Returns (has_conflict, conflict_description)
    """
    for phrase, actions in custom_commands.items():
        # Fan conflict: one turns on, other turns off same device
        if fan_action is not None and actions.get("fan") is not None:
            if fan_action != actions["fan"]:
                return True, f"Fan conflict with custom command '{phrase}'"
        # Light conflict
        if light_action is not None and actions.get("light") is not None:
            if light_action != actions["light"]:
                return True, f"Light conflict with custom command '{phrase}'"
    return False, ""


# ══════════════════════════════════════════════
#  5. COMMAND PROCESSOR
# ══════════════════════════════════════════════

def process_command(text):
    """
    Match recognized text to predefined or custom commands and execute.
    """
    text = text.lower().strip()
    print(f"[VOICE] Recognized: '{text}'")

    if not text:
        return

    # ── PREDEFINED COMMANDS ──────────────────
    if "turn on fan" in text:
        turn_fan_on()
        print_status()
        return

    if "turn off fan" in text:
        turn_fan_off()
        print_status()
        return

    if "turn on light" in text:
        turn_light_on()
        print_status()
        return

    if "turn off light" in text:
        turn_light_off()
        print_status()
        return

    if "turn on all" in text or "everything on" in text:
        turn_fan_on()
        turn_light_on()
        print_status()
        return

    if "turn off all" in text or "everything off" in text:
        turn_fan_off()
        turn_light_off()
        print_status()
        return

    if "status" in text:
        print_status()
        return

    # ── ADAPTIVE COMMAND LEARNING ────────────
    # Format: "create command study mode" → saves as trigger for current device states
    if text.startswith("create command"):
        parts = text.replace("create command", "").strip()
        if parts:
            register_custom_command(parts)
        else:
            print("[LEARN] ❌ Please say a phrase after 'create command'.")
        return

    # ── MATCH CUSTOM COMMANDS ────────────────
    for phrase, actions in custom_commands.items():
        if phrase in text:
            print(f"[LEARN] ✅ Custom command matched: '{phrase}'")
            # Conflict check before executing
            conflict, reason = check_conflict(actions.get("fan"), actions.get("light"))
            if conflict:
                print(f"[CONFLICT] ⚠️  Conflict detected: {reason}. Blocked.")
                return
            if actions.get("fan") is True:
                turn_fan_on()
            elif actions.get("fan") is False:
                turn_fan_off()
            if actions.get("light") is True:
                turn_light_on()
            elif actions.get("light") is False:
                turn_light_off()
            print_status()
            return

    print(f"[VOICE] ❓ Command not recognized: '{text}'")


def register_custom_command(phrase):
    """
    Register current device ON/OFF states as a custom command trigger.
    User says: 'create command study mode' → saves fan+light current target states.
    We ask user via terminal what the command should do.
    """
    print(f"\n[LEARN] Registering new command: '{phrase}'")
    print("  What should this command do?")
    print("  [1] Turn ON fan + light")
    print("  [2] Turn OFF fan + light")
    print("  [3] Turn ON fan only")
    print("  [4] Turn ON light only")
    print("  [5] Turn OFF fan only")
    print("  [6] Turn OFF light only")

    choice = input("  Enter choice (1-6): ").strip()

    mapping = {
        "1": {"fan": True,  "light": True},
        "2": {"fan": False, "light": False},
        "3": {"fan": True,  "light": None},
        "4": {"fan": None,  "light": True},
        "5": {"fan": False, "light": None},
        "6": {"fan": None,  "light": False},
    }

    if choice in mapping:
        actions = mapping[choice]
        # Conflict check before saving
        conflict, reason = check_conflict(actions.get("fan"), actions.get("light"))
        if conflict:
            print(f"[CONFLICT] ⚠️  Cannot register — conflicts with: {reason}")
            return

        custom_commands[phrase] = actions
        save_custom_commands()
        print(f"[LEARN] ✅ Custom command saved: '{phrase}' → {actions}")
    else:
        print("[LEARN] ❌ Invalid choice. Command not saved.")


# ══════════════════════════════════════════════
#  6. VOICE RECOGNITION (runs in its own thread)
# ══════════════════════════════════════════════

def voice_thread():
    print("[VOICE] Loading Vosk model... (this may take a few seconds)")

    if not os.path.exists(VOSK_MODEL_PATH):
        print(f"[VOICE] ❌ Model folder '{VOSK_MODEL_PATH}' not found!")
        print("  Download from: https://alphacephei.com/vosk/models")
        print("  Recommended: vosk-model-small-en-us-0.15")
        return

    model = vosk.Model(VOSK_MODEL_PATH)
    rec   = vosk.KaldiRecognizer(model, SAMPLE_RATE)

    p    = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=8000
    )
    stream.start_stream()
    print("[VOICE] 🎤 Listening for commands...\n")

    while True:
        data = stream.read(4000, exception_on_overflow=False)
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text   = result.get("text", "").strip()
            if text:
                process_command(text)


# ══════════════════════════════════════════════
#  7. MAIN
# ══════════════════════════════════════════════

def main():
    print("=" * 55)
    print("  Edge-Resident No-Code Voice Smart Home System")
    print("  Running fully OFFLINE on Raspberry Pi 4")
    print("=" * 55)

    setup_gpio()
    load_custom_commands()

    # Start occupancy detection in background thread
    t_occ = threading.Thread(target=occupancy_thread, daemon=True)
    t_occ.start()

    # Start voice recognition in background thread
    t_voice = threading.Thread(target=voice_thread, daemon=True)
    t_voice.start()

    print("\n[MAIN] System running. Press Ctrl+C to exit.\n")
    print("  Predefined commands:")
    print("    'turn on fan'    | 'turn off fan'")
    print("    'turn on light'  | 'turn off light'")
    print("    'turn on all'    | 'turn off all'")
    print("    'status'")
    print("    'create command <your phrase>'")
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[MAIN] Shutting down...")
    finally:
        GPIO.output(RELAY_PIN, GPIO.HIGH)   # Fan OFF
        GPIO.output(LED_PIN,   GPIO.LOW)    # Light OFF
        GPIO.cleanup()
        print("[MAIN] GPIO cleaned up. Bye!")


if __name__ == "__main__":
    main()
