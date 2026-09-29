# RL-Cleanse: Hardware Requisition, Circuit Design, & Edge Demo Setup

**Competition Track:** technIEEEks'26 — Embedded Systems & IoT Track  
**Project:** RL-Cleanse (Sequential IoT Sensor-Stream Denoising via Deep Q-Networks)  
**Deliverable:** Hardware Requisition List, Circuit Schematic, Digital Simulation Guide, Firmware & Serial Bridge  

---

## 0. Status of every claim in this document

Nothing in this document has been run on physical hardware. The table below
states, for each component, what has actually been executed.

| Component | Status | What that means |
|---|---|---|
| Requisition list (§1) | **Planned** | Parts specified; not yet procured. |
| Circuit design and pinout (§3) | **Designed** | Schematic and pin mapping are complete and internally consistent; never physically wired. |
| Wokwi / Tinkercad simulation (§2) | **Planned** | The wiring is intended to be validated in simulation. No simulation run is recorded in this repository, so no simulation result is claimed. |
| ESP32 firmware sketch (§4) | **Written, not flashed** | The sketch compiles against the named libraries by inspection only. It has not been built in the Arduino IDE or flashed to a board. |
| Serial bridge `scripts/live_iot_inference.py` (§5) | **Implemented; replay-tested only** | Runs end to end via `--replay`, which drives it from the UCI test split. The `--port` serial path has never been connected to a board. |
| Inference latency (§5) | **Measured on host CPU only** | The bridge reports its own host-CPU latency. No ESP32 or on-device figure is claimed anywhere. |
| Live demo procedure (§6) | **Planned** | A script for a demonstration that has not been rehearsed on hardware. |

The trained policy, the streaming environment, the rule baseline, the benchmark
and the notebook **are** implemented and executed; see `docs/PROFESSOR_BRIEFING.md`
for what they measured. The gap is specifically the physical layer.


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

**Status: implemented; exercised in replay mode only.**

The bridge is a real file in this repository, not a listing in a document. It
reads newline-delimited JSON packets from the serial port, denoises each reading
as it arrives, and prints the decision:

```json
{"timestep": 41, "sensor": "CO(GT)", "value": 2.45}
```

Run it against a board, or without one:

```bash
# With hardware attached (never yet exercised — no board has been connected)
python scripts/live_iot_inference.py --port /dev/ttyUSB0 --baud 115200

# Without hardware: replays a corrupted window from the UCI test split
python scripts/live_iot_inference.py --replay --steps 48
```

Replay output, copied verbatim from `--replay --steps 14`:

```text
   t       raw            action   cleaned      ms     truth    |err|
---------------------------------------------------------------------
   0     1.900              skip     1.900    0.50     1.900    0.000
   1     2.400              skip     2.400    0.28     2.400    0.000
   2     2.000              skip     2.000    0.24     2.000    0.000
   3     1.266              skip     1.266    0.23     1.300    0.034
   4     1.266              skip     1.266    0.23     1.000    0.266
   5     1.098              skip     1.098    0.22     1.200    0.102
   6     1.363              skip     1.363    0.21     1.500    0.137
   7     1.129              skip     1.129    0.23     1.300    0.171
   8     1.295              skip     1.295    0.22     1.500    0.205
   9     1.500              skip     1.500    0.22     1.500    0.000
  10     2.100              skip     2.100    0.23     2.100    0.000
  11     2.600              skip     2.600    0.21     2.600    0.000
  12     3.000              skip     3.000    0.20     3.000    0.000
  13     2.000              skip     2.000    0.22     2.000    0.000

Host-CPU inference latency over 14 readings: mean 0.25 ms, p95 0.36 ms
Replay MAE vs. ground truth: 0.0653
```

Note that the policy chose `skip` at every step of this particular window: it
was a benign stretch of the test split with no large transient, and skipping is
the correct decision there. A window that exercises the corrective actions is
plotted in section 8 of the notebook.

### Design note: the bridge reuses the trained environment's semantics

`StreamDenoiser` holds only `history_len = 5` floats of state and mirrors
`DataCleaningEnvironment._apply_action` exactly. Re-deriving the action formulas
independently here is the standard way a deployed filter silently drifts away
from the one that was trained and evaluated, so the two are kept aligned
deliberately and the unit tests assert they agree.

### Latency

The bridge prints its own mean and p95 latency per run. On the development host
(x86 CPU, no GPU needed) a single decision is a forward pass through an
11,206-parameter MLP over a 19-dimensional input, and measures well under a
millisecond — the run above measured 0.25 ms mean and 0.36 ms p95 over 14
readings.

**This is a host-CPU measurement and nothing more.** An ESP32-class figure would
require flashing the board and timing it there, which has not been done. The
architecture is small enough that on-device inference is plausible — $O(1)$
memory, five retained floats, no lookahead, no dataset-wide normaliser — but
"plausible" is the claim, not "measured".

---

## 6. Live Hardware Demo Script for Professors & Evaluators

When demonstrating the project to your professor or competition judges:
1. **Show the Circuit:** Point out the ESP32 microcontroller, MQ-135 gas sensor, and DHT22 temperature/humidity sensor on the breadboard.
2. **Induce Fault 1 (Electrical / Spike Noise):** Flick or tap the analog wire / introduce an instant spark or flame near the MQ-135 $\to$ the terminal will show a sudden spike, the RL agent will immediately trigger `remove_outlier`, and the signal will be clipped to the rolling median.
3. **Induce Fault 2 (Transmission Dropout):** Unplug the data wire momentarily $\to$ the terminal receives `None`/`-200`, the RL agent will trigger `fill_missing`, maintaining smooth telemetry continuity without crashing.
4. **Induce Fault 3 (Drift):** Breathe gently on the MQ-135 to elevate the baseline $\to$ observe the agent select `fix_type` (recalibration), gradually guiding the reading back to nominal levels.
5. **Show Comparison:** Display `plots/baseline_vs_rl_comparison.png` and `plots/denoising_before_after.png`. Quote the measured numbers from `docs/PROFESSOR_BRIEFING.md` — the spike family is where the learned policy has a clear advantage over the rule filter, the drift family is where neither method does much, and the dropout and duplicate families have so little raw error that there is nothing to win. Do not claim a headline figure that the benchmark did not produce; the table in the briefing is regenerated by `python -m backend.ml.evaluate_benchmarks` and is the authority.

### A caution for the demo

Points 2 to 4 above describe the response the policy is *intended* to produce.
They have never been observed on hardware, and the policy was trained on the UCI
air-quality channel rather than on MQ-135 output, whose scale and noise
characteristics differ. The encoder is scale-relative, which is the reason to
expect some transfer, but transfer to this sensor is untested. Rehearse the demo
in replay mode first and describe the hardware portion as a prototype.
