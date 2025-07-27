import numpy as np
import pandas as pd
import sys
import os
from PIL import Image
from PIL.ExifTags import TAGS
import re
import glob
from datetime import datetime
from collections import OrderedDict
from pathlib import Path
import json
import shutil
import subprocess
from typing import Iterable, Union


class ExposureMetadata:
    def __init__(self, roll, path):
        self.roll = roll                     # roll object reference
        self.filePath = path
        self.fileName = os.path.basename(path)
        self.name = self.fileName.split(".jpg")[0]
        self.fileType = self.fileName.split(".")[-1]
        self.fileSize = os.path.getsize(self.filePath)
        
        # Exposure attributes
        self.exposureIndex = None           # Exposure index, from filename (dependant on duplicates... TODO)
        self.location = None                # Location, EXIF
        self.state = None                   # State, EXIF
        self.country = None                 # Country, EXIF
        self.stk = None                     # Stock ID, EXIF
        self.stock = None                   # Stock name, from ??? TODO
        self.rating = None                  # Rating, EXIF
        self.fNumber = None                 # F-number, EXIF  
        self.shutterSpeed = None            # Shutter speed, EXIF (string, e.g. '1/125', '1/60', '1/30', etc.)
        self.iso = None                     # ISO, EXIF
        self.exposureTime = None            # Exposure time, derived (float value of self.shutterspeed)
        self.exposureValue = None           # EV, derived

        # Datetime attributes
        self.dateExposed = None            # Exposure time, EXIF
        self.dateCreated = None            # Creation time, EXIF
        
        # Camera & lens
        self.camera = None                  # Camera, Derived
        self.cameraBrand = None             # Camera brand, EXIF
        self.cameraModel = None             # Camera model, EXIF
        self.lensBrand = None               # Lens brand, EXIF
        self.lensModel = None               # Lens model, EXIF
        self.lens = None                    # Lens, Derived
        self.focalLength = None             # Focal length, EXIF

        # Image data
        self.width = None                   # Image width, EXIF
        self.height = None                  # Image height, EXIF
        self.mpx = None                     # Megapixels, derived               
        self.aspectRatio = None             # Aspect ratio, derived
        self.isVertical = None              # Is vertical, derived
        self.isSquare = None                # Is square, derived
        self.isHorizontal = None            # Is horizontal, derived
        self.isPano = None                  # Is panorama, derived        
        
        # Film attributes
        self.isExpired = None               # Is film expired, cast
        self.isColor = None                 # Is color film, cast
        self.isBlackAndWhite = None         # Is black and white film, cast
        self.isInfrared = None              # Is infrared film, cast
        self.isNegative = None              # Is negative film, cast
        self.isSlide = None                 # Is slide film, cast
        self.boxSpeed = None                # Box speed, cast
        self.filmFormat = None              # Film format, cast


        # Duplicate Attributes
        self.isOriginal = None              # Is original, cast
        self.isDuplicate = None             # Is duplicate, cast
        self.isGrayscale = None             # Is grayscale, EXIF
        self.isStitched = None              # Is stitched, EXIF

        # Full EXIF / metadata JSON
        self.exif = None
        self.metadata = None # TODO: dont know if I need this
    
    # Grab exif. return exif json TODO
    def grab_exif(self):
        return
    
    # Grab metadata. return metadata json TODO
    def grab_metadata(self):
        return
    
    # Extract metadata from filename
    def process_fileName(self):
        name = self.name

        # Case 1: 22-10-02 Ektar 100 Seebach 1.jpg
        if ' - ' not in name:
            n = name.split(' ') # [22-10-02, Ektar, 100, Seebach, 1]
            try:
                self.exposure = int(n[-1])
            except Exception:
                self.exposure = None
            self.location = n[-2] if len(n) >= 2 else None
            self.stock = ' '.join(n[1:-2]) if len(n) >= 2 else None
            self.rating = None # no rating available

        # Case 2: 22-07-28 - 1 - Flims - Superia 400 -  - 5s.jpg
        elif ' - ' in name and '#' not in name:
            n = name.split(' - ')  # [22-07-28, 1, Flims, Superia 400, , 5s]
            try:
                self.exposure = int(n[1])
            except Exception:
                self.exposure = None
            self.location = n[2] if len(n) > 2 else None
            self.stock = n[3] if len(n) > 3 else None
            last = n[-1] if n else ''
            self.rating = last.split('s')[0] if 's' in last else None
    

        # Case 3: 23-01-01 - Zurich - Ektar 100 - F3 - 3s - #2.jpg
        elif ' - ' in name and '#' in name:
            n = name.split(' - ')  # [23-01-01, Zurich, Ektar 100, F3, 3s, #2]
            try:
                self.exposure = int(n[-1].split('#')[-1])
            except Exception:
                self.exposure = None
            self.location = n[1] if len(n) > 1 else None
            self.stock = n[2] if len(n) > 2 else None
            rating_field = n[-2] if len(n) > 1 else ''
            self.rating = rating_field.split('s')[0] if 's' in rating_field else None

        else:
            print(f"[{self.roll.index}]\tError: Skipping unrecognized file name format:\n\t\t{self.fileName}")
            self.exposure = None
            self.location = "error"
            self.stock = "error"
            self.rating = None


    # Updates image metadata from EXIF.
    def update_from_exif(self):
        if self.exif is None:
            print(f"[{self.roll.index}] [{self.exposureIndex}]\tError: No EXIF data available for:\n\t\t{self.fileName}.")
            return
        
        exif = self.exif
        
        # Exposure attributes
        self.location = exif.get('City')
        self.state = exif.get('Province-State')
        self.country = exif.get('Country-PrimaryLocationName')
        self.stk = exif.get('SceneType')
        self.rating = int(exif['Rating']) if exif.get('Rating') else None
        self.fNumber = float(exif['FNumber']) if exif.get('FNumber') else None
        self.shutterSpeed = str(exif.get('ShutterSpeedValue')) if exif.get('ShutterSpeedValue') else None
        self.exposureTime = self._convertShutterspeed(self.shutterSpeed)
        self.iso = int(exif['ISO']) if exif.get('ISO') else None

        # Datetime attributes
        date = exif.get('DateTimeOriginal', None)  
        self.dateExposed = self._convertDateTime(date)
        date = exif.get('CreateDate', None)
        self.dateCreated = self._convertDateTime(date)

        # Camera & lens
        self.cameraBrand = exif.get('Make')
        self.cameraModel = exif.get('Model')
        self.camera = f"{self.cameraBrand} {self.cameraModel}" if self.cameraBrand and self.cameraModel else None
        self.lensBrand = exif.get('LensMake')
        self.lensModel = exif.get('LensModel')
        self.lens = f"{self.lensBrand} {self.lensModel}" if self.lensBrand and self.lensModel else None
        self.focalLength = float(exif.get('FocalLength').split(' ')[0]) if exif.get('FocalLength') else None
        
        # Image data
        self.width = int(exif.get('ExifImageWidth', 0)) if exif.get('ExifImageWidth') else None
        self.height = int(exif.get('ExifImageHeight', 0)) if exif.get('ExifImageHeight') else None

        # Duplicate Attributes
        self.isGrayscale = bool(exif.get('ConvertToGrayscale', None)) if exif.get('ConvertToGrayscale') else None
        self.isStitched = bool(exif.get('IsMergedPanorama', None)) if exif.get('IsMergedPanorama') else None

        # Update derived attributes
        self._update_derived_attributes()

        # Update cast attributes
        self._update_cast_attributes()


    def _update_derived_attributes(self):
        # Exposure attributes
        if self.exposureTime and self.iso and self.fNumber:
            self.exposureValue = np.log2((self.fNumber ** 2) / self.iso * (1 / self.exposureTime))
        else:
            self.exposureValue = None

        # Image data
        if self.width and self.height:
            self.mpx = (self.width * self.height) / 1_000_000
            self.aspectRatio = self.width / self.height
            self.isVertical = self.aspectRatio < 1
            self.isSquare = (self.aspectRatio > 0.9 and self.aspectRatio < 1.1) # between 0.9 and 1.1
            self.isHorizontal = self.aspectRatio > 1
            self.isPano = self.aspectRatio > 1.85
    
    # TODO: requests info from roll object to cast attributes to exposure object.
    def _update_cast_attributes(self):
        # Film attributes TODO
        if self.stk:
            stock_info = self.roll.get_stock_info(self.stk)
            if stock_info:
                self.isExpired = stock_info.get('isExpired', False)
                self.isColor = stock_info.get('isColor', False)
                self.isBlackAndWhite = stock_info.get('isBlackAndWhite', False)
                self.isInfrared = stock_info.get('isInfrared', False)
                self.isNegative = stock_info.get('isNegative', False)
                self.isSlide = stock_info.get('isSlide', False)
                self.boxSpeed = stock_info.get('boxSpeed')
                self.filmFormat = stock_info.get('filmFormat')



    # Converts 'YYYY:MM:DD HH:MM:SS' or 'YYYY:MM:DD' + 'HH:MM:SS' into datetime object.
    def _convertDateTime(self, date_str=None, time_str=None):
        if not date_str:
            return None

        # If time_str is provided, join them explicitly
        if time_str:
            candidate = f"{date_str} {time_str}".strip()
            fmts = ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S")
        else:
            candidate = date_str.strip()
            fmts = (
                "%Y:%m:%d %H:%M:%S",
                "%Y:%m:%d",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            )

        for fmt in fmts:
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                pass
        return None
    
    def _convertShutterspeed(self, shutterspeed):

        # Convert shutter speeds to (float) seconds.
        # Parse the following formats:
            # '1/125', '1/60', '1/30'
            # 1s, 2s, 3s, etc.
            # 1, 2, 3, etc.
            # 6h10m, '6h 10m', '6h10m30s', '6h 10m 30s'
        if not shutterspeed:
            return None
        if isinstance(shutterspeed, str):
            shutterspeed = shutterspeed.strip().lower()
            if 'h' in shutterspeed or 'm' in shutterspeed or 's' in shutterspeed:
                # Handle hours, minutes, seconds
                match = re.match(r'(?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?', shutterspeed)
                if match:
                    hours, minutes, seconds = match.groups()
                    total_seconds = (int(hours) * 3600 if hours else 0) + \
                                    (int(minutes) * 60 if minutes else 0) + \
                                    (int(seconds) if seconds else 0)
                    return total_seconds
            elif '/' in shutterspeed:
                # Handle fractions like '1/125'
                num, denom = map(int, shutterspeed.split('/'))
                return num / denom
            else:
                # Handle whole numbers like '1', '2', etc.
                return float(shutterspeed)
            
        # throw error if could not match any of the formats
        raise ValueError(f"[{self.rollIndex}] [{self.exposureIndex}]\tCould not convert shutter speed:\n\t\t{shutterspeed}")
    
    