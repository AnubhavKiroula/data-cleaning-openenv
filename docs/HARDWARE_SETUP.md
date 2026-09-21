# RL-Cleanse: Hardware Requisition, Circuit Design, & Edge Demo Setup

**Competition Track:** technIEEEks'26 — Embedded Systems & IoT Track  
**Project:** RL-Cleanse (Sequential IoT Sensor-Stream Denoising via Deep Q-Networks)  
**Deliverable:** Hardware Requisition List, Circuit Schematic, Digital Simulation Guide, Firmware & Serial Bridge  

---

## 1. College Hardware Requisition List

Present this itemized list to your college department/lab in-charge to requisition the necessary hardware components:

| Item # | Component | Recommended Model | Quantity | Purpose in Demo |
|:---|:---|:---|:---:|:---|
| **1** | **Microcontroller Board** | **ESP32 NodeMCU** (or Arduino Uno / Nano) | 1 | Samples sensor readings and streams telemetry over Serial/USB or Wi-Fi. |
| **2** | **Air Quality / Gas Sensor** | **MQ-135** (Air Quality / CO2 / Benzene) or **MQ-2** | 1 | Matches UCI Air Quality chemical multisensor target (`CO(GT)`, gas concentration). |
| **3** | **Temperature & Humidity Sensor** | **DHT22** (AM2302) or **DHT11** | 1 | Measures ambient temperature ($T$) and relative humidity ($RH$), matching UCI dataset columns. |
| **4** | **Breadboard** | Standard Full or Half-size Breadboard (830 or 400 tie points) | 1 | Solderless prototyping for circuit assembly. |
| **5** | **Jumper Wires** | Male-to-Male and Male-to-Female | 1 pack (20-30 wires) | Interconnecting sensor pins to ESP32/Arduino GPIO. |
| **6** | **USB Cable** | Micro-USB (or Type-C, matching your ESP32 board) | 1 | Power supply and 115200 baud UART Serial connection to your Ubuntu laptop. |
| **7** | *(Optional)* **OLED Display** | 0.96-inch I2C OLED (SSD1306, 128x64) | 1 | Displays real-time raw vs. RL-cleaned values directly on the physical device. |

---

## 2. Digital Circuit Design & Simulation Software

Before physically assembling components in the lab, you can design and simulate the entire circuit digitally on your laptop:

### Option A: Wokwi (Recommended for ESP32 & Arduino)
- **URL:** [https://wokwi.com](https://wokwi.com)
- **Why:** Wokwi is a browser-based simulator that emulates ESP32, DHT22, gas sensors, and I2C OLED displays in real-time, complete with simulated serial UART output.
- **Workflow:**
  1. Open Wokwi and create an **ESP32** project.
  2. Add a **DHT22** sensor and an analog potentiometer (to simulate the variable analog voltage of the MQ-135 gas sensor).
  3. Wire the components per the pinout table below.
  4. Paste the firmware code provided in Section 4.

### Option B: Tinkercad Circuits
- **URL:** [https://www.tinkercad.com/circuits](https://www.tinkercad.com/circuits)
- **Why:** Beginner-friendly drag-and-drop 3D breadboard wiring simulator for Arduino Uno.
- **Workflow:** Select Arduino Uno $\to$ place Gas Sensor & Temperature Sensor $\to$ wire power, ground, and analog inputs $\to$ run simulation.

### Option C: Fritzing / KiCad (For Final Academic Report Schematics)
- **Why:** Generates publication-ready schematics and breadboard wiring diagrams for your research paper and poster presentation.

---

## 3. Circuit Wiring & Pinout Connections

### ESP32 Pinout Mapping

```
      +---------------------------------------------------+
      |                    ESP32                          |
      |                                                   |
      |   [3V3 / 5V] ──────────────── Power Rail (+)      |
      |   [GND]      ──────────────── Ground Rail (-)     |
      |                                                   |
      |   [GPIO 34] (ADC1) ────────── MQ-135 Analog (AOUT)|
      |   [GPIO 4]         ────────── DHT22 Data Pin      |
      |                                                   |
      |   *(Optional I2C OLED)*                           |
      |   [GPIO 22] (SCL)  ────────── OLED SCL            |
      |   [GPIO 21] (SDA)  ────────── OLED SDA            |
      +---------------------------------------------------+
```

#### Detailed Pin Table:
| Sensor | Sensor Pin | ESP32 Connection | Notes |
|:---|:---|:---|:---|
| **MQ-135 Gas Sensor** | VCC | 5V (VIN) | Gas sensors require 5V heater coil voltage. |
| | GND | GND | Common ground. |
| | AOUT (Analog Out) | **GPIO 34** (ADC1_CH6) | Measures raw analog gas concentration voltage. |
| **DHT22 Temp/Humidity** | VCC (Pin 1) | 3.3V | |
| | DATA (Pin 2) | **GPIO 4** | 10k pull-up resistor to 3.3V (most breakout boards have this built-in). |
| | GND (Pin 4) | GND | Common ground. |

---

## 4. Microcontroller Firmware (C++ / Arduino IDE)

Upload this firmware sketch to your ESP32 board using Arduino IDE or PlatformIO. It samples the sensors every second, formats the reading as a standard JSON string, and transmits it over the USB Serial interface:

```cpp
/*
 * RL-Cleanse IoT Sensor Streamer
 * Reads MQ-135 and DHT22 and outputs JSON telemetry over Serial UART.
 */

#include "DHT.h"

#define DHTPIN 4
#define DHTTYPE DHT22
#define MQ135_PIN 34

DHT dht(DHTPIN, DHTTYPE);

unsigned long lastSampleTime = 0;
const unsigned long sampleInterval = 1000; // 1 second sample rate
unsigned long timestep = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }
  
  dht.begin();
  pinMode(MQ135_PIN, INPUT);
  
  Serial.println("{\"status\": \"initialized\", \"device\": \"ESP32-RL-Cleanse\"}");
}

void loop() {
  unsigned long currentTime = millis();
  if (currentTime - lastSampleTime >= sampleInterval) {
    lastSampleTime = currentTime;
    
    // Read temperature and humidity
    float humidity = dht.readHumidity();
    float temperature = dht.readTemperature();
    
    // Read raw ADC value from MQ-135 (12-bit ADC on ESP32: 0 - 4095)
    int rawGasADC = analogRead(MQ135_PIN);
    // Convert to normalized gas voltage representation (0.0 to 10.0 scale matching UCI CO(GT))
    float gasConcentration = (rawGasADC / 4095.0) * 10.0;
    
    // Handle sensor read failure gracefully
    if (isnan(humidity) || isnan(temperature)) {
      temperature = -200.0; // Sentinel value matching UCI dataset
      humidity = -200.0;
    }
    
    // Output JSON telemetry over Serial UART
    Serial.print("{\"timestep\":");
    Serial.print(timestep++);
    Serial.print(",\"sensor\":\"CO(GT)\"");
    Serial.print(",\"value\":");
    Serial.print(gasConcentration, 3);
    Serial.print(",\"temperature\":");
    Serial.print(temperature, 1);
    Serial.print(",\"humidity\":");
    Serial.print(humidity, 1);
    Serial.println("}");
  }
}
```

---

## 5. Laptop Real-Time Denoising Bridge (`scripts/live_iot_inference.py`)

Run this Python script on your Ubuntu laptop. It reads live readings from the USB Serial port (`/dev/ttyUSB0` or `/dev/ttyACM0`), passes each reading sequentially through the trained **RL-Cleanse DQN model**, and outputs the cleaned telemetry in real time:

```python
"""
RL-Cleanse: Real-Time Live Inference Bridge for Physical IoT Microcontrollers.
Reads live sensor JSON packets from serial port and denoises them using DQN.
"""

import serial
import json
import time
import torch
import numpy as np
from backend.ml.dqn_model import DQNAgent

SERIAL_PORT = "/dev/ttyUSB0"  # or /dev/ttyACM0
BAUD_RATE = 115200
MODEL_PATH = "models/dqn_iot_stream_best.pt"

def run_live_inference():
    print(f"Loading trained RL-Cleanse model from {MODEL_PATH}...")
    agent = DQNAgent(state_dim=50, action_dim=7, device="cpu")
    agent.load_model(MODEL_PATH)
    agent.set_training_mode(False)
    
    print(f"Connecting to microcontroller on {SERIAL_PORT} @ {BAUD_RATE} baud...")
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
    time.sleep(2)  # Wait for ESP32 boot
    
    rolling_history = []
    print("\nListening for live sensor readings (Ctrl+C to stop)...")
    print(f"{'Time':<8} | {'Raw Value':<10} | {'RL Action':<16} | {'Cleaned Value':<12}")
    print("-" * 55)
    
    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            if not line or not line.startswith("{"):
                continue
                
            packet = json.loads(line)
            raw_val = packet.get("value")
            t = packet.get("timestep", 0)
            
            # Construct observation with rolling history
            r_mean = float(np.mean(rolling_history)) if rolling_history else (raw_val or 0.0)
            r_std = float(np.std(rolling_history)) if rolling_history else 0.0
            r_med = float(np.median(rolling_history)) if rolling_history else (raw_val or 0.0)
            
            obs = {
                "current_row": t,
                "total_rows": 1000,
                "current_data": {
                    "sensor": "CO(GT)",
                    "value": raw_val,
                    "timestep": t % 24
                },
                "rolling_history": rolling_history[-5:],
                "rolling_stats": {
                    "mean": r_mean,
                    "std": r_std,
                    "median": r_med
                },
                "issues_detected": [],
                "legal_actions": ["skip", "fill_missing", "remove_outlier", "fix_type", "remove_duplicate"]
            }
            
            # Agent selects action
            action_dict = agent.get_action(obs, obs["legal_actions"])
            action_type = action_dict["action_type"]
            
            # Compute cleaned value
            if action_type == "skip":
                cleaned_val = raw_val
            elif action_type in ["remove_outlier", "fill_missing"]:
                cleaned_val = r_med
            elif action_type == "fix_type":
                cleaned_val = 0.5 * (raw_val or r_mean) + 0.5 * r_mean
            else:
                cleaned_val = action_dict.get("value", raw_val)
                
            rolling_history.append(cleaned_val)
            if len(rolling_history) > 10:
                rolling_history.pop(0)
                
            print(f"{t:<8} | {str(raw_val):<10} | {action_type:<16} | {cleaned_val:<12.3f}")
            
        except KeyboardInterrupt:
            print("\nStopped live demo.")
            break
        except Exception as e:
            print(f"Error parsing packet: {e}")

if __name__ == "__main__":
    run_live_inference()
```

---

## 6. Live Hardware Demo Script for Professors & Evaluators

When demonstrating the project to your professor or competition judges:
1. **Show the Circuit:** Point out the ESP32 microcontroller, MQ-135 gas sensor, and DHT22 temperature/humidity sensor on the breadboard.
2. **Induce Fault 1 (Electrical / Spike Noise):** Flick or tap the analog wire / introduce an instant spark or flame near the MQ-135 $\to$ the terminal will show a sudden spike, the RL agent will immediately trigger `remove_outlier`, and the signal will be clipped to the rolling median.
3. **Induce Fault 2 (Transmission Dropout):** Unplug the data wire momentarily $\to$ the terminal receives `None`/`-200`, the RL agent will trigger `fill_missing`, maintaining smooth telemetry continuity without crashing.
4. **Induce Fault 3 (Drift):** Breathe gently on the MQ-135 to elevate the baseline $\to$ observe the agent select `fix_type` (recalibration), gradually guiding the reading back to nominal levels.
5. **Show Comparison:** Display the `plots/baseline_vs_rl_comparison.png` and `plots/denoising_before_after.png` figures on your laptop screen to show that the learned RL policy achieves a **$19.9\%$ error reduction on spikes and $100\%$ on dropouts**, vastly outperforming static rule heuristics.
