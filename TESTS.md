# Acceptance Tests

## Manual Tests

### 1. Stroke Validation (Per-Basket)

**Test Case**: Select basket 1, start stroke validation
- Navigate to Validation → Select Basket 1 → Select Stroke → Start
- Confirm `stroke-counter` increments using only S1 input
- Verify basket 2 stroke readings are not used
- Check console logs show per-basket tracking

**Test Case**: Select basket 2, start stroke validation
- Navigate to Validation → Select Basket 2 → Select Stroke → Start
- Confirm `stroke-counter` increments using only S2 input
- Verify basket 1 stroke readings are not used
- Check that `lastStrokeReadingByBasket[2]` is updated, not `[1]`

**Expected Result**: Each basket tracks strokes independently; counter only increments for selected basket

### 2. Temperature Validation (Per-Basket)

**Test Case**: Temperature validation for basket 2 only
- Navigate to Validation → Select Basket 2 → Select Temperature
- Set temperature to X (e.g., 45.0°C)
- Click Apply/Start
- Confirm only basket 2 heater state changes
- Verify UI shows preheat indicator for basket 2 only
- Check console logs show `sendPreheatForBasket(2, 45.0)`
- Verify `HEATER_STATE.t2` is updated, `HEATER_STATE.t1` remains unchanged

**Expected Result**: Only the selected validation basket receives preheat; other basket unaffected

### 3. Navigation Blocking During Validation

**Test Case**: Attempt navigation during active validation
- Start stroke or temperature validation
- Attempt to navigate to Settings, Reports, or Dashboard
- Verify navigation is blocked with message: "Validation in progress — stop or complete validation before navigating away"
- Verify navigation to validation screens (stroke-validation, temp-validation) is allowed
- Stop validation and confirm navigation works normally

**Expected Result**: Navigation blocked except to validation screens; flag cleared on stop/complete

### 4. USB report export (`kioskexport_dt` parity)

Export copies non-empty PDFs from internal storage (`/media/usb_internal/reports`) to the external USB under `Disintegrator-Reports-Exported/`, using `/api/export_reports` (and optional `/api/prepare_export_usb` on login and before each export).

**Test Case**: Prepare mount (localhost)
- From the Pi: `curl -s -X POST http://127.0.0.1:5000/api/prepare_export_usb -H 'Content-Type: application/json' -d '{}'`
- Expect `ok: true` with `path` when a second USB stick is mounted at `/media/usb_export` or another eligible `/dev/sd*` mount; or `ok: false` with `no_external_usb_ready` when none present.

**Test Case**: Bulk export
- Ensure at least one `.pdf` exists under internal reports (generate a report PDF from the UI if needed).
- `curl -s -X POST http://127.0.0.1:5000/api/export_reports -H 'Content-Type: application/json' -d '{"filter":"all"}'`
- Expect `ok: true`, `exported` listing paths on the stick, `pdf_count` >= 1.

**Test Case**: UI
- Reports → **Export Reports** (orange) or report preview → **Export to USB** (green).
- Expect success toast/modal; files on USB in `Disintegrator-Reports-Exported/`.

**Expected Result**: No TE/ESP traffic required; mount helper is `scripts/udev_mount_export_usb.sh` (passwordless sudo on Pi).

### 5. On-Screen Keyboard

**Test Case**: Keyboard layout and functionality
- Open keyboard on mobile/touch device
- Verify keyboard covers bottom ~48% of screen (max-height: 340px)
- Confirm keyboard does not clip or overflow
- Verify `.keyboard-open .main-screen` adds padding to prevent content overlap

**Test Case**: Keyboard key functionality
- Press Caps Lock key → verify key shows blue background (`.caps-active` class)
- Press letter keys → verify uppercase when caps active, lowercase when not
- Press "123" key → verify numeric layer appears
- Press "ABC" key → verify letter layer returns
- Press Backspace → verify character deleted at caret
- Press Enter → verify keydown/keyup events dispatched
- Press Space → verify space inserted

**Test Case**: Touch and click handlers
- Tap keys on touch device → verify both touchstart and click events work
- Verify keys respond immediately without delay
- Confirm input field receives characters correctly
- Verify keyboard does not close while typing

**Expected Result**: Keyboard fully functional on touch and mouse; all special keys work; layout correct

### 5. Date & Time Screen

**Test Case**: Set date/time and apply
- Navigate to Settings → Edit Date & Time
- Verify simple `datetime-local` input is visible
- Select a new date/time
- Click Apply button
- Verify status message shows "Date/time set successfully" or error details
- Check network panel shows `POST /api/set_datetime` with correct payload
- Verify system time updated (or date matches sent value on Pi)

**Expected Result**: Date/time set successfully; status shows feedback; backend receives correct data

### 7. A4 Printing

**Test Case**: Print A4 via PDF generation
- Open a report preview
- Click "Print A4"
- Verify server generates PDF (check `/api/generate_pdf` call)
- Verify PDF sent to CUPS (check `/api/print_a4` with `pdf_path`)
- Inspect printed sheet for correct layout and spacing
- Verify no binary garbage or formatting issues

**Test Case**: Print A4 via image rendering (new)
- POST sample HTML to `/api/report_to_image` with `printer: "a4"`
- Verify HTML rendered to PNG image(s) in REPORTS_DIR
- Verify image printed via CUPS
- Check response shows `ok: true, printed: true, images: [...]`
- Inspect printed sheet for correct image output

**Test Case**: Print A4 fallback (if CUPS unavailable)
- If CUPS not configured, verify HTML converted to text
- Verify text sent to UART with proper chunking
- Check printed output is readable (may not match PDF exactly)

**Expected Result**: PDF prints with exact layout via CUPS; image rendering produces high-quality output; fallback text is readable

### 7. Thermal Printing

**Test Case**: Print thermal test
- Call `/api/print_test` endpoint
- Verify thermal printer receives ASCII "TEST" message
- Check printed output shows readable text (no noise or garbage)
- Verify full content printed (not truncated)

**Test Case**: Print thermal full report
- Open report preview
- Click "Print Thermal"
- Verify HTML converted to text (width ~40 chars)
- Verify encoding fallback (UTF-8 preferred, CP437 if needed)
- Check chunked writes with delays prevent truncation
- Verify full report content printed

**Test Case**: Print thermal via raster image (if PIL available)
- Open report preview
- Click "Print Thermal" (with use_raster=true)
- Verify HTML/PDF rendered to PNG image
- Verify image converted to ESC/POS raster format
- Check thermal printer receives raster data
- Verify printed output shows pixel-perfect image (not text)

**Expected Result**: Thermal prints readable ASCII; full content printed; no noise or truncation; raster mode produces image output when available

### 9. Error Handling

**Test Case**: Backend error details surfaced
- Trigger an API error (e.g., invalid endpoint, missing device)
- Verify error toast/modal shows `data.detail` or `data.error` from backend
- Check console shows full error response
- Verify error message is informative (not just "HTTP 500")

**Expected Result**: UI shows detailed backend error messages; console logs full response

### 10. Serial Device Configuration

**Test Case**: Verify device nodes exist
- Run: `ls -l /dev/ttyAMA4 /dev/ttyAMA3`
- Expect nodes to exist with proper permissions (crw-rw---- dialout)
- If missing, check kernel/device-tree overlays for GPIO mapping

**Test Case**: POST /api/print_thermal with device probe
- Send POST request to `/api/print_thermal` with test HTML
- Expect `ok: true` and `device=/dev/ttyAMA3` in response (or informative failure message)
- If device missing, expect error with `device` field showing `/dev/ttyAMA3` and helpful note

**Test Case**: POST /api/print_a4 with device probe
- Send POST request to `/api/print_a4` with test HTML (when CUPS disabled)
- Expect `ok: true` and `device=/dev/ttyAMA4` in response (or clear device failure)
- If device missing, expect error with `device` field showing `/dev/ttyAMA4` and helpful note

**Test Case**: GET /api/print_test endpoint
- Call `/api/print_test` endpoint
- Verify response includes `device` field for both A4 and thermal
- Check logs for "using discovered serial device" or device not found errors

**Expected Result**: All print endpoints return device path in success/error responses; missing devices show clear error messages with device path and troubleshooting notes

## Automated Test Placeholders

### API Tests

```javascript
// Test /api/print_test
async function testPrintTest() {
  const res = await fetch('/api/print_test');
  const data = await res.json();
  assert(res.status === 200);
  assert(data.a4 && typeof data.a4.ok === 'boolean');
  assert(data.thermal && typeof data.thermal.ok === 'boolean');
}

// Test /api/generate_pdf
async function testGeneratePdf() {
  const res = await fetch('/api/generate_pdf', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({html: '<html><body>Test</body></html>'})
  });
  const data = await res.json();
  assert(res.status === 200 || res.status === 500); // May fail if chromium not installed
  if (res.ok) {
    assert(data.pdf_path && typeof data.pdf_path === 'string');
  }
}

// Test /api/report_to_image (HTML input)
async function testReportToImageHtml() {
  const res = await fetch('/api/report_to_image', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      html: '<html><body><h1>Test Report</h1><p>Sample content</p></body></html>',
      dpi: 150
    })
  });
  const data = await res.json();
  assert(res.status === 200);
  assert(data.ok === true);
  assert(Array.isArray(data.images));
  assert(data.images.length > 0);
  // Verify images are in REPORTS_DIR
  data.images.forEach(path => {
    assert(path.includes('/reports/') || path.includes('reports'));
  });
}

// Test /api/report_to_image (PDF base64 input)
async function testReportToImagePdf() {
  // Create a minimal PDF base64 string (or use a real one)
  const pdfBase64 = 'JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPD4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovUmVzb3VyY2VzIDw8Ci9Gb250IDw8Ci9GMSA0IDAgUgo+Pgo+PgovQ29udGVudHMgNSAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL1R5cGUgL0ZvbnQKL1N1YnR5cGUgL1R5cGUxCi9CYXNlRm9udCAvSGVsdmV0aWNhCj4+CmVuZG9iagoxIDAgb2JqCjw8Ci9UeXBlIC9QYWdlCi9QYXJlbnQgMiAwIFIKL01lZGlhQm94IFswIDAgNjEyIDc5Ml0KL1Jlc291cmNlcyA8PAovRm9udCA8PAovRjEgNCAwIFIKPj4KPj4KL0NvbnRlbnRzIDUgMCBSCj4+CmVuZG9iago1IDAgb2JqCjw8Ci9MZW5ndGggNDQKPj4Kc3RyZWFtCkJUCi9GMSAxMiBUZgoxMDAgNzAwIFRkCihUZXN0KSBUagpFVAplbmRzdHJlYW0KZW5kb2JqCnhyZWYKMCA2CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAwOSAwMDAwMCBuIAowMDAwMDAwMDU4IDAwMDAwIG4gCjAwMDAwMDAxMTUgMDAwMDAgbiAKMDAwMDAwMDI2MyAwMDAwMCBuIAowMDAwMDAwMzQ3IDAwMDAwIG4gCnRyYWlsZXIKPDwKL1NpemUgNgovUm9vdCAxIDAgUgo+PgpzdGFydHhyZWYKNDQ1CiUlRU9G';
  const res = await fetch('/api/report_to_image', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      pdf_base64: pdfBase64,
      dpi: 150
    })
  });
  const data = await res.json();
  assert(res.status === 200);
  assert(data.ok === true);
  assert(Array.isArray(data.images));
}

// Test /api/report_to_image with printing (A4)
async function testReportToImageWithA4Print() {
  const res = await fetch('/api/report_to_image', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      html: '<html><body><h1>Test</h1></body></html>',
      printer: 'a4',
      printer_name: 'test_printer'  // May be None for default
    })
  });
  const data = await res.json();
  assert(res.status === 200);
  assert(data.ok === true);
  assert(typeof data.printed === 'boolean');
  // If printed fails, should have print_error
  if (!data.printed) {
    assert(typeof data.print_error === 'string');
  }
}

// Test /api/report_to_image with printing (thermal)
async function testReportToImageWithThermalPrint() {
  const res = await fetch('/api/report_to_image', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      html: '<html><body><h1>Test</h1></body></html>',
      printer: 'thermal'
    })
  });
  const data = await res.json();
  assert(res.status === 200);
  assert(data.ok === true);
  assert(typeof data.printed === 'boolean');
  // If printed fails (e.g., device not available), should have print_error
  if (!data.printed) {
    assert(typeof data.print_error === 'string');
  }
}
```

## Acceptance Criteria Checklist

- [ ] Starting stroke validation for basket 1 increments stroke counter using only S1; basket 2 unaffected
- [ ] Starting temperature validation for basket 2 only changes heater state for basket 2
- [ ] Navigation is blocked while `validationInProgress` is true
- [ ] OSK covers bottom area, all keys (Caps, 123, special, enter, backspace) work on touch and click
- [ ] Caps key shows blue active state when caps lock is on
- [ ] Date/time apply returns success and shows status
- [ ] A4 print via PDF prints with correct layout; thermal test prints readable ASCII (no noise)
- [ ] UI shows backend detail for errors
