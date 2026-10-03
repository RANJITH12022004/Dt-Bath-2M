#!/usr/bin/env bash
# DS1307/RTC0 is the clock source. Kernel RTC_HCTOSYS expects UTC in the chip.
set -euo pipefail
RTC_DEV="/dev/rtc0"
for _ in 1 2 3 4 5 6 7 8 9 10; do
  [[ -e "$RTC_DEV" ]] && break
  sleep 0.5
done
[[ -e "$RTC_DEV" ]] || exit 0
/usr/bin/timedatectl set-ntp false >/dev/null 2>&1 || true
/usr/bin/timedatectl set-local-rtc 0 >/dev/null 2>&1 || true
if [[ -x /usr/sbin/hwclock ]]; then
  /usr/sbin/hwclock -f "$RTC_DEV" --hctosys --utc >/dev/null 2>&1 || true
fi
