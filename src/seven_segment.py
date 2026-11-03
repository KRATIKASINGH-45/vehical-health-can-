"""7-segment display model (common cathode) used by the receiver node.

Segment bit order: bit0=a, bit1=b, bit2=c, bit3=d, bit4=e, bit5=f, bit6=g.
The same table is used in firmware/stm32_receiver/main.c.
"""
SEG = {"0": 0x3F, "1": 0x06, "2": 0x5B, "3": 0x4F, "4": 0x66, "5": 0x6D, "6": 0x7D,
       "7": 0x07, "8": 0x7F, "9": 0x6F, " ": 0x00, "-": 0x40, "E": 0x79, "F": 0x71, "H": 0x76, "A": 0x77}


def encode_text(text: str):
    """Map each character to its segment byte; unsupported characters raise KeyError."""
    return [SEG[c] for c in text.upper()]


def render(text: str) -> str:
    """ASCII-art rendering of the display (3 rows) for the console dashboard."""
    rows = ["", "", ""]
    for byte in encode_text(text):
        on = lambda bit, ch: ch if byte >> bit & 1 else " "
        rows[0] += f" {on(0,'_')}  "
        rows[1] += f"{on(5,'|')}{on(6,'_')}{on(1,'|')} "
        rows[2] += f"{on(4,'|')}{on(3,'_')}{on(2,'|')} "
    return "\n".join(rows)
