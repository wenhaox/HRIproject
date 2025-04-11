import machine
from machine import Pin, I2C
import utime
import _thread
from servo import Servo # type: ignore
import math

# Debug flag for printing status (set to False for production)
debug = True

# Flag to control the heartbeat action (True = heartbeat active, False = inactive)
HB_action = True

# Initialize the servo motor for breathing control
breath_servo = Servo(pin_id=6, min_us=500.0, max_us=2500.0, min_deg=0.0, max_deg=270.0, freq=50)
true_zero_position = 140

# Heartbeat parameters
HB_frequency = 50  # Beats per minute (90 bpm max)
HB_interval = int(60000 / HB_frequency)  # ms (converted to milliseconds from minutes)
lub_duration = 250  # ms
vibrate_duration = 150
loop_delay = 50  # ms delay to avoid overloading

# Define and initialize motor control pins for the heartbeat mechanism
HBm1_a = machine.Pin(26, machine.Pin.OUT)  # Motor 1 control pin A
HBm1_b = machine.Pin(27, machine.Pin.OUT)  # Motor 1 control pin B
HBm1_a.value(1)  # Set motor pin A to high (initial state)
HBm1_b.value(1)  # Set motor pin B to high (initial state)

# Global flag to signal the breathing thread to stop
stop_thread = False

# ---------- Easing Functions for Smooth Breathing Motion ----------

# Cubic easing function for smooth acceleration and deceleration (breathing in)
def easeInOutCubic(current_time, start_angle, end_angle, total_duration):
    t = current_time / total_duration  # Normalize time to a 0-1 range
    t = max(0, min(1, t))  # Clamp t between 0 and 1
    c = end_angle - start_angle  # Calculate the change in angle (motion range)
    t *= 2
    if t < 1:
        return c / 2 * t * t * t + start_angle  # First half of the motion
    else:
        t -= 2
        return c / 2 * (t * t * t + 2) + start_angle  # Second half of the motion

# Quadratic easing function for smooth acceleration and deceleration (breathing out)
def easeInOutQuad(current_time, start_angle, end_angle, total_duration):
    t = current_time / total_duration  # Normalize time to a 0-1 range
    t = max(0, min(1, t))  # Clamp t between 0 and 1
    c = end_angle - start_angle  # Calculate the change in angle (motion range)
    return -c / 2 * (math.cos(math.pi * t) - 1) + start_angle

# ---------- Breathing Motion Control Function ----------

# This function controls the breathing motion by adjusting the servo angle smoothly
def Breath_thread():
    global stop_thread
    
    print("1")
    
    # Breathing motion parameters
    start_angle = true_zero_position  # Starting position of the servo (degrees)
    end_angle = true_zero_position + 45   # End position of the servo (degrees)
    breath_duration = 2000  # Time for one full breath cycle (in milliseconds)
    pause_duration = 500  # Pause between breathing cycles (in milliseconds)
    steps = 100  # Number of intermediate steps for smooth motion
    
    while not stop_thread:  # Loop while the stop flag is not set
        # Breathing in phase (move servo from start_angle to end_angle)
        for i in range(steps):
            if stop_thread:  # Exit thread if stop signal is received
                return
            current_time = (i * breath_duration) / (steps - 1)  # Calculate the current time step
            current_angle = int(easeInOutCubic(current_time, start_angle, end_angle, breath_duration))  # Apply easing
            if debug:
                print(current_angle)  # Print the current servo angle for debugging
            breath_servo.write(current_angle)  # Move the servo to the calculated angle
            utime.sleep_ms(breath_duration // steps)  # Wait for the next step
            
        utime.sleep_ms(pause_duration)  # Pause before the breathing out phase
        
        # Breathing out phase (move servo from end_angle back to start_angle)
        for i in range(steps):
            if stop_thread:  # Exit thread if stop signal is received
                return
            current_time = (i * breath_duration) / (steps - 1)  # Calculate the current time step
            current_angle = int(easeInOutQuad(current_time, end_angle, start_angle, breath_duration))  # Apply easing
            if debug:
                print(current_angle)  # Print the current servo angle for debugging
            breath_servo.write(current_angle)  # Move the servo to the calculated angle
            utime.sleep_ms(breath_duration // steps)  # Wait for the next step
            
        utime.sleep_ms(pause_duration)  # Pause before the next breathing cycle

# Start the breathing thread in the background
_thread.start_new_thread(Breath_thread, ())

# ---------- Heartbeat Control in the Main Loop ----------

last_lub = utime.ticks_ms()  # Track the last "lub" (heartbeat) time

try:
    while True:
        if HB_action:  # Only proceed if heartbeat action is enabled
            current_time = utime.ticks_ms()
            elapsed_time = utime.ticks_diff(current_time, last_lub)

            if elapsed_time < vibrate_duration: # Activate motor for lub_duration
                HBm1_b.value(0)
                if debug:
                    print("Lub")
            elif elapsed_time >= lub_duration and elapsed_time < (lub_duration+vibrate_duration):
                # Activate motor for dub_duration
                HBm1_b.value(0)
                if debug:
                    print("Lub")
            else: 
                # Deactivate motor
                HBm1_b.value(1)
                if debug:
                    print("NA")

            # Reset timer after the full interval
            if elapsed_time >= HB_interval-loop_delay:
                last_lub = utime.ticks_ms()  # Adjust for delay

            # Small delay to avoid overloading the system
            utime.sleep_ms(loop_delay)
        else:
            if debug:
                print("No HB")  # Debugging: no heartbeat when HB_action is False
            else:
                break  # Exit the loop if no heartbeat and debug is disabled

except KeyboardInterrupt:
    # Graceful handling of program interruption (e.g., Ctrl+C)
    print("Program interrupted. Stopping thread...")
    stop_thread = True  # Signal the breathing thread to stop
    utime.sleep_ms(1000)  # Allow time for the thread to exit
    breath_servo.write(80)  # Reset the servo to a neutral position
    print("Thread stopped.")