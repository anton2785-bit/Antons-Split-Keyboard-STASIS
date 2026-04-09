"""
SplitKey38 — CircuitPython firmware
Left half (USB host side)

Hardware:  Seeed XIAO nRF52840
Matrix:    5 cols × 4 rows, COL2ROW diodes (1N4148W)
Split:     UART over D7(TX) / D6(RX) between halves
USB HID:   left half plugged into PC via USB-C

Pin mapping (from schematic):
  Rows (driven LOW, input pulled HIGH):
    ROW0 → D6  / P1.11
    ROW1 → D7  / P1.12   ← also UART RX from right half
    ROW2 → D8  / P1.13
    ROW3 → D9  / P1.14   (thumb row)

  Cols (read):
    COL0 → D0  / P0.02
    COL1 → D1  / P0.03
    COL2 → D2  / P0.28
    COL3 → D3  / P0.29
    COL4 → D4  / P0.04

NOTE: If you use D6/D7 for UART, free up two other pins for ROW0/ROW1.
      Adjust ROW_PINS below to match your final PCB traces.
      UART_TX → D10 (P1.15 / MOSI) on left half
      UART_RX → D7  (P1.12)        on left half  ← conflicts with ROW1
      Recommended: use D10(TX) on left, D10(RX) on right, cross-wired.
      See WIRING NOTE at bottom of file.
"""

import board
import busio
import digitalio
import usb_hid
import time
import struct

from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

# ─── UART (inter-half communication) ────────────────────────────────────────
# Left half receives key events from right half over UART.
# Protocol: single byte per event — high bit = press(1)/release(0), low 7 bits = key index (0-18)
uart = busio.UART(
    tx=board.D10,   # P1.15 — to right half RX
    rx=board.D7,    # P1.12 — from right half TX
    baudrate=38400,
    timeout=0,      # non-blocking
)

# ─── MATRIX PINS ────────────────────────────────────────────────────────────
# Rows: output, driven LOW to scan
ROW_PINS = [
    board.D6,   # P1.11 — row 0 (SW1 SW3 SW6 SW7 SW9)
    board.D8,   # P1.13 — row 1 (SW11 SW13 SW15 SW17 SW19)  ← skip D7 (UART)
    board.D9,   # P1.14 — row 2 (SW21 SW23 SW25 SW27 SW29)
    board.D4,   # P0.04 — row 3 / thumb (SW31 SW33 SW35 SW37)
]

# Cols: input, pulled HIGH; LOW = key pressed
COL_PINS = [
    board.D0,   # P0.02 — col 0
    board.D1,   # P0.03 — col 1
    board.D2,   # P0.28 — col 2
    board.D3,   # P0.29 — col 3
    board.A4,   # P0.05 — col 4  (D4 used for row, use A4/D5 instead)
]

NUM_ROWS = len(ROW_PINS)
NUM_COLS = len(COL_PINS)

# ─── LAYER DEFINITIONS ──────────────────────────────────────────────────────
# Index = row * 5 + col  (left side, 0-18)
# None = transparent (falls through to BASE)
# Key index layout:
#   row0: [0][1][2][3][4]   → Tab Q W E R
#   row1: [5][6][7][8][9]   → Esc A S D F
#   row2: [10][11][12][13][14] → Sft Z X C V
#   row3: [15][16][17][18]  → Ctrl GUI Alt Spc   (thumb, col4 unused)

KC = Keycode

BASE_L = [
    # row 0
    KC.TAB,         KC.Q,       KC.W,       KC.E,       KC.R,
    # row 1
    KC.ESCAPE,      KC.A,       KC.S,       KC.D,       KC.F,
    # row 2
    KC.LEFT_SHIFT,  KC.Z,       KC.X,       KC.C,       KC.V,
    # row 3 (thumb — only 4 keys, index 15-18, col4=None)
    KC.LEFT_CONTROL, KC.LEFT_GUI, KC.LEFT_ALT, KC.SPACE,
]

NAV_L = [
    # row 0
    None, None, None, None, None,
    # row 1
    None, None, None, None, None,
    # row 2
    None, None, None, None, None,
    # row 3 (thumb)
    None, None, None, None,
]

SYM_L = [
    # row 0
    KC.GRAVE, KC.ONE,  KC.TWO,   KC.THREE, KC.FOUR,
    # row 1
    None,     KC.EXCLAMATION_POINT, KC.AT, KC.POUND, KC.DOLLAR,
    # row 2
    None,     None,    None,     None,     None,
    # row 3 (thumb)
    None,     None,    None,     None,
]

# Right half keymaps
# Key index 0-18, same row/col structure, mirrored columns
# Right row0: T Y U I O  → col order: [col4..col0] visually but wired same
BASE_R = [
    # row 0
    KC.T,           KC.Y,       KC.U,       KC.I,       KC.O,
    # row 1
    KC.G,           KC.H,       KC.J,       KC.K,       KC.L,
    # row 2
    KC.B,           KC.N,       KC.M,       KC.COMMA,   KC.PERIOD,
    # row 3 (thumb)
    KC.RETURN,      None,       None,       KC.RIGHT_SHIFT,  # MO1/MO2 handled in logic
]

NAV_R = [
    # row 0
    KC.PAGE_UP,   KC.HOME,    KC.UP_ARROW,   KC.END,        KC.DELETE,
    # row 1
    KC.PAGE_DOWN, KC.LEFT_ARROW, KC.DOWN_ARROW, KC.RIGHT_ARROW, KC.INSERT,
    # row 2
    None,         None,       None,          None,          KC.BACKSPACE,
    # row 3 (thumb)
    None,         None,       None,          None,
]

SYM_R = [
    # row 0
    KC.FIVE,      KC.SIX,     KC.SEVEN,      KC.EIGHT,      KC.NINE,
    # row 1
    KC.PERCENT,   KC.CARET,   KC.AMPERSAND,  KC.ASTERISK,   KC.ZERO,
    # row 2
    None,         KC.LEFT_BRACKET, KC.RIGHT_BRACKET, KC.MINUS, KC.EQUALS,
    # row 3 (thumb)
    None,         None,       None,          None,
]

LAYERS_L = [BASE_L, NAV_L, SYM_L]
LAYERS_R = [BASE_R, NAV_R, SYM_R]

# Right thumb key indices that activate layers
RIGHT_MO1 = 16   # MO(NAV)  — index in right keymap row3 col1
RIGHT_MO2 = 17   # MO(SYM)  — index in right keymap row3 col2

# ─── SETUP ──────────────────────────────────────────────────────────────────
rows = []
for pin in ROW_PINS:
    r = digitalio.DigitalInOut(pin)
    r.direction = digitalio.Direction.OUTPUT
    r.value = True   # idle HIGH
    rows.append(r)

cols = []
for pin in COL_PINS:
    c = digitalio.DigitalInOut(pin)
    c.direction = digitalio.Direction.INPUT
    c.pull = digitalio.Pull.UP
    cols.append(c)

kbd = Keyboard(usb_hid.devices)

# ─── STATE ──────────────────────────────────────────────────────────────────
left_state  = [False] * 19   # current pressed state, left half
right_state = [False] * 19   # received from right half over UART

prev_left  = [False] * 19
prev_right = [False] * 19

active_layer = 0

# ─── MATRIX SCAN ─────────────────────────────────────────────────────────────
def scan_matrix():
    """Returns a 19-element list of booleans — True = key pressed."""
    result = [False] * 19
    for row_idx, row in enumerate(rows):
        row.value = False   # drive LOW
        time.sleep(0.000002)  # 2µs settle
        for col_idx, col in enumerate(cols):
            if not col.value:   # LOW = pressed (COL2ROW + pull-up)
                key_idx = row_idx * NUM_COLS + col_idx
                if key_idx < 19:
                    result[key_idx] = True
        row.value = True    # restore HIGH
    return result

# ─── UART RECEIVE ────────────────────────────────────────────────────────────
def read_uart():
    """
    Reads all pending bytes from UART.
    Protocol: 1 byte per event
      bit 7 : 1 = press, 0 = release
      bits 6-0 : key index 0-18
    """
    while True:
        data = uart.read(1)
        if data is None or len(data) == 0:
            break
        byte = data[0]
        pressed  = bool(byte & 0x80)
        key_idx  = byte & 0x7F
        if 0 <= key_idx <= 18:
            right_state[key_idx] = pressed

# ─── LAYER RESOLUTION ────────────────────────────────────────────────────────
def resolve_key(keymap_list, idx):
    """Walk layers top-down, return first non-None keycode."""
    for layer in range(len(keymap_list) - 1, -1, -1):
        kc = keymap_list[layer][idx]
        if kc is not None:
            return kc
    return None

def get_active_layers():
    """Return list of active layer indices based on held MO keys."""
    layers = [0]   # base always active
    if right_state[RIGHT_MO1]:
        layers.append(1)
    if right_state[RIGHT_MO2]:
        layers.append(2)
    return layers

# ─── MAIN LOOP ───────────────────────────────────────────────────────────────
print("SplitKey38 ready")

while True:
    # 1. Read right half events from UART
    read_uart()

    # 2. Scan left half matrix
    left_state = scan_matrix()

    # 3. Determine active layers
    active_layers = get_active_layers()

    # 4. Build layered keymaps for this tick
    layered_l = [BASE_L, NAV_L, SYM_L]
    layered_r = [BASE_R, NAV_R, SYM_R]

    # 5. Process left half changes
    for i in range(19):
        if left_state[i] != prev_left[i]:
            kc = None
            # Walk layers top-down
            for layer in reversed(active_layers):
                candidate = layered_l[layer][i]
                if candidate is not None:
                    kc = candidate
                    break
            if kc is not None:
                if left_state[i]:
                    kbd.press(kc)
                else:
                    kbd.release(kc)
            prev_left[i] = left_state[i]

    # 6. Process right half changes
    for i in range(19):
        # Skip MO keys — they control layers, not HID keycodes
        if i in (RIGHT_MO1, RIGHT_MO2):
            prev_right[i] = right_state[i]
            continue
        if right_state[i] != prev_right[i]:
            kc = None
            for layer in reversed(active_layers):
                candidate = layered_r[layer][i]
                if candidate is not None:
                    kc = candidate
                    break
            if kc is not None:
                if right_state[i]:
                    kbd.press(kc)
                else:
                    kbd.release(kc)
            prev_right[i] = right_state[i]

    time.sleep(0.001)   # 1ms scan rate


# ─── WIRING NOTE ─────────────────────────────────────────────────────────────
# Left XIAO D10 (TX) ──────────────── Right XIAO D6  (RX)
# Left XIAO D7  (RX) ──────────────── Right XIAO D10 (TX)
# Left GND           ──────────────── Right GND
# No level shifter needed — both 3.3V
#
# The right half runs right_half.py (see that file).
# Only the LEFT half connects to USB.
