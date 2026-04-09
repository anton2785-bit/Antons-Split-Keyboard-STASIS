"""
boot.py — runs before code.py, enables USB HID.
This file goes on the LEFT half only.
The right half does NOT need boot.py.

CircuitPython requires USB HID to be explicitly requested at boot.
"""

import usb_hid
import supervisor

# Enable keyboard HID device
usb_hid.enable((usb_hid.Device.KEYBOARD,))

# Optional: disable USB drive in production to prevent accidental edits
# supervisor.set_usb_identification("SplitKey38", "Keyboard")
