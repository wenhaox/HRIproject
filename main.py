import machine
import sys
import utime
import math
from machine import Pin, I2C
from servo import Servo  # type: ignore
import math
import select

# Debug flag for printing status (set to False for production)
debug = True

# Flag to control the heartbeat action (True = heartbeat active, False = inactive)
HB_action = False
breath_enabled = True
last_print = utime.ticks_ms()  # used for printing "nothing sent" every 5 seconds

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
HBm1_a.value(1)
HBm1_b.value(1)

# ---------- Easing Functions ----------
def easeInOutCubic(current_time, start_angle, end_angle, total_duration):
    t = current_time / total_duration
    t = max(0, min(1, t))
    c = end_angle - start_angle
    t *= 2
    if t < 1:
        return c / 2 * t * t * t + start_angle
    else:
        t -= 2
        return c / 2 * (t * t * t + 2) + start_angle

def easeInOutQuad(current_time, start_angle, end_angle, total_duration):
    t = current_time / total_duration
    t = max(0, min(1, t))
    c = end_angle - start_angle
    return -c / 2 * (math.cos(math.pi * t) - 1) + start_angle

# ---------- Breathing Motion ----------
def do_breath_cycle():
    global breath_enabled
    start_angle = true_zero_position - 10
    end_angle = true_zero_position + 35
    breath_duration = 2000
    pause_duration = 500
    steps = 100

    for i in range(steps):
        current_time = (i * breath_duration) / (steps - 1)
        current_angle = int(easeInOutCubic(current_time, start_angle, end_angle, breath_duration))
        if debug:
            print(current_angle)
        breath_servo.write(current_angle)
        utime.sleep_ms(breath_duration // steps)

    utime.sleep_ms(pause_duration)

    for i in range(steps):
        current_time = (i * breath_duration) / (steps - 1)
        current_angle = int(easeInOutQuad(current_time, end_angle, start_angle, breath_duration))
        if debug:
            print(current_angle)
        breath_servo.write(current_angle)
        utime.sleep_ms(breath_duration // steps)

    utime.sleep_ms(pause_duration)
    breath_enabled = False

# ---------- Main Loop ----------
poll = select.poll()
poll.register(sys.stdin, select.POLLIN)

last_lub = utime.ticks_ms()

while True:
    # Check USB serial input non-blockingly
    if poll.poll(0):  # Non-blocking check
        line = sys.stdin.readline()
        if line:
            breath_enabled = True
            if debug:
                print("Breathing enabled; received:", line.strip())
    else:
        if utime.ticks_diff(utime.ticks_ms(), last_print) > 5000:
            print("nothing sent")
            last_print = utime.ticks_ms()

    if breath_enabled:
        do_breath_cycle()

    if HB_action:
        current_time = utime.ticks_ms()
        elapsed_time = utime.ticks_diff(current_time, last_lub)

        if elapsed_time < vibrate_duration:
            HBm1_b.value(0)
            if debug:
                print("Lub")
        elif elapsed_time >= lub_duration and elapsed_time < (lub_duration + vibrate_duration):
            HBm1_b.value(0)
            if debug:
                print("Lub")
        else:
            HBm1_b.value(1)
            if debug:
                print("NA")

        if elapsed_time >= HB_interval - loop_delay:
            last_lub = utime.ticks_ms()
        utime.sleep_ms(loop_delay)

    utime.sleep_ms(10)
