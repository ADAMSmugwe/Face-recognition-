#!/usr/bin/env python3
"""
Import local images into known_faces/ with validation and optional renaming.
Usage examples:
  python3 import_faces.py --src "/path/to/folder" --name "John Doe"
  python3 import_faces.py --src "/path/A.jpg" --name "Alice"
  python3 import_faces.py --src "/path/folder" --recursive
"""

import os
import sys
import shutil
import argparse
from typing import List
from utils import validate_image_file


def find_images(path: str, recursive: bool) -> List[str]:
    if os.path.isfile(path):
        return [path] if validate_image_file(path) else []
    images: List[str] = []
    if recursive:
        for root, _, files in os.walk(path):
            for f in files:
                fp = os.path.join(root, f)
                if validate_image_file(fp):
                    images.append(fp)
    else:
        for f in os.listdir(path):
            fp = os.path.join(path, f)
            if os.path.isfile(fp) and validate_image_file(fp):
                images.append(fp)
    return images


def slugify_name(name: str) -> str:
    slug = name.strip().lower().replace(" ", "_").replace("-", "_")
    return "".join(ch for ch in slug if ch.isalnum() or ch == "_")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import images into known_faces")
    p.add_argument("--src", required=True, help="Source image file or folder")
    p.add_argument("--name", help="Override person name for all images")
    p.add_argument("--dest", default="known_faces", help="Destination folder (known_faces)")
    p.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    os.makedirs(args.dest, exist_ok=True)

    if not os.path.exists(args.src):
        print(f"Error: Source not found: {args.src}")
        return 1

    images = find_images(args.src, args.recursive)
    if not images:
        print("No valid images found.")
        return 2

    print(f"Found {len(images)} image(s). Importing → {args.dest}")
    imported = 0

    for idx, src_path in enumerate(images, 1):
        base = os.path.basename(src_path)
        name_root, ext = os.path.splitext(base)
        person = args.name if args.name else name_root
        person_slug = slugify_name(person)
        dest_name = f"{person_slug}_{idx:02d}{ext.lower()}"
        dest_path = os.path.join(args.dest, dest_name)

        try:
            shutil.copy2(src_path, dest_path)
            print(f"✓ {src_path} → {dest_path}")
            imported += 1
        except Exception as e:
            print(f"! Failed to copy {src_path}: {e}")

    print(f"Done. Imported {imported}/{len(images)}.")
    return 0 if imported else 3


if __name__ == "__main__":
    sys.exit(main())


