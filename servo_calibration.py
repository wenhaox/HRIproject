import machine
from machine import Pin, I2C
import utime
from servo import Servo # type: ignore

breath_servo = Servo(pin_id=27, min_us=500.0, max_us=2500.0, min_deg=0.0, max_deg=270.0, freq=50)  # Create a Servo object connected to pin 22 with specified parameters
breath_servo.write(140)  # Set the servo to a position (degrees)