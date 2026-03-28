from server.interfaces.MissionModule import MissionModule
import time
import os
from server.controllers.Aircraft import Aircraft

class Delivery(MissionModule):
    """
    This mission module controls a sequence where the aircraft can land within 5m
    of a casualty, release a package, take-off, and then return-to-home (RTH).
    """

    def start(self, options):
        """
        Start the mission module.

        If you need information to start with, then these can be provided in the
        `options` parameter.
        """
        CASUALTY_LAT = options.get('casualty_lat', 51.4235372)
        CASUALTY_LON = options.get('casualty_lon', -2.6702034)
        SERVO_CHAN    = options.get('servo_chan', 14)  # Aux Out 6

        # --- CONNECT ---
        aircraft = options['aircraft']
        if not aircraft.connected:
            aircraft.connect(os.getenv("AIRCRAFT_CONNECTION_STRING"))

        print("Locking payload mechanism...")
        aircraft.set_servo(SERVO_CHAN, 1100)

        # --- PRE-FLIGHT ---
        print("\n--- PRE-FLIGHT ---")
        pos = aircraft.get_position()
        if not pos:
            print("CRITICAL: Could not get home position. Aborting.")
            return False
        HOME_LAT, HOME_LON, _ = pos
        print(f"Home position locked: {HOME_LAT}, {HOME_LON}")

        aircraft.set_mode("GUIDED")
        if not aircraft.wait_for_mode("GUIDED"):
            print("CRITICAL: GUIDED mode not confirmed. Aborting.")
            return False

        if not aircraft.arm():
            print("CRITICAL: Failed to arm. Aborting.")
            return False

        if not aircraft.takeoff(20):
            print("CRITICAL: Takeoff failed. Aborting.")
            return False

        # --- DELIVERY SEQUENCE ---
        print("\n--- INITIATING DELIVERY ---")

        print("Flying to casualty...")
        aircraft.goto(CASUALTY_LAT, CASUALTY_LON, 20)

        print("Calculating 7.5m offset (East)...")
        offset_lat, offset_lon = Aircraft.get_offset_location(
            CASUALTY_LAT, CASUALTY_LON, distance_m=7.5, bearing_deg=90)
        aircraft.goto(offset_lat, offset_lon, 20)

        print("Descending to 10m for terrain check...")
        aircraft.goto(offset_lat, offset_lon, 10, tolerance_m=1.0)

        if not Aircraft.ask_hitl("Terrain safe to land?"):
            print("ABORTED by operator. Climbing to 20m.")
            aircraft.goto(offset_lat, offset_lon, 20)
            return False

        # --- DELIVERY AND RETRY LOOP ---
        delivery_successful = False
        attempt = 1
        MAX_ATTEMPTS = 3

        while not delivery_successful:
            print(f"\n--- DELIVERY ATTEMPT {attempt} OF {MAX_ATTEMPTS} ---")

            if not aircraft.land():
                print("CRITICAL: Landing/disarm timed out. Aborting.")
                return False
            print("Touchdown confirmed.")

            # Servo dwell times kept as time.sleep() intentionally —
            # MAVLink has no servo position feedback, these are mechanical dwell times.
            print("Releasing payload stage 1 (1600 PWM)...")
            aircraft.set_servo(SERVO_CHAN, 1600)
            time.sleep(2)
            print("Releasing payload stage 2 (2200 PWM)...")
            aircraft.set_servo(SERVO_CHAN, 2200)
            time.sleep(2)

            print("Re-arming for inspection flight...")
            aircraft.set_mode("GUIDED")
            if not aircraft.wait_for_mode("GUIDED"):
                print("CRITICAL: GUIDED mode not confirmed on re-arm. Aborting.")
                return False

            if not aircraft.arm():
                print("CRITICAL: Failed to re-arm. Aborting.")
                return False

            if not aircraft.takeoff(10):
                print("CRITICAL: Re-takeoff failed. Aborting.")
                return False

            # Move horizontally to the offset position after climbing
            aircraft.goto(offset_lat, offset_lon, 10, tolerance_m=1.0)

            if Aircraft.ask_hitl("Delivery successful?"):
                delivery_successful = True
                print("Confirmation received.")
            else:
                if attempt >= MAX_ATTEMPTS:
                    print(f"\nCRITICAL: Deployment failed after {MAX_ATTEMPTS} attempts. Aborting.")
                    aircraft.goto(offset_lat, offset_lon, 20)
                    return False
                print(f"Attempt {attempt} failed. Retrying...")
                attempt += 1

        # --- RETURN TO LAUNCH ---
        print("Delivery confirmed. Ascending to cruise altitude...")
        aircraft.goto(offset_lat, offset_lon, 20)

        print("\n--- INITIATING RETURN TO LAUNCH ---")
        aircraft.goto(HOME_LAT, HOME_LON, 20)

        print("Arrived at home. Landing...")
        if not aircraft.land(timeout_s=120):
            print("WARNING: Final disarm confirmation timed out.")
            return False

        print("\n==========================================")
        print("MISSION ACCOMPLISHED. SHUTTING DOWN.")
        print("==========================================")
        return True