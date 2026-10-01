# Changelog

## [Unreleased] - Fixes

### Fixed
- **Stroke validation**: Per-basket counting and delta logic
  - Replaced single `lastStrokeReading` with `lastStrokeReadingByBasket` object
  - Each basket (1 and 2) now tracks stroke readings independently
  - Delta calculation only counts increases, not resets
  - Supports both `S1:123` and `S1=123` message formats

- **Temperature validation**: Per-basket preheat and navigation lock during validation
  - Added `sendPreheatForBasket(basketId, temp)` function for per-basket control
  - Only the selected validation basket receives preheat commands
  - Maintains `HEATER_STATE` object to preserve other basket state
  - Navigation is blocked while `window.validationInProgress` is true

- **On-screen keyboard**: Layout, touch handlers, caps/numeric/special keys fixed
  - Updated CSS to ensure keyboard covers bottom ~48% of screen (max-height: 340px)
  - Added `.keyboard-open .main-screen` padding to prevent content overlap
  - Enhanced `.osk-key` styles with proper touch-action and visual feedback
  - Added `.caps-active` class styling (blue background when caps lock is on)
  - Keyboard handlers support both touchstart and click events

- **Date/Time screen**: Rebuilt with reliable datetime-local control
  - Replaced complex UI with simple `datetime-local` input
  - Added status display for success/error feedback
  - Improved error handling with detailed backend error messages
  - Status element shows real-time feedback

- **Printing**: PDF generation + CUPS printing recommended; thermal printing fixed
  - A4 printing: Prefer server-side PDF generation via `/api/generate_pdf` then CUPS
  - Thermal printing: Fixed encoding (UTF-8/CP437 fallback) and chunked writes
  - All print operations use thread-safe locks to prevent UART contention
  - Backend error details (`data.detail` or `data.error`) now surfaced to UI

- **Error handling**: Backend error details surfaced to UI
  - All fetch calls now parse JSON and extract `data.detail` or `data.error`
  - Error messages shown in toasts/modals with full detail
  - Console logging for debugging

### Added
- `window.validationInProgress` global flag to block navigation during validation
- `lastStrokeReadingByBasket` object for per-basket stroke tracking
- `sendPreheatForBasket()` function for per-basket temperature control
- `HEATER_STATE` object to maintain heater state across baskets
- Enhanced error handling in all API calls
- Status display in Date/Time screen

### Changed
- `navigateTo()` now checks `window.validationInProgress` before allowing navigation
- `startValidationProcess()` sets `validationInProgress = true`
- `stopValidation()` and `completeValidation()` clear `validationInProgress = false`
- `startStrokeValidationReal()` uses per-basket tracking
- `applyValidationSetTemp()` uses `sendPreheatForBasket()` instead of global preheat
- `parseStrokeMsg()` supports both colon and equals separators
- Print functions show detailed error messages from backend
