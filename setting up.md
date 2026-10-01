setting up



/etc/systemd/system/bridge.service

sudo nano /etc/systemd/system/bridge.service




sudo systemctl daemon-reload
sudo systemctl enable bridge.service
sudo systemctl start bridge.service







Context for my project (please remember this for this chat):

I’m building a Raspberry Pi–based offline kiosk for a Tablet Disintegration Tester.

Frontend:
- Files in /opt/kiosk:
  - index.html
  - app.js
  - style.css
  - assets/ (images, logo, etc.)
  - vendor/ (local copies of Tailwind, Lucide, Chart.js)
- The UI runs in Chromium in kiosk mode.
- All hardware and storage access is via HTTP calls to a local backend at http://localhost:5000.

Backend:
- File: /opt/kiosk/bridge.py (Flask app).
- It does ALL hardware + storage work:
  - Talks to an ESP32 over UART (main Pi UART: /dev/serial0 @ 9600).
  - Implements these REST endpoints:
    - GET  /api/temp               -> send "TEMP" to ESP32 and parse "IR1:..,IR2:..,EXT1:..,EXT2:.."
    - POST /api/heater             -> map JSON to "PHW,xx.x,yy.y"
    - POST /api/motor              -> map JSON {id,cmd,value} to "START,Bx,xx.xW", "STOP", "STOP1", "STOP2"
    - POST /api/start-stroke       -> map to "START,STROKE,Bx,A"
    - GET  /api/stream             -> Server-Sent Events, streaming lines from ESP32 (S1:..,S2:.. each second)
    - GET/POST/DELETE /api/storage/<key>    -> JSON files on internal USB (/media/usb_internal/storage)
    - POST /api/storage/save_report         -> base64 -> PDF in /media/usb_internal/reports + FIFO cleanup if free < 4 GB
    - POST /api/print              -> {type:'a4',file:'...'} or {type:'thermal',text:'...'} via RS232 UARTs
    - POST /api/export_reports     -> copy PDFs + reports.json from /media/usb_internal to /media/usb_export
- It also serves static files:
  - GET /         -> /opt/kiosk/index.html
  - GET /<path>   -> other files from /opt/kiosk

Hardware:
- ESP32 connected to Pi main UART:
  - GPIO14 (TXD0, pin 8) -> ESP32 RX
  - GPIO15 (RXD0, pin 10) -> ESP32 TX
  - GND -> GND
- Two RS232 printers:
  - Thermal printer on a UART via MAX3232 (shows up as some /dev/ttyXXX, e.g. /dev/ttyTHRM)
  - A4 printer on another UART via MAX3232 (another /dev/ttyXXX, e.g. /dev/ttyA4)
- I will adjust THERMAL_PORT and A4_PORT in bridge.py to match the actual /dev/tty* names.

Storage:
- Internal USB pendrive permanently mounted at /media/usb_internal
  - /media/usb_internal/storage  -> JSON (StorageAdapter)
  - /media/usb_internal/reports  -> PDF reports
- External USB pendrive only used during export:
  - Mounted at /media/usb_export
- FIFO policy: when free space on internal USB < 4 GB, delete oldest PDFs in reports/ until free space >= 4 GB.

Service:
- systemd unit at /etc/systemd/system/bridge.service
  - ExecStart=/usr/bin/python3 /opt/kiosk/bridge.py
  - User=pi, WorkingDirectory=/opt/kiosk

Frontend behavior:
- app.js uses:
  - StorageAdapter with storageMode='bridge' using /api/storage/<key>
  - HardwareAdapter with hardwareMode='bridge' using the endpoints above.
  - EventSource('/api/stream') for stroke data from ESP32.
- Printing:
  - handlePrintA4() -> POST /api/print {"type":"a4","file": "<pdf name>"}
  - handlePrintThermal() -> POST /api/print {"type":"thermal","text":"..."}
- Export:
  - exportReports() -> POST /api/export_reports

What I’ll ask you from now on:
- Help debugging errors in bridge.py, systemd, UART, printers, or mounting USB.
- Help updating code (Python or JS) while keeping this architecture.
- Help with commands to run on the Pi: systemctl, lsblk, ls /dev/tty*, etc.

You don’t need to re-explain the architecture; you can assume everything above is already set up conceptually.

Now here is my actual question:

