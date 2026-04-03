# ─────────────────────────────────────────────────────────
#  SETUP GUIDE — Run these commands on your Raspberry Pi
# ─────────────────────────────────────────────────────────

# STEP 1: Update system
sudo apt update && sudo apt upgrade -y

# STEP 2: Install Python dependencies
pip3 install vosk pyaudio RPi.GPIO

# If pyaudio fails, install portaudio first:
sudo apt install portaudio19-dev -y
pip3 install pyaudio

# STEP 3: Download Vosk offline model
# Go to your project folder and run:
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 model

# STEP 4: Run the system
python3 smart_home.py


# ─────────────────────────────────────────────────────────
#  WIRING GUIDE
# ─────────────────────────────────────────────────────────

# IR SENSOR 1 (Entry side - inside the door frame)
#   VCC  --> Pin 2  (5V)
#   GND  --> Pin 6  (GND)
#   OUT  --> Pin 11 (GPIO 17)

# IR SENSOR 2 (Exit side - just behind Sensor 1)
#   VCC  --> Pin 4  (5V)
#   GND  --> Pin 14 (GND)
#   OUT  --> Pin 13 (GPIO 27)

# RELAY MODULE (for Fan)
#   VCC  --> Pin 2  (5V)
#   GND  --> Pin 6  (GND)
#   IN   --> Pin 15 (GPIO 22)
#   COM  --> Fan Live wire
#   NO   --> Power supply Live wire  (Normally Open)

# LED (for Light)
#   Anode (+) --> 220 ohm resistor --> Pin 12 (GPIO 18)
#   Cathode(-) --> Pin 20 (GND)

# USB MICROPHONE
#   Plug into any USB port on Raspberry Pi
