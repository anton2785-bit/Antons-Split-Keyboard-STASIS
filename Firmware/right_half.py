"""
SplitKey38 — CircuitPython firmware
Right half (peripheral side)

This half does NOT connect to USB for HID.
It scans its matrix and sends key events to the left half over UART.

Protocol: 1 byte per event
  bit 7    : 1 = press, 0 = release
  bits 6-0 : key index 0-18

Pin mapping (same PCB, flipped — same physical pins):
  Rows: D6(P1.11), D8(P1.13), D9(P1.14), D4(P0.04)
  Cols: D0(P0.02), D1(P0.03), D2(P0.28), D3(P0.29), A4(P0.05)
  UART TX: D10 (P1.15) → left half RX
  UART RX: D7  (P1.12) ← left half TX (unused on right, but pin reserved)
"""

import board
import busio
import digitalio
import time

# ─── UART ────────────────────────────────────────────────────────────────────
uart = busio.UART(
    tx=board.D10,  # P1.15 → left half D7 (RX)
    rx=board.D7,   # P1.12 ← left half D10 (TX) — reserved, not used
    baudrate=38400,
    timeout=0,
)

# ─── MATRIX PINS ─────────────────────────────────────────────────────────────
ROW_PINS = [
    board.D6,   # P1.11 — row 0
    board.D8,   # P1.13 — row 1
    board.D9,   # P1.14 — row 2
    board.D4,   # P0.04 — row 3 (thumb)
]

COL_PINS = [
    board.D0,   # P0.02 — col 0
    board.D1,   # P0.03 — col 1
    board.D2,   # P0.28 — col 2
    board.D3,   # P0.29 — col 3
    board.A4,   # P0.05 — col 4
]

NUM_ROWS = len(ROW_PINS)
NUM_COLS = len(COL_PINS)

# ─── SETUP ───────────────────────────────────────────────────────────────────
rows = []
for pin in ROW_PINS:
    r = digitalio.DigitalInOut(pin)
    r.direction = digitalio.Direction.OUTPUT
    r.value = True
    rows.append(r)

cols = []
for pin in COL_PINS:
    c = digitalio.DigitalInOut(pin)
    c.direction = digitalio.Direction.INPUT
    c.pull = digitalio.Pull.UP
    cols.append(c)

# ─── STATE ───────────────────────────────────────────────────────────────────
prev_state = [False] * 19

# ─── MATRIX SCAN ─────────────────────────────────────────────────────────────
def scan_matrix():
    result = [False] * 19
    for row_idx, row in enumerate(rows):
        row.value = False
        time.sleep(0.000002)
        for col_idx, col in enumerate(cols):
            if not col.value:
                key_idx = row_idx * NUM_COLS + col_idx
                if key_idx < 19:
                    result[key_idx] = True
        row.value = True
    return result

# ─── MAIN LOOP ───────────────────────────────────────────────────────────────
print("SplitKey38 right half ready")

while True:
    current = scan_matrix()

    for i in range(19):
        if current[i] != prev_state[i]:
            # Encode: bit7 = press/release, bits 6-0 = index
            byte = (0x80 | i) if current[i] else i
            uart.write(bytes([byte]))
        prev_state[i] = current[i]

    time.sleep(0.001)
