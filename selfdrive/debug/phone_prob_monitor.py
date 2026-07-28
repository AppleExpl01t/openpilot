#!/usr/bin/env python3
"""Live readout of the driver monitoring phone classifier.

Use this to pick a _PHONE_THRESH that ignores whatever you actually hold
while driving without also ignoring a real phone.

  1. Park, start openpilot so dmonitoringmodeld is running, and run this.
  2. Sit normally holding the object that causes false positives. Watch the
     "session max" for the side you sit on. That is the number to beat.
  3. Repeat holding an actual phone the way you would use one. That gives
     you the upper bound.
  4. Set _PHONE_THRESH in selfdrive/monitoring/policy.py between the two,
     with margin above your everyday object.

Columns are the three detectors that are OR'd in policy.py:_get_distracted_types.
A '*' marks a detector currently reporting distracted.
"""

import argparse
import time

import cereal.messaging as messaging
from openpilot.selfdrive.monitoring.policy import DRIVER_MONITOR_SETTINGS


def main(side: str, interval: float) -> None:
  settings = DRIVER_MONITOR_SETTINGS()
  sm = messaging.SubMaster(['driverStateV2'])

  peak = {'left': 0., 'right': 0.}
  last_print = 0.

  print(f"phone thresh={settings._PHONE_THRESH}  blink thresh={settings._BLINK_THRESHOLD}  "
        f"face thresh={settings._FACE_THRESHOLD}")
  print("watching driverStateV2, ctrl-c to stop\n")

  while True:
    sm.update(100)
    if not sm.updated['driverStateV2']:
      continue

    ds = sm['driverStateV2']
    now = time.monotonic()

    for name in ('left', 'right'):
      peak[name] = max(peak[name], getattr(ds, f'{name}DriverData').phoneProb)

    if now - last_print < interval:
      continue
    last_print = now

    for name in ('left', 'right'):
      if side != 'both' and side != name:
        continue
      d = getattr(ds, f'{name}DriverData')
      blink = (d.leftBlinkProb + d.rightBlinkProb) * 0.5
      face_ok = d.faceProb > settings._FACE_THRESHOLD

      phone_hit = '*' if d.phoneProb > settings._PHONE_THRESH else ' '
      eye_hit = '*' if blink > settings._BLINK_THRESHOLD else ' '

      print(f"{name:>5}  face={d.faceProb:4.2f}{'' if face_ok else ' (no face)':10s}  "
            f"phone={d.phoneProb:4.2f}{phone_hit}  peak={peak[name]:4.2f}  "
            f"blink={blink:4.2f}{eye_hit}")


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("--side", default="both", choices=["left", "right", "both"], help="which seat to report")
  parser.add_argument("--interval", type=float, default=0.5, help="seconds between lines")
  args = parser.parse_args()

  try:
    main(args.side, args.interval)
  except KeyboardInterrupt:
    pass
