"""KMK Firmware for 6-key macropad with reactive RGB lighting.

Features:
- Per-key RGB colors on press
- Idle fade-out with rainbow animation recovery
- USB suspend/resume power management
"""

print("Starting")

import time
import board
from kmk.kmk_keyboard import KMKKeyboard
from kmk.scanners.keypad import KeysScanner
from kmk.keys import KC
from kmk.extensions.rgb import RGB, AnimationModes
from kmk.extensions import Extension

keyboard = KMKKeyboard()

# Configure 2 RGB LEDs on GP6 with reduced brightness to prevent glare
rgb = RGB(
    pixel_pin=board.GP6,
    num_pixels=2,
    val_limit=35,
    val_default=35,
)
rgb.animation_mode = AnimationModes.RAINBOW
keyboard.extensions.append(rgb)

class RGBReactiveIdleFade(Extension):
    """Extension that shows per-key colors on press and fades to rainbow when idle."""

    def __init__(self, rgb):
        self.rgb = rgb

        self.last_key_time = 0
        self.idle_timeout = 2.0

        self.fade_active = False
        self.fade_dir = -1
        self.fade_val = rgb.val_default
        self.fade_step = 3
        self.fade_interval = 0.01
        self.last_fade_tick = 0

        self.suspended = False

        # HSV colors (hue, saturation, value) mapped to each key index
        self.key_colors = {
            0: (0,   255, 120),
            1: (85,  255, 120),
            2: (170, 255, 120),
            3: (128, 255, 120),
            4: (200, 255, 120),
            5: (30,  255, 120),
        }

    def during_bootup(self, keyboard):
        self.last_key_time = time.monotonic()

    def on_key_pressed(self, keyboard, key, coord_int):
        if self.suspended:
            return

        self.last_key_time = time.monotonic()
        self.fade_active = False

        if coord_int in self.key_colors:
            h, s, v = self.key_colors[coord_int]
            # Keys 0-2 use LED 0, keys 3-5 use LED 1
            led = 0 if coord_int < 3 else 1

            self.rgb.animation_mode = AnimationModes.STATIC
            self.rgb.set_hsv(h, s, v, led)
            self.rgb.show()

    def after_hid_send(self, keyboard):
        if self.suspended:
            return

        now = time.monotonic()

        # Start fading out after idle timeout
        if not self.fade_active and now - self.last_key_time > self.idle_timeout:
            self.fade_active = True
            self.fade_dir = -1
            self.fade_val = self.rgb.val
            self.last_fade_tick = now

        if self.fade_active and now - self.last_fade_tick >= self.fade_interval:
            self.last_fade_tick = now
            self.fade_val += self.fade_dir * self.fade_step

            # Once fully faded out, switch to rainbow and fade back in
            if self.fade_val <= 0:
                self.fade_val = 0
                self.fade_dir = 1
                self.rgb.animation_mode = AnimationModes.RAINBOW

            elif self.fade_val >= self.rgb.val_default:
                self.fade_val = self.rgb.val_default
                self.fade_active = False

            self.rgb.val = self.fade_val
            self.rgb.show()

    def on_usb_suspend(self, keyboard):
        self.suspended = True
        self.rgb.off()
        self.rgb.show()

    def on_usb_resume(self, keyboard):
        self.suspended = False
        self.rgb.val = self.rgb.val_default
        self.rgb.animation_mode = AnimationModes.RAINBOW
        self.last_key_time = time.monotonic()
        self.rgb.show()

keyboard.extensions.append(RGBReactiveIdleFade(rgb))

# GPIO pins connected to each key switch (active low)
keyboard.matrix = KeysScanner(
    pins=(
        board.GP26,
        board.GP27,
        board.GP1,
        board.GP2,
        board.GP4,
        board.GP3,
    ),
    value_when_pressed=False,
)

# Key assignments: Volume Down, Volume Up, Mute, Copy, Paste, Enter
keyboard.keymap = [
    [
        KC.VOLD,
        KC.VOLU,
        KC.MUTE,
        KC.COPY,
        KC.PASTE,
        KC.ENTER,
    ]
]

if __name__ == "__main__":
    keyboard.go()
