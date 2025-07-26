#!/usr/bin/env python3
# exif_grabber.py

import argparse
import json
import shutil
import subprocess
from pathlib import Path

def grab_metadata(path: str) -> str:
    """
    Return all available metadata for `path` as a pretty-printed JSON string.
    Uses exiftool if available; falls back to Pillow EXIF (limited).
    """
    if shutil.which("exiftool"):
        # exiftool gives EXIF + IPTC + XMP (incl. keywords, LR info)
        result = subprocess.run(
            ["exiftool", "-j", "-a", "-u", "-g1", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        data = json.loads(result.stdout or "[]")
        return json.dumps(data[0] if data else {}, indent=2, ensure_ascii=False)

    # Fallback: Pillow (EXIF only, no XMP/keywords)
    try:
        from PIL import Image, ExifTags
        with Image.open(path) as im:
            exif = im._getexif() or {}
        tagmap = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
        return json.dumps(tagmap, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Could not read metadata: {e}"}, indent=2)

def main():
    path = Path('/Users/rja/Documents/Coding/film-photo-archive-manager/data/filmCollectionTest/2023/74_23-09-09 F3 FP4 JPY/jpg/23-09-17 - 18 - Tokyo - FP4 - F 35-105mm - 4s.jpg')

    meta_str = grab_metadata(path)
    print(meta_str)

if __name__ == "__main__":
    main()