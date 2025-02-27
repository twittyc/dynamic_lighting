import appdaemon.plugins.hass.hassapi as hass
from datetime import datetime

class DynamicLighting(hass.Hass):

    def initialize(self):
        """Initialize presence-based lighting automation with adaptive fading, manual override, and logging."""
        
        # Define rooms with associated presence sensors, lights, and lux sensors
        self.rooms = {
            "bridge_lower": {
                "sensor": "binary_sensor.den_presence_sensor_fp2_presence_sensor_4", # zone 4 is under bridge lighting
                "light": "light.bridge_lower",
                "lux": "sensor.den_presence_sensor_fp2_light_sensor_light_level",
                "last_lux": None,  # To store pre-light lux levels
                "override": "input_boolean.bridge_lower_automation"
            },
            "bridge_upper": {
                "sensor": "binary_sensor.bridge_presence_sensor_fp2_presence_sensor_1",
                "light": "light.bridge_upper",
                "lux": "sensor.bridge_presence_sensor_fp2_light_sensor_light_level",
                "last_lux": None,
                "override": "input_boolean.bridge_upper_automation"
            },
            "stairs": {
                "sensor": "binary_sensor.den_presence_sensor_fp2_presence_sensor_6",
                "light": "light.stairs",
                "lux": "sensor.bridge_presence_sensor_fp2_light_sensor_light_level",
                "last_lux": None,
                "override": "input_boolean.stairs"
            },
            "kitchen": {
                "sensor": "binary_sensor.den_presence_sensor_fp2_presence_sensor_2",
                "light": "light.kitchen",
                "lux": "sensor.den_presence_sensor_fp2_light_sensor_light_level",
                "last_lux": None,
                "override": "input_boolean.kitchen_automation"
            },
            "espresso_bar": {
                "sensor": "binary_sensor.den_presence_sensor_fp2_presence_sensor_3",
                "light": "light.espresso_bar",
                "lux": "sensor.den_presence_sensor_fp2_light_sensor_light_level",
                "last_lux": None,
                "override": "input_boolean.espresso_bar_automation"
            },
            "dining": {
                "sensor": "binary_sensor.living_room_presence_sensor_fp2_presence_sensor_2",
                "light": "light.dining",
                "lux": "sensor.living_room_presence_sensor_fp2_light_sensor_light_level",
                "last_lux": None,
                "override": "input_boolean.dining_automation"
            },
            "entry": {
                "sensor": "binary_sensor.living_room_presence_sensor_fp2_presence_sensor_3",
                "light": "light.entry",
                "lux": "sensor.living_room_presence_sensor_fp2_light_sensor_light_level",
                "last_lux": None,
                "override": "input_boolean.entry_automation"
            },
            "main_bath": {
                "sensor": "binary_sensor.main_bath_presence_sensor_fp2_presence_sensor_1",
                "light": "light.main_bath",
                "lux": "sensor.binary_sensor.main_bath_presence_sensor_fp2_presence_sensor_1",
                "last_lux": None,
                "override": "input_boolean.main_bath_automation"
            }
        }

        # Subscribe to presence sensor state changes
        for room, devices in self.rooms.items():
            self.listen_state(self.presence_detected, devices["sensor"], room=room)

    def presence_detected(self, entity, attribute, old, new, kwargs):
        """Handles light activation/deactivation based on presence."""
        room = kwargs["room"]
        light = self.rooms[room]["light"]
        lux_sensor = self.rooms[room]["lux"]
        override_switch = self.rooms[room]["override"]

        # Check if manual override is enabled
        if self.get_state(override_switch) == "off":
            self.log(f"Automation disabled for {room}, skipping light control.")
            return

        # Get lux threshold and current lux level
        lux_threshold = float(self.get_state("input_number.lux_threshold", default=100))
        current_lux = float(self.get_state(lux_sensor, default=0))

        # Skip turning on lights if lux is above threshold
        if current_lux > lux_threshold:
            self.log(f"Skipping light activation in {room} due to high lux ({current_lux} lx > {lux_threshold} lx).")
            return

        if new == "on":
            # Presence detected → Turn on the lights if brightness is needed
            self.rooms[room]["last_lux"] = current_lux
            brightness = self.get_dynamic_brightness(current_lux, lux_threshold)

            if brightness > 0:
                brightness_255 = self.percent_to_255(brightness)  # Convert 0-100% to 0-255
                self.turn_on(light, brightness=brightness_255, transition=2)  # ✅ Pass correct brightness
                self.log(f"Turning on {room} lights at {brightness}% brightness (Converted: {brightness_255}/255, Lux: {current_lux})")
            else:
                # 🔹 Special case: If brightness is set to 0%, override to minimum (1/255)
                self.log(f"Brightness set to 0%, updating {room} to minimum brightness (1/255).")
                self.turn_on(light, brightness=1, transition=2)

            # Store that the light was turned on
            self.rooms[room]["light_on"] = True  

            # Cancel any fade-out timer if it exists
            fade_timer = self.rooms.get(room, {}).get("fade_timer")
            if fade_timer is not None:
                self.cancel_timer(fade_timer)
                self.rooms[room]["fade_timer"] = None

        else:
            # Presence lost → Only schedule fade-out if light was actually turned on
            if self.rooms[room].get("light_on", False):
                fade_delay_raw = self.get_state("input_number.fade_delay", default="30")
                self.log(f"Raw fade delay value from Home Assistant: {fade_delay_raw}")

                try:
                    fade_delay = int(float(fade_delay_raw))  # Convert to float first, then to int
                except ValueError:
                    self.log(f"Invalid fade delay value: {fade_delay_raw}, defaulting to 30", level="WARNING")
                    fade_delay = 30

                self.log(f"Using fade delay: {fade_delay} seconds for {room}")

                fade_timer = self.run_in(self.adaptive_fade_out, fade_delay, room=room, light=light)
                
                # Store the fade-out timer reference for cancellation if presence comes back
                self.rooms[room]["fade_timer"] = fade_timer
            else:
                self.log(f"Skipping fade-out for {room} because lights never turned on.")


    def adaptive_fade_out(self, kwargs):
        """Fades out the light using the built-in transition if supported."""
        
        room = kwargs["room"]
        light = kwargs["light"]

        if not room or not light:
            self.log("Error: adaptive_fade_out called without required parameters!", level="ERROR")
            return

        # If presence is detected again, cancel fading
        if self.get_state(self.rooms[room]["sensor"]) == "on":
            self.log(f"Fade-out cancelled: Presence detected again in {room}.")
            return

        # Get transition duration from Home Assistant UI
        dim_duration = int(float(self.get_state("input_number.dimming_duration_seconds", default=3)))

        self.log(f"Using built-in transition to fade out {room} over {dim_duration} seconds.")

        # Use built-in transition
        self.turn_off(light, transition=dim_duration)
        self.log(f"{room} lights are fading out over {dim_duration} seconds.")



    def reset_lux_check(self, kwargs):
        """Resets last_lux so that the automation can check lux again after some time."""
        room = kwargs["room"]
        self.rooms[room]["last_lux"] = None

    def get_dynamic_brightness(self, lux, lux_threshold):
        """Determines light brightness based on user-configurable settings (0-100%)."""
        now = datetime.now()

        # Get user-defined time settings
        evening_start = self.get_state("input_datetime.evening_start", default="18:00:00")
        night_start = self.get_state("input_datetime.night_start", default="22:00:00")

        # Extract HH:MM format from the time string
        evening_start = evening_start[:5]  # Get only HH:MM
        night_start = night_start[:5]      # Get only HH:MM

        # Convert to datetime objects for comparison
        evening_time = datetime.strptime(evening_start, "%H:%M").time()
        night_time = datetime.strptime(night_start, "%H:%M").time()

        # Get brightness settings in 0-100% scale
        brightness_day = round(float(self.get_state("input_number.brightness_day", default=100)))
        brightness_evening = round(float(self.get_state("input_number.brightness_evening", default=70)))
        brightness_night = round(float(self.get_state("input_number.brightness_night", default=30)))

        # If lux is above threshold, don't turn on the light
        if lux > lux_threshold:
            self.log(f"Skipping light activation due to high lux ({lux} lx).")
            return 0  # No brightness needed

        # Determine brightness based on user-defined time settings
        if now.time() >= night_time:
            self.log(f"Using night time brightness setting. Current time: {now.time()}. Night time: {night_time}.")
            brightness = brightness_night
        elif now.time() >= evening_time:
            self.log(f"Using evening time brightness setting. Current time: {now.time()}. Evening time: {evening_time}.")
            brightness = brightness_evening
        else:
            self.log(f"Using day brightness setting. Current time: {now.time()}.")
            brightness = brightness_day

        self.log(f"Calculated brightness: {brightness}% (UI scale)")
        return brightness  # Always return brightness in 0-100%

    def percent_to_255(self, brightness_percent):
        """Converts 0-100% brightness to the 0-255 scale used by Home Assistant."""
        return round((brightness_percent / 100) * 255)
