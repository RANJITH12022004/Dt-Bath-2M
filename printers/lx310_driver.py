import subprocess
from PIL import Image
import serial
import time
import os

# Configure your port
A4_PORT = "/dev/ttyAMA4"
A4_BAUD = 9600

# 1. Convert a PDF page into PNG using poppler-utils (pdftoppm)
def pdf_to_png(pdf_path, out_png):
    cmd = [
        "pdftoppm",
        "-png",
        "-r", "203",   # 203 DPI → matches LX-310 print resolution
        pdf_path,
        out_png.replace(".png", "")
    ]
    subprocess.run(cmd, check=True)

    # pdftoppm outputs file-1.png → rename
    first_output = out_png.replace(".png", "-1.png")
    os.rename(first_output, out_png)
    return out_png

# 2. Convert image to 1-bit bitmap (required by ESC/P2)
def to_1bit_png(source, out_png):
    img = Image.open(source).convert("1")  # 1-bit black & white
    img.save(out_png)
    return out_png

# 3. Convert bitmap to ESC/P2 raster data
def image_to_escp(image_path):
    img = Image.open(image_path)
    width, height = img.size
    data = list(img.getdata())

    # ESC/P2 commands
    esc = b'\x1B'  # ESC
    init = esc + b'@'  # Initialize printer

    output = bytearray()
    output += init

    bytes_per_row = (width + 7) // 8

    for y in range(height):
        row = bytearray()
        for x in range(0, width, 8):
            byte = 0
            for bit in range(8):
                if x + bit < width:
                    pixel = data[(y * width) + (x + bit)]
                    if pixel == 0:  # black pixel
                        byte |= (1 << (7 - bit))
            row.append(byte)

        # ESC * m nl nh <data>   (Graphics mode)
        nl = bytes_per_row & 0xFF
        nh = (bytes_per_row >> 8) & 0xFF
        output += esc + b'*' + b'\x00' + bytes([nl, nh]) + row + b'\n'

    output += b'\n\n\n'  # feed a bit
    return output

# 4. Send ESC/P2 data over UART to LX-310
def send_to_lx310(esc_bytes):
    with serial.Serial(A4_PORT, A4_BAUD, timeout=1) as ser:
        ser.write(esc_bytes)
        ser.flush()
        time.sleep(0.5)

# 5. Main function
def print_pdf(pdf_path):
    tmp_png = "/tmp/lx310_page.png"
    tmp_bw = "/tmp/lx310_bw.png"

    png = pdf_to_png(pdf_path, tmp_png)
    bw = to_1bit_png(png, tmp_bw)
    esc = image_to_escp(bw)
    send_to_lx310(esc)

    return True

