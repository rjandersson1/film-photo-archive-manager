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

DEBUG = True
ERROR = True
WARNING = True

class exposureObj:
    def __init__(self, roll, path):
        self.roll = roll                     # roll object reference
        
        # File attributes
        self.filePath = path
        self.fileName = os.path.basename(path)
        self.name = self.fileName.split(".jpg")[0]
        self.fileType = self.fileName.split(".")[-1]
        self.fileSize = os.path.getsize(self.filePath)
        self.rawFileName = None     # Raw file name, EXIF
        self.rawFilePath = None       # Raw file path, derived TODO: grab from self.roll.rawPaths and search for matching filenames
        self.attributesFile = {}

        # Exposure attributes
        self.index = None           # Exposure index, from filename (dependant on duplicates... TODO)
        self.index_original = None
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
        self.attributesExposure = {}

        # Datetime attributes
        self.dateExposed = None            # Exposure time, EXIF
        self.dateCreated = None            # Creation time, EXIF

        # Camera & lens
        self.camera = None                  # Camera, Derived
        self.cameraBrand = None             # Camera brand, EXIF
        self.cameraModel = None             # Camera model, EXIF
        self.cam = None                     # Camera ID, Cast
        self.lensBrand = None               # Lens brand, EXIF
        self.lensModel = None               # Lens model, EXIF
        self.lens = None                    # Lens, Derived
        self.lns = None                     # Lens ID, Cast
        self.focalLength = None             # Focal length, EXIF
        self.attributesCamera = {}

        # Image data
        self.width = None                   # Image width, EXIF
        self.height = None                  # Image height, EXIF
        self.mpx = None                     # Megapixels, derived               
        self.aspectRatio = None             # Aspect ratio, derived
        self.isVertical = None              # Is vertical, derived
        self.isSquare = None                # Is square, derived
        self.isHorizontal = None            # Is horizontal, derived
        self.isPano = None                  # Is panorama, derived       
        self.attributesImage = {} 
        
        # Film attributes
        self.isExpired = None               # Is film expired, cast
        self.isColor = None                 # Is color film, cast
        self.isBlackAndWhite = None         # Is black and white film, cast
        self.isInfrared = None              # Is infrared film, cast
        self.isNegative = None              # Is negative film, cast
        self.isSlide = None                 # Is slide film, cast
        self.boxspeed = None                # Box speed, cast
        self.filmtype = None                # Film type, cast (135, 120, 45, 810)
        self.filmformat = None              # Film format, cast (35mm, half frame, 6x7, 6x6 etc)
        self.attributesFilm = {}

        # Duplicate Attributes
        self.original = None                # Master exposure obj (none if master), derived
        self.copies = []                  # Vector of copy objs, derived
        self.isOriginal = None              # Is original, cast
        self.copyCount = None
        self.containsCopies = None          # Does this exposure contain copies, derived
        self.isCopy = None                  # Is duplicate, cast
        self.isGrayscale = None             # Is grayscale, EXIF
        self.isStitched = None              # Is stitched, EXIF
        self.attributesCopies = {}


        # Full EXIF / metadata JSON
        self.exif = None
        self.attributes = {}

        # Methods
        self.process_fileName()  # Process filename to extract exposure index

    
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
                self.index= int(n[-1])
            except Exception:
                if ERROR: print(f'[{self.roll.index}]\t{"\033[35m"}ERROR:{"\033[0m"} [1] Could not get exposure index from:\n\t\t{name}')
                self.index= None

        # Case 2: 22-07-28 - 1 - Flims - Superia 400 -  - 5s.jpg
        elif ' - ' in name and '#' not in name:
            n = name.split(' - ')  # [22-07-28, 1, Flims, Superia 400, , 5s]
            try:
                self.index= int(n[1])
            except Exception:
                if ERROR: print(f'[{self.roll.index}]\t{"\033[35m"}ERROR:{"\033[0m"} [2] Could not get exposure index from:\n\t\t{name}')
                self.index= None
    

        # Case 3: 23-01-01 - Zurich - Ektar 100 - F3 - 3s - #2.jpg
        elif ' - ' in name and '#' in name:
            n = name.split(' - ')  # [23-01-01, Zurich, Ektar 100, F3, 3s, #2]
            try:
                self.index= int(n[-1].split('#')[-1])
            except Exception:
                if ERROR: print(f'[{self.roll.index}]\t{"\033[35m"}ERROR:{"\033[0m"} [3] Could not get exposure index from:\n\t\t{name}')
                self.index= None

        else:
            if ERROR: print(f'[{self.roll.index}]\t{"\033[35m"}ERROR:{"\033[0m"} [E] Could not get exposure index from:\n\t\t{name}')
            self.index= None

        self.index_original = self.index  # Store original index for later use

    # Set exif data to image
    def set_exif(self, exif):
        self.exif = exif
        self._update_from_exif()


    # =========== Private methods ================== #

    # Updates image attributes from EXIF.
    def _update_from_exif(self):
        if not self.exif:
            if ERROR:
                print(f"[{self.roll.index}] [{self.index}] ERROR: No EXIF data available for {self.fileName}")
            return

        # File attributes
        self.rawFileName = self._get_exif(("XMP-xmpMM", "PreservedFileName"))
        if self.roll.index == 12:
            print(f'\n[{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} hardcode workaround --> renaming exif-filename from .ARW to .dng to match raw files')
            self.rawFileName = self.rawFileName.split(".")[0]+".dng"


        if self.roll.rawDirs and self.rawFileName:
            rawDir = self.roll.rawDirs[0]
            rawName = self.rawFileName.split('.')[0] 
            if rawName == -1 or rawDir == -1:
                self.rawFilePath = None
            else:
                rawPath = os.path.join(rawDir, (rawName+".ARW"))
                if os.path.isfile(rawPath):
                    self.rawFilePath = rawPath
                rawPath = os.path.join(rawDir, (str(rawName)+".dng"))
                if os.path.isfile(rawPath):
                    self.rawFilePath = rawPath
                else:
                    if WARNING:
                        # print(f"\n[{self.roll.index}][{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} No rawDirs or rawFileName available to set rawFilePath for \n\t\t{self.fileName} <-> {self.rawFileName} in {rawPath}")
                        a=1

        # Exposure attributes
        self.location   = self._get_exif(("IPTC", "City"))
        self.country    = self._get_exif(("IPTC", "Country-PrimaryLocationName"))
        self.stk        = self._get_exif(("XMP-iptcCore", "Scene"))
        self.rating     = self._get_exif(("XMP-xmp", "Rating"), conv=int)
        if self.rating is None:
            self.rating = 0
        self.iso        = self._get_exif(("ExifIFD", "ISO"), conv=int)
        self.state      = self._get_exif(("IPTC", "Province-State"))
        self.fNumber    = self._get_exif(("ExifIFD", "FNumber"), conv=float)

        shutter_str     = self._get_exif(("ExifIFD", "ShutterSpeedValue"))
        if shutter_str:
            self.shutterSpeed = str(shutter_str)
            self.exposureTime = self._convertShutterspeed(self.shutterSpeed)
        else:
            self.shutterSpeed = None

        # Datetime
        self.dateExposed = self._convertDateTime(
            self._get_exif(("ExifIFD", "DateTimeOriginal"))
        )
        self.dateCreated = self._convertDateTime(
            self._get_exif(("ExifIFD", "CreateDate"))
        )

        # Camera & lens
        self.cameraBrand = self._get_exif(("IFD0", "Make"))
        self.cameraModel = self._get_exif(("IFD0", "Model"))
        self.camera      = f"{self.cameraBrand} {self.cameraModel}" if self.cameraBrand and self.cameraModel else None

        self.lensBrand   = self._get_exif(("ExifIFD", "LensMake"))
        self.lensModel   = self._get_exif(("ExifIFD", "LensModel"))
        self.lens        = f"{self.lensBrand}f{self.lensModel}" if self.lensBrand and self.lensModel else ''
        self.maxAperture = self.lensModel.split('/')[-1].split(' ')[0] if self.lensModel and '/' in self.lensModel else ''

        # todo: improve lens ID casting to handle zoom (35-105) etc. --> grab from lensModel.
        self.focalLength = self._get_exif(("ExifIFD", "FocalLength"),
                                        conv=lambda v: float(v.split(" ")[0]) if v else None)
        self.lns         = str(int(self.focalLength)) + 'f' + self.maxAperture if self.focalLength and self.maxAperture else ''

        # Image data
        self.width  = self._get_exif(("File", "ImageWidth"), conv=int)
        self.height = self._get_exif(("File", "ImageHeight"), conv=int)

        # Duplicate attributes
        self.isGrayscale = self._get_exif(("XMP-crs", "ConvertToGrayscale"),
                                        conv=lambda v: bool(int(v)) if str(v).isdigit() else bool(v),
                                        default=False)
        self.isStitched  = self._get_exif(("XMP-aux", "IsMergedPanorama"),
                                        conv=bool,
                                        default=False)
        

        # Hard code workaround for roll 29 (exif scene name issue)
        if self.stk == 'Gold 200 OM Accura':
            self.stk = 'Gold 200'

        # Update derived attributes
        self._update_derived_attributes()

    # Helper function to get nested EXIF values with optional conversion and default.
    def _get_exif(self, path, conv=None, default=None):
        d = self.exif
        try:
            for p in path:
                d = d[p]
            if d in (None, "", "NaN"):
                return default
            return conv(d) if conv else d
        except Exception:
            return default

    # Processes all derived attributes
    def _update_derived_attributes(self):
        # Exposure attributes
        if self.exposureTime and self.iso and self.fNumber:
            self.exposureValue = np.log2((self.fNumber ** 2) / self.iso * (1 / self.exposureTime))
        else:
            self.exposureValue =  'Unavailable'

        # Image data
        if self.width and self.height:
            self.mpx = (self.width * self.height) / 1_000_000
            self.aspectRatio = self.width / self.height
            self.isVertical = self.aspectRatio < 1
            self.isSquare = (self.aspectRatio > 0.9 and self.aspectRatio < 1.1) # between 0.9 and 1.1
            self.isHorizontal = self.aspectRatio > 1
            self.isPano = self.aspectRatio > 1.85

    # =========== Helper methods ================== #

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
        raise ValueError(f"[{self.roll.index}] [{self.index}]\tCould not convert shutter speed:\n\t\t{shutterspeed}")
    
    # prints all (filtered) attributes of an image as a table
    def getInfo(self, key=None):
        # setup
        if self.attributes == {}: self.buildInfo()
        tab = '\t\t'

        missingCount = 0
        for dict in self.attributes.values():
            for term in dict.keys():
                val = dict[term]
                if val == None:
                    missingCount += 1

        print(f'[{self.roll.index}][{self.index}] INFO: [{missingCount}] unassigned attributes ========================================================\n\n')

        # Find max key length for alignment
        max_len = 0
        for subdict in self.attributes.values():
            for term in subdict.keys():
                max_len = max(max_len, len(str(term)))

        if key == 'none':
            for dict in self.attributes.values():
                for term in dict.keys():
                    val = dict[term]
                    if val == None:
                        dots = '.' * (max_len - len(term) + 1)
                        print(f'{term}{dots}{val}')
        elif key == None:
            dict = self.attributes
            for subdict in dict.values():
                for term in subdict.keys():
                    val = subdict[term]
                    if val != None:
                        dots = '.' * (max_len - len(term) + 1)
                        print(f'{term}{dots}{val}')
        else:
            dict = self.attributes[key]
            for key in dict.keys():
                val = dict[key]
                dots = '.' * (max_len - len(key) + 1)
                print(f'{key}{dots}{val}')


    # Build attribute dictionary for image
    def buildInfo(self):
        # Build sub-dictionaries
        attributesFile = {}
        attributesExposure = {}
        attributesCamera = {}
        attributesImage = {}
        attributesFilm = {}
        attributesCopies = {}

        # File attributes
        attributesFile['filePath'] = self.filePath
        attributesFile['fileName'] = self.fileName
        attributesFile['name'] = self.name
        attributesFile['fileType'] = self.fileType
        attributesFile['fileSize'] = self.fileSize
        attributesFile['rawFileName'] = self.rawFileName
        attributesFile['rawFilePath'] = self.rawFilePath


        # Exposure attributes
        attributesExposure['index'] = self.index
        attributesExposure['index_original'] = self.index_original
        attributesExposure['dateExposed'] = self.dateExposed
        attributesExposure['dateCreated'] = self.dateCreated
        attributesExposure['location'] = self.location
        attributesExposure['state'] = self.state
        attributesExposure['country'] = self.country
        attributesExposure['stk'] = self.stk
        attributesExposure['stock'] = self.stock
        attributesExposure['rating'] = self.rating
        attributesExposure['fNumber'] = self.fNumber
        attributesExposure['shutterSpeed'] = self.shutterSpeed
        attributesExposure['iso'] = self.iso
        attributesExposure['exposureTime'] = self.exposureTime
        attributesExposure['exposureValue'] = self.exposureValue

        # Camera & lens
        attributesCamera['camera'] = self.camera
        attributesCamera['cameraBrand'] = self.cameraBrand
        attributesCamera['cameraModel'] = self.cameraModel
        attributesCamera['lensBrand'] = self.lensBrand
        attributesCamera['lensModel'] = self.lensModel
        attributesCamera['lens'] = self.lens
        attributesCamera['focalLength'] = self.focalLength

        # Image data
        attributesImage['width'] = self.width
        attributesImage['height'] = self.height
        attributesImage['mpx'] = self.mpx
        attributesImage['aspectRatio'] = self.aspectRatio
        attributesImage['isVertical'] = self.isVertical
        attributesImage['isSquare'] = self.isSquare
        attributesImage['isHorizontal'] = self.isHorizontal
        attributesImage['isPano'] = self.isPano

        # Film attributes
        attributesFilm['isExpired'] = self.isExpired
        attributesFilm['isColor'] = self.isColor
        attributesFilm['isBlackAndWhite'] = self.isBlackAndWhite
        attributesFilm['isInfrared'] = self.isInfrared
        attributesFilm['isNegative'] = self.isNegative
        attributesFilm['isSlide'] = self.isSlide
        attributesFilm['boxspeed'] = self.boxspeed
        attributesFilm['filmtype'] = self.filmtype
        attributesFilm['filmformat'] = self.filmformat

        # Duplicate Attributes
        attributesCopies['original'] = self.original
        attributesCopies['copies'] = self.copies
        attributesCopies['isOriginal'] = self.isOriginal
        attributesCopies['copyCount'] = self.copyCount
        attributesCopies['containsCopies'] = self.containsCopies
        attributesCopies['isCopy'] = self.isCopy
        attributesCopies['isGrayscale'] = self.isGrayscale
        attributesCopies['isStitched'] = self.isStitched


        # Build master dict
        attributes = {}
        attributes['file'] = attributesFile
        attributes['exposure'] = attributesExposure
        attributes['camera'] = attributesCamera
        attributes['image'] = attributesImage
        attributes['film'] = attributesFilm
        attributes['copies'] = attributesCopies

        # Cast back to obj
        self.attributesFile = attributesFile
        self.attributesExposure = attributesExposure
        self.attributesCamera = attributesCamera
        self.attributesImage = attributesImage
        self.attributesFilm = attributesFilm
        self.attributesCopies = attributesCopies
        self.attributes = attributes


    def count_unassigned_attr(self):
        self.buildInfo()
        count = 0
        for dict in self.attributes.values():
            for term in dict.values():
                if term == None:
                    count += 1
        return count





