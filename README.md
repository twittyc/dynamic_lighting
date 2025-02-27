# 🏡 Dynamic Lighting Automation for Home Assistant

This script automates **smart lighting control** in Home Assistant using **presence sensors, lux sensors, and time-based brightness settings**.  

💡 **Lights automatically adjust brightness based on time of day**  
🚶 **Presence sensors turn lights on/off based on occupency**  
🌞 **Lux sensors prevent lights from turning on when there's enough natural light**  
🌙 **Smooth fade-out when no presence is detected**  

---

## 🚀 Features
- **Adaptive Brightness:** Lights adjust to different brightness levels based on **time of day**.
- **Motion-Activated:** Uses **presence sensors** to turn lights on/off.
- **Lux-Based Control:** Lights only turn on if the **natural light is too low**.
- **Smooth Dimming:** Lights **fade out gradually** when presence is lost.
- **Per-Room Control:** Enable or disable automation for specific rooms.

---

## 🛠️ Installation
### 📌 **Prerequisites**
- **Home Assistant** installed & running.
- **AppDaemon Add-on** installed in Home Assistant.
- **Presence Sensors** (e.g., Aqara FP2, mmWave, etc.).
- **Lux Sensors** (optional for light-level-based control).
- **Smart Lights** integrated with Home Assistant (e.g., Philips Hue, Zigbee, WiFi bulbs).

### 📂 **1. Clone or Copy the Script**
```bash
git clone https://github.com/twittyc/dynamic_lighting.git
```
Or manually copy dynamic_lighting.py into:
```bash
/config/appdaemon/apps/dynamic_lighting.py
```

### 🛠️ 2. Configure AppDaemon
Edit `apps.yaml`:
```yaml
dynamic_lighting:
  module: dynamic_lighting
  class: DynamicLighting
```

### 🔄 3. Restart AppDaemon
```bash
ha restart
```

## ⚙️ Configuration
Edit `configuration.yaml` to add input numbers for bightness settings. Or add these via UI Helpers.
```yaml
input_number:
  brightness_day:
    name: "Daytime Brightness"
    min: 0
    max: 100
    step: 5
  brightness_evening:
    name: "Evening Brightness"
    min: 0
    max: 100
    step: 5
  brightness_night:
    name: "Nighttime Brightness"
    min: 0
    max: 100
    step: 5
  lux_threshold:
    name: "Lux Threshold"
    min: 0
    max: 500
    step: 10
  dimming_duration_seconds:
    name: "Dimming Duration (Seconds)"
    min: 1
    max: 30
    step: 1
  fade_delay:
    name: "Fade Delay"
    min: 0
    max: 60
    step: 5
```
### 🏡 Rooms & Sensors
In `dynamic_lighting.py, edit the rooms dictionary to match your sensor and light entities:
```python
self.rooms = {
    "kitchen": {
        "sensor": "binary_sensor.kitchen_presence",
        "light": "light.kitchen",
        "lux": "sensor.kitchen_lux",
        "override": "input_boolean.kitchen_automation"
    },
    "living_room": {
        "sensor": "binary_sensor.living_room_presence",
        "light": "light.living_room",
        "lux": "sensor.living_room_lux",
        "override": "input_boolean.living_room_automation"
    }
}
```
## 🎛️ Dashboard Setup
To monitor & control lighting settings, add this to your Lovelace dashboard:
```yaml
views:
  - title: Home
    sections:
      - type: grid
        cards:
          - type: entities
            entities:
              - entity: input_boolean.den_automation
                name: Enable Den Automation
              - entity: input_boolean.kitchen_automation
                name: Enable Kitchen Automation
              - entity: input_boolean.dining_automation
                name: Enable Dining Automation
              - entity: input_boolean.entry_automation
                name: Enable Entry Automation
              - entity: input_boolean.main_bath_automation
                name: Enable Main Bath Automation
              - entity: input_boolean.stairs
            title: Manual Overrides
            show_header_toggle: false
          - type: entities
            title: Lighting Settings
            show_header_toggle: false
            entities:
              - entity: input_number.lux_threshold
                name: Lux Threshold for Lights
              - entity: input_number.brightness_daytime
                name: Brightness (Day)
              - entity: input_number.brightness_evening
                name: Brightness (Evening)
              - entity: input_number.brightness_night
                name: Brightness (Night)
              - entity: input_number.dimming_duration_seconds
                name: Dimming Duration (Seconds)
              - entity: input_number.fade_delay
              - entity: input_datetime.evening_start
                name: Evening Mode Start
              - entity: input_datetime.night_start_time
                name: Night Mode Start
        column_span: 2
```
## ✅ How It Works
1️⃣ Presence detected → Lights turn on based on time of day or lux levels

2️⃣ No motion detected → Lights fade out smoothly after a delay

## 📝 Customization
🔹 Adjust brightness levels based on lux sensors instead of time

🔹 Create per-room automation toggles

🔹 Customize fade delay and dimming duration

## 🔍 Troubleshooting
`dynamic_lighting.py` will log to the AppDaemon addon logs to aid in troubleshooting.

❌ Lights don’t turn on?
- Check if lux levels are above the threshold (input_number.lux_threshold).
- Ensure presence sensor state is "on".

❌ Lights don’t turn off?
- Check fade delay settings (input_number.fade_delay).
- Verify presence sensor state is correctly updating.
