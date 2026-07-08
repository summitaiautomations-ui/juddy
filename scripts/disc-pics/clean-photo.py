#!/usr/bin/env python3
"""Cut the disc out of a photo (discs are circles), composite onto white,
crop with padding, and sharpen. Usage: discproc.py in.jpg out.jpg"""

import sys
import cv2
import numpy as np


def find_disc(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.medianBlur(gray, 7)
    h, w = gray.shape
    circles = cv2.HoughCircles(
        blur, cv2.HOUGH_GRADIENT, dp=1.5, minDist=w,
        param1=120, param2=40,
        minRadius=int(min(h, w) * 0.30), maxRadius=int(min(h, w) * 0.52),
    )
    if circles is None:
        return None
    x, y, r = circles[0][0]
    return int(x), int(y), int(r)


def main(src, dst):
    img = cv2.imread(src)
    found = find_disc(img)
    if not found:
        print(f"no disc circle found in {src}", file=sys.stderr)
        sys.exit(1)
    x, y, r = found
    h, w = img.shape[:2]
    print(f"{src}: disc at ({x},{y}) r={r} in {w}x{h}")

    # Feathered circular mask, trimmed slightly inside the rim edge
    mask = np.zeros((h, w), np.float32)
    cv2.circle(mask, (x, y), r - 2, 1.0, -1)
    mask = cv2.GaussianBlur(mask, (9, 9), 0)[..., None]

    white = np.full_like(img, 255)
    comp = (img.astype(np.float32) * mask + white.astype(np.float32) * (1 - mask)).astype(np.uint8)

    # Crop square around the disc with padding; pad with white where the
    # crop runs off the original frame
    pad = int(r * 0.10)
    side = 2 * (r + pad)
    x0, y0 = x - r - pad, y - r - pad
    canvas = np.full((side, side, 3), 255, np.uint8)
    sx0, sy0 = max(0, x0), max(0, y0)
    sx1, sy1 = min(w, x0 + side), min(h, y0 + side)
    canvas[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = comp[sy0:sy1, sx0:sx1]

    # Unsharp mask + slight contrast/saturation lift
    blur = cv2.GaussianBlur(canvas, (0, 0), 2.0)
    sharp = cv2.addWeighted(canvas, 1.6, blur, -0.6, 0)
    hsv = cv2.cvtColor(sharp, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] *= 1.10
    hsv[..., 1] = np.clip(hsv[..., 1], 0, 255)
    sharp = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # Upscale a touch so listings don't look tiny
    if side < 900:
        scale = 900 / side
        sharp = cv2.resize(sharp, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)

    cv2.imwrite(dst, sharp, [cv2.IMWRITE_JPEG_QUALITY, 92])
    print(f"wrote {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
