# 🏠 Smart Home Voice IoT — Edge-Resident No-Code Voice Platform

An offline, edge-resident smart home automation system built on **Raspberry Pi 4** that uses voice commands, dual IR occupancy detection, adaptive command learning, and rule conflict detection — **no cloud, no internet required.**

> 📄 Research Paper: *Design and Implementation of an Edge-Resident No-Code Voice Platform with Adaptive Command Learning for Smart Home IoT*

---

## ✨ Features

- 🎤 **Offline Voice Control** — Powered by Vosk speech recognition, runs locally
- 🚪 **Dual IR Occupancy Detection** — Bidirectional entry/exit tracking
- 🔒 **Occupancy-Based Safety** — Devices won't turn ON in an empty room
- 🧠 **Adaptive Command Learning** — Add your own custom voice commands without retraining
- ⚠️ **Rule Conflict Detection** — Prevents contradicting automation rules from running
- ⚡ **Low Latency** — ~1.5 second response time vs ~4.2s for cloud systems
- 🔐 **Privacy First** — No voice data sent to any server

---

## 🛠️ Hardware Required

| Component | Quantity |
|---|---|
| Raspberry Pi 4 | 1 |
| IR Sensor (FC-51) | 2 |
| Relay Module (5V) | 1 |
| LED | 1 |
| USB Microphone | 1 |
| DC Fan | 1 |

---

## 📌 GPIO Wiring

| Component | GPIO Pin |
|---|---|
| IR Sensor 1 (Entry) | GPIO 17 |
| IR Sensor 2 (Exit) | GPIO 27 |
| Relay Module (Fan) | GPIO 22 |
| LED (Light) | GPIO 18 |

---

## ⚙️ Installation

```bash
# Install dependencies
pip3 install vosk pyaudio RPi.GPIO

# If pyaudio fails
sudo apt install portaudio19-dev -y
pip3 install pyaudio

# Download Vosk offline model
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 model

# Run the system
python3 smart_home.py
```

---

## 🎙️ Voice Commands

| Command | Action |
|---|---|
| `turn on fan` | Turns fan ON (if room occupied) |
| `turn off fan` | Turns fan OFF |
| `turn on light` | Turns light ON (if room occupied) |
| `turn off light` | Turns light OFF |
| `turn on all` | Turns both ON |
| `turn off all` | Turns both OFF |
| `status` | Prints current device & occupancy status |
| `create command <phrase>` | Registers a new custom voice command |

---

## 📊 System Performance

| Metric | Result |
|---|---|
| Occupancy Detection Accuracy | 98% |
| Voice Recognition Accuracy | 92% |
| Avg. Command Response Latency | ~1.5 seconds |
| System Throughput | 17 commands/min |
| Custom Command Success Rate | 95% |
| Conflict Detection Rate | 100% |

---

## 📁 Project Structure

```
smart-home-voice-iot/
│
├── smart_home.py        # Main Python code (all modules)
├── SETUP.sh             # Wiring guide + installation steps
├── model/               # Vosk offline model (download separately)
└── custom_commands.json # Auto-generated when you add custom commands
```

---
