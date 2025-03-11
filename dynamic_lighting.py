import appdaemon.plugins.hass.hassapi as hass
import time
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

    def get_room_setting(self, room, setting_name, default_value):
        """
        Fetches a room-specific setting from Home Assistant.
        Falls back to the global setting if no room-specific setting exists.

        Example:
        - Room: "kitchen"
        - Setting Name: "brightness_night"
        - Checks "input_number.brightness_night_kitchen" first.
        - Falls back to "input_number.brightness_night" if missing.
        """
        room_entity = f"input_number.{setting_name}_{room}"
        global_entity = f"input_number.{setting_name}"

        room_value = self.get_state(room_entity)
        if room_value is not None:
            self.log(f"Using per-room override for {room}: {setting_name} = {room_value}")
            return float(room_value)

        # Fall back to global setting
        global_value = self.get_state(global_entity)
        if global_value is not None:
            return float(global_value)

        return default_value

    def get_group_lights(self, group_entity):
        """Retrieves the individual lights in a light group from Home Assistant."""
        return self.get_state(group_entity, attribute="entity_id") or []

    def reliable_turn_on(self, light_group, brightness=None, transition=2, max_retries=3):
        """Ensures all lights in the group turn on correctly, retrying if necessary for individual lights."""
        
        group_lights = self.get_group_lights(light_group)
        if not group_lights:
            self.log(f"Warning: No individual lights found for {light_group}. Using group control only.", level="WARNING")
            group_lights = [light_group]  # Fallback to controlling the group entity itself

        # ✅ Issue the turn_on command to the group once
        self.turn_on(light_group, brightness=brightness, transition=transition)
        
        # ✅ Wait for the transition period to complete before verification
        time.sleep(transition * 2)

        # Verify each light in the group
        failed_lights = [light for light in group_lights if self.get_state(light) != "on"]

        if not failed_lights:
            self.log(f"All lights in {light_group} successfully turned on.")
            return
        
        self.log(f"Retrying failed lights in {light_group}: {failed_lights}", level="WARNING")

        # Retry failed lights individually
        for attempt in range(1, max_retries + 1):
            for light in failed_lights:
                self.turn_on(light, brightness=brightness, transition=transition)
            
            time.sleep(transition * 2)  # Wait again for the transition

            # Check again
            failed_lights = [light for light in failed_lights if self.get_state(light) != "on"]
            if not failed_lights:
                self.log(f"All remaining lights in {light_group} successfully turned on after {attempt} retry(ies).")
                return
        
        self.log(f"Failed to turn on all lights in {light_group} after {max_retries} attempts!", level="ERROR")


    def reliable_turn_off(self, light_group, transition=2, max_retries=3):
        """Ensures all lights in the group turn off correctly, retrying if necessary for individual lights."""

        group_lights = self.get_group_lights(light_group)
        if not group_lights:
            self.log(f"Warning: No individual lights found for {light_group}. Using group control only.", level="WARNING")
            group_lights = [light_group]  # Fallback to controlling the group entity itself

        # ✅ Issue the turn_off command to the group once
        self.turn_off(light_group, transition=transition)

        # ✅ Wait for the transition period to complete before verification
        time.sleep(transition * 2)

        # ✅ Refresh only the group lights' states
        self.force_refresh_states(group_lights)

        # Verify each light in the group
        failed_lights = [light for light in group_lights if self.get_state(light) != "off"]

        if not failed_lights:
            self.log(f"All lights in {light_group} successfully turned off.")
            return

        self.log(f"Retrying failed lights in {light_group}: {failed_lights}", level="WARNING")

        # Retry failed lights individually
        for attempt in range(1, max_retries + 1):
            for light in failed_lights:
                self.turn_off(light, transition=transition)
                self.log(f"Issued turn off command for {light} (Retry {attempt})")

            time.sleep(transition * 2)  # Wait again for the transition

            # ✅ Refresh only the failed lights' states before checking again
            self.force_refresh_states(failed_lights)

            # Check again
            failed_lights = [light for light in failed_lights if self.get_state(light) != "off"]

            if not failed_lights:
                self.log(f"All remaining lights in {light_group} successfully turned off after {attempt} retry(ies).")
                return

        self.log(f"Failed to turn off all lights in {light_group} after {max_retries} attempts!", level="ERROR")

    def presence_detected(self, entity, attribute, old, new, kwargs):
        """Handles light activation/deactivation based on presence."""
        room = kwargs["room"]
        light = self.rooms[room]["light"]
        lux_sensor = self.rooms[room]["lux"]
        override_switch = self.rooms[room]["override"]

        if self.get_state(override_switch) == "off":
            self.log(f"Automation disabled for {room}, skipping light control.")
            return

        # ✅ Fetch per-room or global settings
        lux_threshold = self.get_room_setting(room, "lux_threshold", 100)
        fade_delay = int(self.get_room_setting(room, "fade_delay", 30))

        current_lux = float(self.get_state(lux_sensor, default=0))

        if new == "on":
            self.rooms[room]["last_lux"] = current_lux
            brightness = self.get_dynamic_brightness(room, current_lux, lux_threshold)

            # Only check lux when turning lights ON
            if current_lux > lux_threshold:
                self.log(f"Skipping light activation in {room} due to high lux ({current_lux} lx > {lux_threshold} lx).")
                return

            if brightness > 0:
                brightness_255 = self.percent_to_255(brightness)
                self.reliable_turn_on(light, brightness=brightness_255, transition=2)
                self.rooms[room]["light_on"] = True
            else:
                self.log(f"Brightness set to 0%, updating {room} to minimum brightness (1/255).")
                self.reliable_turn_on(light, brightness=1, transition=2)

            fade_timer = self.rooms.get(room, {}).get("fade_timer")
            if fade_timer is not None:
                self.cancel_timer(fade_timer)
                self.rooms[room]["fade_timer"] = None

        else:
            # ✅ New Logic: Always check actual light state before skipping fade-out
            actual_light_state = self.get_state(light)
            if actual_light_state == "on":
                self.log(f"Presence lost in {room}, but {light} is still ON. Scheduling fade-out.")
                fade_timer = self.run_in(self.adaptive_fade_out, fade_delay, room=room, light=light)
                self.rooms[room]["fade_timer"] = fade_timer
            else:
                self.log(f"Presence lost in {room}, and all lights are already off. No fade-out needed.")


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
        self.reliable_turn_off(light, transition=dim_duration)
        self.log(f"{room} lights are fading out over {dim_duration} seconds.")



    def reset_lux_check(self, kwargs):
        """Resets last_lux so that the automation can check lux again after some time."""
        room = kwargs["room"]
        self.rooms[room]["last_lux"] = None

    def get_dynamic_brightness(self, room, lux, lux_threshold):
        """Determines light brightness based on user-configurable settings (global or per-room)."""
        now = datetime.now().time()

        # Get user-defined time settings
        evening_start = self.get_state("input_datetime.evening_start", default="18:00:00")[:5]
        night_start = self.get_state("input_datetime.night_start", default="22:00:00")[:5]

        evening_time = datetime.strptime(evening_start, "%H:%M").time()
        night_time = datetime.strptime(night_start, "%H:%M").time()

        # Retrieve sunrise time from Home Assistant
        sunrise_str = self.get_state("sun.sun", attribute="next_rising")
        
        try:
            if sunrise_str:
                # Remove microseconds if present
                sunrise_str = sunrise_str.split(".")[0]

                # Check for timezone information
                try:
                    sunrise = datetime.fromisoformat(sunrise_str).time()
                except ValueError:
                    self.log(f"Sunrise time format issue: {sunrise_str}. Trying fallback parsing.", level="WARNING")
                    sunrise = datetime.strptime(sunrise_str, "%Y-%m-%dT%H:%M:%S").time()
            else:
                raise ValueError("No sunrise data available")

        except Exception as e:
            self.log(f"Error parsing sunrise time: {e}. Defaulting to 06:30 AM.", level="WARNING")
            sunrise = datetime.strptime("06:30", "%H:%M").time()

        # ✅ Fetch room-specific brightness settings, fallback to global
        brightness_day = self.get_room_setting(room, "brightness_day", 100)
        brightness_evening = self.get_room_setting(room, "brightness_evening", 70)
        brightness_night = self.get_room_setting(room, "brightness_night", 30)

        # Prevent turning on lights if lux is too high (but don't use this for turning off)
        if lux > lux_threshold:
            self.log(f"Skipping light activation due to high lux ({lux} lx).")
            return 0

        # Determine brightness based on time
        if night_time <= now or now < sunrise:
            self.log(f"Using night brightness setting for {room}: {brightness_night}% (Current time: {now}, Night until: {sunrise})")
            return brightness_night
        elif evening_time <= now < night_time:
            self.log(f"Using evening brightness setting for {room}: {brightness_evening}% (Current time: {now})")
            return brightness_evening
        else:
            self.log(f"Using day brightness setting for {room}: {brightness_day}% (Current time: {now}, Sunrise: {sunrise})")
            return brightness_day

    def percent_to_255(self, brightness_percent):
        """Converts 0-100% brightness to the 0-255 scale used by Home Assistant."""
        return round((brightness_percent / 100) * 255)

    def force_refresh_states(self, entities):
        """Forces Home Assistant to refresh specific entity states to prevent stale readings."""
        if not entities:
            return
        time.sleep(0.5)  # Small delay before requesting fresh states
        self.call_service("homeassistant/update_entity", entity_id=entities)
