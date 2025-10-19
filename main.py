#!/usr/bin/env python3
"""
screenrec.py — simple screen capture / recorder using mss + OpenCV.

Controls while running:
  r : toggle recording on/off
  q or ESC : quit
  s : save a single screenshot to disk (timestamped)
  
Usage examples:
  python screenrec.py                # records primary monitor, preview on screen
  python screenrec.py --monitor 2    # choose monitor index (1 = all, 2+ = physical monitors)
  python screenrec.py --outfile demo.mp4 --fps 20 --region 0 0 1280 720
"""

import time
import argparse
from datetime import datetime
import os

import numpy as np
import cv2
import mss

def parse_args():
    p = argparse.ArgumentParser(description="Simple screen capture/recorder (mss + OpenCV)")
    p.add_argument("--outfile", "-o", default="capture.mp4", help="Output filename (.mp4 or .avi)")
    p.add_argument("--fps", type=float, default=20.0, help="Target frames per second")
    p.add_argument("--monitor", type=int, default=1,
                   help="Monitor index to capture. 1 = full virtual screen, 2.. = individual monitors (mss monitors list)")
    p.add_argument("--region", type=int, nargs=4, metavar=('LEFT', 'TOP', 'WIDTH', 'HEIGHT'),
                   help="Optional capture region (left top width height). Overrides monitor if provided.")
    p.add_argument("--codec", default=None, help="FourCC codec (optional). Defaults chosen by extension.")
    return p.parse_args()

def select_codec_by_ext(filename, override=None):
    if override:
        return cv2.VideoWriter_fourcc(*override)
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".mp4", ".m4v"):
        return cv2.VideoWriter_fourcc(*"mp4v")
    if ext in (".avi",):
        return cv2.VideoWriter_fourcc(*"XVID")
    # fallback
    return cv2.VideoWriter_fourcc(*"XVID")

def timestamped_name(prefix="screenshot", ext=".png"):
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

def main():
    args = parse_args()
    sct = mss.mss()

    # Determine capture rectangle
    if args.region:
        left, top, w, h = args.region
        monitor_rect = {"left": left, "top": top, "width": w, "height": h}
    else:
        # mss monitors: index 0 is virtual full, others are each monitor
        monitors = sct.monitors
        if args.monitor < 0 or args.monitor >= len(monitors):
            print(f"Invalid monitor index {args.monitor}. Available: 0..{len(monitors)-1}")
            return
        # monitor index passed by user: use that monitor dict
        chosen = monitors[args.monitor]
        monitor_rect = {"left": chosen["left"], "top": chosen["top"],
                        "width": chosen["width"], "height": chosen["height"]}

    width = monitor_rect["width"]
    height = monitor_rect["height"]
    print(f"Capture rectangle: left={monitor_rect['left']} top={monitor_rect['top']} w={width} h={height}")

    # Prepare VideoWriter if recording toggled on
    fourcc = select_codec_by_ext(args.outfile, args.codec)
    writer = cv2.VideoWriter(args.outfile, fourcc, args.fps, (width, height))
    if not writer.isOpened():
        print("Warning: VideoWriter could not be opened. Check codec/filename. Will still show preview and allow screenshots.")
        writer = None

    recording = False
    last_time = time.time()
    frame_count = 0
    measured_fps = 0.0

    window_name = "ScreenRec - press 'r' to record, 's' to screenshot, 'q' to quit"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    # keep window reasonably sized relative to capture
    cv2.resizeWindow(window_name, min(1280, width), min(720, height))

    try:
        while True:
            t0 = time.time()
            img = np.array(sct.grab(monitor_rect))  # BGRA
            # Convert BGRA to BGR for OpenCV
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # Overlay status
            status_text = f"REC ON" if recording else "REC OFF"
            color = (0, 0, 255) if recording else (200, 200, 200)
            cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2, cv2.LINE_AA)
            cv2.putText(frame, f"FPS: {measured_fps:.1f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
            cv2.putText(frame, f"Press 'r' to toggle recording, 's' to save screenshot, 'q' to quit", (10, height - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

            # Show preview
            cv2.imshow(window_name, frame)

            # Write frame if recording and writer available
            if recording and writer:
                writer.write(frame)
                frame_count += 1

            # simple FPS measurement
            now = time.time()
            dt = now - last_time
            last_time = now
            measured_fps = measured_fps * 0.9 + (1.0 / dt) * 0.1 if dt > 0 else measured_fps

            key = cv2.waitKey(max(1, int(1000 / max(1, args.fps)))) & 0xFF
            if key == ord('r'):
                recording = not recording
                if recording:
                    print("Recording started.")
                else:
                    print("Recording stopped.")
            elif key == ord('s'):
                name = timestamped_name("screenshot", ".png")
                cv2.imwrite(name, frame)
                print(f"Saved screenshot: {name}")
            elif key == ord('q') or key == 27:
                print("Quitting.")
                break
            # otherwise continue loop

    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        if writer:
            writer.release()
            print(f"Saved video to {args.outfile}")
        cv2.destroyAllWindows()
        sct.close()

if __name__ == "__main__":
    main()
