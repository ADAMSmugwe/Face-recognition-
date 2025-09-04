#!/usr/bin/env python3
"""
Capture face images from webcam and save to known_faces/ for encoding.
"""

import os
import sys
import time
import argparse
import cv2
import face_recognition


def slugify_name(name: str) -> str:
    slug = name.strip().lower().replace(" ", "_").replace("-", "_")
    return "".join(ch for ch in slug if ch.isalnum() or ch == "_")


def get_largest_face(face_locations):
    if not face_locations:
        return None
    return max(face_locations, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))


def save_face_crop(frame, face_location, save_path):
    top, right, bottom, left = face_location
    h, w = frame.shape[:2]

    # Add padding
    pad = int(0.15 * max(bottom - top, right - left))
    top = max(0, top - pad)
    left = max(0, left - pad)
    bottom = min(h, bottom + pad)
    right = min(w, right + pad)

    crop = frame[top:bottom, left:right]
    cv2.imwrite(save_path, crop)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture face images from webcam")
    parser.add_argument("--name", required=True, help="Person's name to label images")
    parser.add_argument("--count", type=int, default=10, help="Number of images to capture")
    parser.add_argument("--delay", type=float, default=0.6, help="Seconds between captures")
    parser.add_argument("--output-dir", default="known_faces", help="Directory to save images")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (0,1,2...)")
    parser.add_argument("--model", default="hog", choices=["hog", "cnn"], help="Face detection model")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    person_slug = slugify_name(args.name)

    print("Webcam Face Capture")
    print("=" * 50)
    print("Instructions:")
    print(" - Position your face in the frame")
    print(" - Vary angles and expressions slightly")
    print(" - Press 'q' to quit early")
    print("=" * 50)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print("Error: Could not open camera")
        return 1

    captured = 0
    last_capture_time = 0.0

    try:
        while captured < args.count:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to read frame from camera")
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame, model=args.model)
            largest = get_largest_face(face_locations)

            # Draw box and HUD
            if largest is not None:
                t, r, b, l = largest
                cv2.rectangle(frame, (l, t), (r, b), (0, 255, 0), 2)
                cv2.putText(frame, f"Face detected", (l, max(0, t - 10)), cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 1)

            cv2.putText(frame, f"Capturing: {captured}/{args.count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, "Press 'q' to quit", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            cv2.imshow("Capture - " + args.name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break

            now = time.time()
            if largest is not None and now - last_capture_time >= args.delay:
                filename = f"{person_slug}_{captured+1:02d}.jpg"
                save_path = os.path.join(args.output_dir, filename)
                # Use original BGR frame for saving
                save_face_crop(frame, largest, save_path)
                captured += 1
                last_capture_time = now
                print(f"Saved: {save_path}")

        print(f"Finished. Captured {captured} image(s).")
        return 0 if captured > 0 else 2

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    sys.exit(main())


