#!/usr/bin/env python3
"""Live readout of the driver monitoring phone classifier.

Use this to pick a _PHONE_THRESH that ignores whatever you actually hold
while driving without also ignoring a real phone.

  1. Park, start openpilot so dmonitoringmodeld is running, and run this.
  2. Sit normally holding the object that causes false positives, for a
     minute or so. Note "duty" and "run".
  3. Repeat holding an actual phone the way you would use one.
  4. Compare. 'peak' is the highest probability seen, 'duty' is the share of
     time above _PHONE_THRESH, and 'run' is the longest unbroken stretch
     above it.

If peak separates the two, raise _PHONE_THRESH between them. If it does not
(a wallet and a phone can both sit above 0.9), the discriminator is time
instead: the policy only latches 'phone' when the detection holds above
threshold for more than roughly 75% of the time, so a duty below that never
accumulates. Set _PHONE_SUSTAIN_TIME above your object's 'run' and below the
phone's.

Columns are the detectors OR'd together in policy.py:_get_distracted_types.
A '*' marks one currently reporting distracted.
"""

import argparse
import time

import cereal.messaging as messaging
from openpilot.common.realtime import DT_DMON
from openpilot.selfdrive.monitoring.policy import DRIVER_MONITOR_SETTINGS


def main(side: str, interval: float) -> None:
  settings = DRIVER_MONITOR_SETTINGS()
  sm = messaging.SubMaster(['driverStateV2'])

  peak = {'left': 0., 'right': 0.}
  frames = {'left': 0, 'right': 0}
  above = {'left': 0, 'right': 0}
  run = {'left': 0, 'right': 0}
  longest = {'left': 0, 'right': 0}
  last_print = 0.

  print(f"phone thresh={settings._PHONE_THRESH}  sustain={settings._PHONE_SUSTAIN_TIME}s  "
        f"release={settings._PHONE_RELEASE_TIME}s")
  print(f"blink thresh={settings._BLINK_THRESHOLD}  face thresh={settings._FACE_THRESHOLD}")
  print("watching driverStateV2, ctrl-c to stop\n")

  while True:
    sm.update(100)
    if not sm.updated['driverStateV2']:
      continue

    ds = sm['driverStateV2']
    now = time.monotonic()

    for name in ('left', 'right'):
      p = getattr(ds, f'{name}DriverData').phoneProb
      peak[name] = max(peak[name], p)
      frames[name] += 1
      if p > settings._PHONE_THRESH:
        above[name] += 1
        run[name] += 1
        longest[name] = max(longest[name], run[name])
      else:
        run[name] = 0

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
      duty = above[name] / max(frames[name], 1)
      # driverStateV2 publishes at the DM rate, so frames map onto DT_DMON
      longest_s = longest[name] * DT_DMON

      print(f"{name:>5}  face={d.faceProb:4.2f}{'' if face_ok else ' (no face)':10s}  "
            f"phone={d.phoneProb:4.2f}{phone_hit}  peak={peak[name]:4.2f}  "
            f"duty={duty:5.1%}  run={longest_s:5.1f}s  blink={blink:4.2f}{eye_hit}")


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument("--side", default="both", choices=["left", "right", "both"], help="which seat to report")
  parser.add_argument("--interval", type=float, default=0.5, help="seconds between lines")
  args = parser.parse_args()

  try:
    main(args.side, args.interval)
  except KeyboardInterrupt:
    pass
