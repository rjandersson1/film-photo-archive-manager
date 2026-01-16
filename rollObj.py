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
from exposureObj import exposureObj
from collections import Counter
from debuggerTool import debuggerTool
from time import time

DEBUG = 1
WARNING = True
ERROR = True

db = debuggerTool(DEBUG, WARNING, ERROR) 


class rollObj:
    def __init__(self, directory, collection):
        self.collection = collection  # Collection object reference

        # File handling
        self.directory = directory                  # subfolder directory eg. \...\2022 - 135\2_22-06-12 Gold 200 Zurich
        self.name = os.path.basename(directory)     # eg. '2_22-06-12 Gold 200 Zurich'
        self.jpgDirs = None                         # sPath to folder with jpg files
        self.rawDirs = None                         # Path to folder with raw files
        self.rawMissing = None                      # Flag for whether raw files could be found
        self.images = None                          # List of ExposureMetadata objects, derived
        self.images_all = []                        # List of all ExposureMetadata objects including copies, derived
        self.unmatched_raws = None                 # List of unmatched raw files after verification, derived
        self.isNewCollection = False                  # if searching using new collection formatting

        # File data TODO
        self.sizeAll = None                         # Total size of roll, derived
        self.sizeJpg = None                         # Size of jpg files, derived
        self.sizeRaw = None                         # Size of raw files, derived
        self.sizeExposures = None                  # Size of all exposures, derived
        self.sizeCopies = None                    # Size of all copies, derived
        self.countAll = None                        # Total count of files in roll, derived
        self.countJpg = None                        # Count of jpg files, derived
        self.countRaw = None                        # Count of raw files, derived
        self.countExposures = None                  # Count of exposures, derived
        self.countCopies = None                     # Count of copies, derived

        # Film stock attributes
        self.manufacturer = None
        self.stock = None
        self.boxspeed = None
        self.stk = None
        self.process = None
        self.isColor = None
        self.isBlackAndWhite = None
        self.isInfrared = None
        self.isNegative = None
        self.isSlide = None

        # Roll attributes
        self.process = None                         # Film development process (C41, E6, BNW), cast from stock info
        self.startDate = None                       # Roll start date, cast from first exposure
        self.endDate = None                         # Roll end date, cast from last exposure
        self.duration = None                        # Roll duration, derived
        self.index = None                           # Roll index, derived from folder name
        self.index_str = None                       # Roll index string, zfill(3) eg 003
        self.dbIdx = None                           # Debug roll index string, eg [083]
        self.title = None                           # Title for the roll, derived from folder name
        self.containsCopies = None                  # Does roll contain images that are copies of a master? Derived from copy check
        self.cameras = []                         # List of cameras used in the roll, derived
        self.cam = None
        self.lenses = None                          # List of lenses used in the roll, derived
        self.exposures = None                       # List of addresses to exposures in the roll, derived
        self.filmtype = None                      # Film format, derived from stock info. eg 135, 120, 45, 810
        self.filmformat = None                      # Exposure format, eg 135, 6x7, 6x6, half frame, xpan

    # Runs preprocessing until exif is required
    def preprocess_roll(self):
        self.process_directory() # get data from folder names
        self.process_images() # fetch all images in the jpgDirs

    # Main loop: pass batch exif processing to roll level to improve runtime.
    def process_roll(self):
        if self.images is None or len(self.images) == 0:
            self.images = []
            return
        self.process_exif()
        self.update_metadata() # update film emulsion info for roll and other metadata
        self.process_copies() # check for copies and nest them in the master copy object
        self.verify_roll()

    # 2) Identify filepaths & gather directory data
        # Search through all jpg files and get their filepaths.
    def process_directory(self):
        # Init
        dir = self.directory
        name = self.name

        # Grab index from name eg. "72_23-09-07 F3 P400 Flims and JPY" --> 72
        index = int(name.split("_")[0])
        self.index = index
        self.index_str = str(self.index).zfill(3)
        self.dbIdx = f'[{self.index_str}]'


        self.find_image_dirs()


        # Print warnings if no jpg/raw files found
        jpgDirs = self.jpgDirs
        rawDirs = self.rawDirs
        if jpgDirs == []:
            if rawDirs == []:
                db.e(self.dbIdx, 'RAW+JPG missing!')
            else:
                db.e(self.dbIdx, 'JPG missing, but RAW exists!')
            self.images = []
            return
        elif rawDirs == []:
            db.w(self.dbIdx, 'RAW missing, but JPG exists!')
            self.rawMissing = True
            rawDirs.append(-1)

        # Print warnings if multiple jpg/raw dirs identified
        if len(jpgDirs) > 1 and not self.isNewCollection:
            db.w(f'[{self.index_str}]',f'{len(jpgDirs)} JPG dirs found!')
        if len(rawDirs) > 1 and not self.isNewCollection:
            db.w(f'[{self.index_str}]',f'{len(rawDirs)} RAW dirs found!', rawDirs)

        # Update attributes
        if len(jpgDirs): self.jpgDirs = jpgDirs 
        else: self.jpgDirs = None

        if len(rawDirs): self.rawDirs = rawDirs
        else: self.rawDirs = None

        if self.jpgDirs is None:
            self.images = []
        return


    def find_image_dirs(self):
        # search new structure
        dir = self.directory
        new_rawDir = os.path.join(dir, '01_scans')
        new_jpgDir = os.path.join(dir, '02_exports')
        new_copyDir = os.path.join(dir, '04_edits')
        new_rawDir_backups = os.path.join(dir, '05_other','01_unmatched_raws')
        if not os.path.isdir(new_jpgDir): # return if identified as old legacy folder structure
            self.find_image_dirs_legacy()
            return
        
        # Identify jpg/raw dirs
        jpgDirs = []
        rawDirs = []
        
        self.isNewCollection = True
        jpgDirs.append(new_jpgDir)

        # Check in 01_scans
        if os.path.isdir(new_rawDir):
            contains_files = 0
            for file in os.listdir(new_rawDir):
                if file.lower().endswith('.arw') or file.lower().endswith('.dng') or file.lower().endswith('.tif') or file.lower().endswith('.tiff'):
                    contains_files = 1
            if contains_files:
                self.rawMissing = False
                rawDirs.append(new_rawDir)
        
        # Check in 05_other/01_unmatched_raws
        if os.path.isdir(new_rawDir_backups):
            contains_files = 0
            for file in os.listdir(new_rawDir_backups):
                if file.lower().endswith('.arw') or file.lower().endswith('.dng') or file.lower().endswith('.tif') or file.lower().endswith('.tiff'):
                    contains_files = 1
            if contains_files:
                self.rawMissing = False
                rawDirs.append(new_rawDir_backups)

        # Check copies
        if os.path.isdir(new_copyDir):
            jpgDirs.append(new_copyDir)

        self.jpgDirs = jpgDirs
        self.rawDirs = rawDirs
        return
    
    def find_image_dirs_legacy(self):
        jpgDirs = []
        rawDirs = []
        dir = self.directory
        # Search main directory
        for file in os.listdir(dir):
            path = os.path.join(dir, file)
            # Skip if a file
            if os.path.isfile(path): continue

            # Check main directory for jpg or raw files
            for file in os.listdir(dir):
                if file.lower().endswith('.jpg') or file.lower().endswith('.png'):
                    if dir not in jpgDirs:
                        jpgDirs.append(dir)
                    break
            for file in os.listdir(dir):
                if file.lower().endswith('.arw') or file.lower().endswith('.dng') or file.lower().endswith('.tif') or file.lower().endswith('.tiff'):
                    if dir not in rawDirs:
                        rawDirs.append(dir)
                    break
        
        # Search subdirs (only one tier)
        for file in os.listdir(dir):
            path = os.path.join(dir, file)
            # Skip if a file
            if os.path.isfile(path): continue

            # search through subdirs
            for file in os.listdir(path):
                # Warn if contains subsubdirs
                conditions_ignore = (
                    file == "Scene" or
                    file == "Camera"
                )
                if conditions_ignore: continue
                if os.path.isdir(os.path.join(path,file)):
                    db.w(self.dbIdx, 'Additional subfolder found in image directory!', f'"{file}" in {path}')

                conditions = (
                    file.lower().endswith('.jpg') or
                    file.lower().endswith('.png')
                )
                conditions_ignore = (
                    file == "Scene" or
                    file == "Camera"
                )
                # print("[",index,'] ', conditions, conditions_ignore)
                if conditions:
                    if conditions_ignore:
                        continue
                    if path not in jpgDirs:
                        jpgDirs.append(path)
                    break
            for file in os.listdir(path):
                if file.lower().endswith('.arw') or file.lower().endswith('.dng') or file.lower().endswith('.tif') or file.lower().endswith('.tiff'):
                    if path not in rawDirs:
                        rawDirs.append(path)
                    break

        self.jpgDirs = jpgDirs
        self.rawDirs = rawDirs

    # 3) Process all image directories and generate ExposureMetadata objects
    # Only process files that are explicitly valid (e.g. skip '5mb' folders or misnamed files)
    def process_images(self):
        images = []
        
        if not self.jpgDirs:
            return

        if not self.isNewCollection:
            filtered_jpgDirs = []
            for dir_path in self.jpgDirs:
                dir_name = os.path.basename(dir_path).lower()

                # Skip directories with '5mb' or '5mp' in the name
                if '5mb' in dir_name or '5mp' in dir_name:
                    db.d(self.dbIdx, 'Skipping 5mb/5mp jpg folder')
                    continue

                # Warn if directory name does not include 'jpg' or 'jpeg'
                if 'jpg' not in dir_name and 'jpeg' not in dir_name and 'new' not in dir_name:
                    if WARNING:
                        print(f'[{self.index_str}]\t{"\033[31m"}WARNING:{"\033[0m"} Folder name might not indicate valid JPG content:\n\t\t{dir_path}')
                    continue
                filtered_jpgDirs.append(dir_path)
            self.jpgDirs = filtered_jpgDirs

        # Process valid image files
        for dir_path in self.jpgDirs:
            for file in os.listdir(dir_path):
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    file_path = os.path.join(dir_path, file)
                    image = exposureObj(self, file_path)
                    images.append(image)

        
        # Update image list attribute
        self.images = images
        self.reindex_images()

    # 4) Bulk process EXIF data for all images. Overflow to process a single exif if requested
        # exif process approach:
        # - build filepath list. check each file if exif already processed.
        # - then fetch exif data. returns a data vector, with each data[i] being the correspnding exif data that needs to be passed back to the image obj
        # - cast each exif to the correct object (image.exif = data[i])
        # - call image.update_from_exif() to update image attributes
    def process_exif(self, image=None):
        # If a single image obj was passed, process it
        if image is not None or len(self.images) == 1:
            if image.exif:
                return # skip if processed
            path = list(image.filePath)
            db.d(f'[{self.index_str}]','Fetching EXIF...')
            data = self.fetch_exif(path)
            exif = data[0]
            if exif is not None:
                image.set_exif(exif)
            else:
                db.e(f'[{self.index_str}]', 'EXIF FETCH FAILED')
            return

        # Else, handle all files in buffer
        else:
            pathsToFetch = {}

            for img in self.images:
                if not img.exif:
                    pathsToFetch[img.filePath] = img

            # Batch fetch exif
            pathList = list(pathsToFetch.keys())
            # db.d(self.dbIdx, f'Fetching EXIF...')
            t1 = time()
            data = self.fetch_exif(pathList)
            t2 = time()
            dt = t2 - t1
            db.d(self.dbIdx, f'Fetched in EXIF {dt:.2f}s', f'{dt/len(pathList)*1000:.0f}ms per img')

            if data is None:
                db.e(self.dbIdx, 'Failed to fetch exif!')
            
            # Cast exif back to objects
            for exif in data:
                exif_path = exif.get("SourceFile")

                if exif_path not in pathsToFetch:
                    db.e(self.dbIdx, "Exif path does not match any image in batch!", f'{exif_path}')
                    continue

                img = pathsToFetch[exif_path]

                # hard assert
                if exif_path != img.filePath:
                    db.e(self.dbIdx, "Exif path does not match any image in batch!", f'Image:\t{img.filePath}\nExif:\t{exif_path}')
                    continue

                # pass exif to image
                img.set_exif(exif)

    # generate exiftool command and run it. returns list of data[i] with each item being exif data for that path
    def fetch_exif(self, pathList):
        if not shutil.which("exiftool"):
            db.e(self.dbIdx, 'Failed to open exiftool!')
            return None

        if not pathList:
            return []

        tags = [
            "-SourceFile",
            "-XMP-xmpMM:PreservedFileName",
            "-IPTC:City",
            "-IPTC:Province-State",
            "-IPTC:Country-PrimaryLocationName",
            "-XMP-iptcCore:Scene",
            "-XMP-xmp:Rating",
            "-ExifIFD:ISO",
            "-ExifIFD:FNumber",
            "-ExifIFD:ShutterSpeedValue",
            "-ExifIFD:DateTimeOriginal",
            "-ExifIFD:CreateDate",
            "-IFD0:Make",
            "-IFD0:Model",
            "-ExifIFD:LensMake",
            "-ExifIFD:LensModel",
            "-ExifIFD:FocalLength",
            "-File:ImageWidth",
            "-File:ImageHeight",
            "-XMP-crs:ConvertToGrayscale",
            "-XMP-aux:IsMergedPanorama",
        ]

        cmd = ["exiftool", "-j", "-g1", "-stay_open"]
        cmd += ["-fast2"]
        cmd += tags
        cmd += pathList
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )

        data = json.loads(result.stdout or "[]")
        return data if data else None


    # 5) Order images by exposure number
    def sort_images(self):
        if self.images is None:
            return
        indices = [img.index for img in self.images]
        if len(indices) != len(set(indices)):
            if ERROR:
                # print out duplicate indices
                index_counts = Counter(indices)
                duplicates = {idx: count for idx, count in index_counts.items() if count > 1}
                
                db.e(f"[{self.index_str}]", 'Duplicate exposure indices found in roll: ', [duplicates])
                if DEBUG:
                    for img in self.images:
                        if img.index in duplicates:
                            print(f"\t\t[{img.index_str}] {img.name}")

        # Sort images by index
        self.images.sort(key=lambda img: img.index)
        self.reindex_images()
        self.build_images_all()

    # 6) Handle copies
        # Check through images to see if any have identical image.dateExposed.
        # If yes, build a list of each group of duplicate objects: list[0] == master copy. Sort by image.dateCreated. Oldest is the master.
        # Handle copies by nesting them in the master copy object.
        # TODO: fix bug where stock attributes are derived after process_copies, but used in process copies. Need to refactor and rework updateFilmMetadata to occur beforehand, and then certain things like copy-relevant stuff needs to occur after the copies are processed.
    def process_copies(self):
        # Hardcode skip for rolls 6 and 12
        if self.index in (6,12,68):
            db.w(f'[{self.index_str}]', 'Skipping copy check on roll (hardcode workaround)', self.index_str)
            self.containsCopies = False
            for img in self.images:
                img.isOriginal = True
                img.isCopy = False
                img.containsCopies = False
                img.copyCount = 0
                img.copies = []
                img.original = img
            self.verify_raw_files()
            self.sort_images()
            return

        # -------- Step 0: initialize and reset attributes --------
        self.containsCopies = False

        # Helper fn to rank master based on if stitched/greyscale
        def master_rank(x):
            # 1) grayscale penalty only applies for color images (and not B&W)
            grayscale_penalty = 0
            if not x.isBlackAndWhite:
                if x.isColor and x.isGrayscale:
                    grayscale_penalty = 1  # worse
                else:
                    grayscale_penalty = 0  # better

            # 2) pano penalty
            pano_penalty = 1 if x.isPano else 0

            # 3) prefer more detail
            mp = x.mpx or 0
            fs = x.fileSize or 0

            # 4) oldest created wins
            created_ts = x.dateCreated.timestamp() if x.dateCreated else float("inf")

            # lower tuple is better -> use min(...)
            ranking = (
                grayscale_penalty,
                pano_penalty,
                -mp,
                -fs,
                created_ts,
                x.fileName or "",
            )
            return ranking
        

        for img in self.images:
            # keep existing img.copies if you want, but safest is to rebuild
            img.copies = []
            img.isOriginal = True
            img.isCopy = False
            img.containsCopies = False
            img.copyCount = 0
            img.original = img

        # -------- Step 1: group by dateExposed --------
        groups = {}
        for img in self.images:
            key = img.dateExposed
            groups.setdefault(key, []).append(img)
        
        # -------- Step 2: Identify master and pass copies --------
        masters = []
        for dt, group in groups.items():
            
            # Unique dateExpose --> master
            if len(group) == 1:
                master = group[0]
                masters.append(master)
                continue

            self.containsCopies = True

            # master: best rank -> derived=1 beats derived=0, then newest dateCreated wins
            master = min(group, key=master_rank)
            copies = [x for x in group if x is not master]

            master.copies = copies
            master.isOriginal = True
            master.isCopy = False
            master.containsCopies = True
            master.copyCount = len(copies)
            master.original = master

            for c in copies:
                c.isOriginal = False
                c.isCopy = True
                c.containsCopies = False
                c.copyCount = 0
                c.original = master

            masters.append(master)

        # -------- Step 3: Sort by exposure time and reindex --------
        masters.sort(key=lambda x: x.dateExposed)

        for new_idx, master in enumerate(masters, start=1):
            master.index = new_idx
            master.index_str = str(new_idx).zfill(2)

            for copy in master.copies:
                copy.index = new_idx
                copy.index_str = str(new_idx).zfill(2)

        # -------- Step 4: Pass back to roll --------
        self.images = masters

        # -------- Step 5: Verify and sort --------
        self.verify_raw_files()
        self.sort_images()
        for img in self.images:
            for copy in img.copies:
                copy.update_copy_type()

    # 7) Update final film-specific metadata
    def update_metadata(self):
        self.update_filmformat()
        self.update_stock_metadata()
        self.update_file_metadata()
        self.update_locations()

    # Update stock-related attributes using first image STK to identify stock among collection stock list.
    def update_stock_metadata(self):
        # Grab film stock from first frame and cast it to all exposures
        img = self.images[0]
        key = img.stk
        stkFound = False

        # Identify stock in stock list using first image STK
        for stock in self.collection.stocklist.values():
            if stock['KEY_ID'] == key:
                self.manufacturer = stock['manufacturer']
                self.stock = stock['stock']
                self.boxspeed = stock['boxspeed']
                self.stk = stock['stk']
                self.process = stock['process']
                self.isColor = stock['isColor']
                self.isBlackAndWhite = stock['isBlackAndWhite']
                self.isInfrared = stock['isInfrared']
                self.isNegative = stock['isNegative']
                self.isSlide = stock['isSlide']
                self.fontPath = stock['font'] # 'fonts/Impact Label Reversed.ttf'
                self.fontColor = tuple(map(int, stock['color'].split(','))) # '252, 194, 180, 255' --> tuple(rgba)
                stkFound = True
        if WARNING and not stkFound:
            print(f'\n[{self.index_str}]\t{"\033[31m"}WARNING:{"\033[0m"} stk not in stocklist:\n\t\t"{key}"')

        # Cast metadata back to all images (if no STK found, casts None and throws warning)
        for image in self.images:
            image.stock = self.stock
            image.boxspeed = self.boxspeed
            image.stk = self.stk
            image.cam = self.cam
            image.process = self.process
            image.isColor = self.isColor
            image.isBlackAndWhite = self.isBlackAndWhite
            image.isInfrared = self.isInfrared
            image.isNegative = self.isNegative
            image.isSlide = self.isSlide
            if image.cam not in self.cameras:
                self.cameras.append(image.cam)
            
            # handle copies
            for copy in image.copies:
                copy.stock = self.stock
                copy.boxspeed = self.boxspeed
                copy.stk = self.stk
                copy.cam = self.cam
                copy.process = self.process
                copy.isColor = self.isColor
                copy.isBlackAndWhite = self.isBlackAndWhite
                copy.isInfrared = self.isInfrared
                copy.isNegative = self.isNegative
                copy.isSlide = self.isSlide
                if copy.cam not in self.cameras:
                    self.cameras.append(copy.cam)
            
        if len(self.cameras) > 1:
            # print warning saying multiple cameras for one roll
            if WARNING:
                print(f'[{self.index_str}]\t{"\033[31m"}WARNING:{"\033[0m"} multiple cameras found in roll: {self.cameras}')


    def update_file_metadata(self):
        # Cast date attributes
        self.startDate = self.images[0].dateExposed
        self.endDate = self.images[-1].dateExposed
        self.duration = (self.endDate - self.startDate).days + 1
        
        # Cast file data attributes
        self.sizeAll = shutil.disk_usage(self.directory).used
        self.sizeJpg = 0
        self.countJpg = 0
        if self.jpgDirs:
            for dir in self.jpgDirs:
                for file in os.listdir(dir):
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        file_path = os.path.join(dir, file)
                        self.sizeJpg += os.path.getsize(file_path)
                        self.countJpg += 1
        self.sizeRaw = 0
        self.countRaw = 0
        if self.rawDirs and self.rawDirs[0] != -1:
            for dir in self.rawDirs:
                for file in os.listdir(dir):
                    if file.lower().endswith(('.arw', '.dng')):
                        file_path = os.path.join(dir, file)
                        self.sizeRaw += os.path.getsize(file_path)
                        self.countRaw += 1
        
        self.sizeExposures = 0
        self.sizeCopies = 0 
        self.countAll = 0
        self.countExposures = 0
        self.countCopies = 0
        for img in self.images:
            if img.isOriginal:
                self.sizeExposures += img.fileSize
                self.countExposures += 1
                self.countAll = self.countAll + 1
            if img.isCopy:
                self.sizeCopies += img.fileSize
                self.countCopies += 1
                self.countAll = self.countAll + 1

    def update_filmformat(self):
        if len(self.images) == 0:
            db.e(self.dbIdx,'No images found!')
            return
        # Pick first camera (assumes all images on roll are from same camera)
        cameraBrand = self.images[0].cameraBrand
        cameraModel = self.images[0].cameraModel

        self.filmtype = None
        self.filmformat = None
        camfound = False

        if cameraBrand and cameraModel:
            # Normalize (case-insensitive, strip spaces)
            brand = str(cameraBrand).strip().lower()
            model = str(cameraModel).strip().lower()

            # EDGE CASE
            if "skye" in model:
                model = model.split(" - ")[0]

            for cam in self.collection.cameralist.values():
                cbrand = (cam.get("brand") or "").strip().lower()
                cmodel = (cam.get("model") or "").strip().lower()

                if brand == cbrand and model == cmodel:
                    self.filmtype = cam.get("filmtype")
                    self.filmformat = cam.get("filmformat")
                    self.cam = cam.get("id")
                    camfound = True
                    break

        if not camfound:
            db.e(self.dbIdx, f'Cam not in cameralist:', f'({cameraBrand},{cameraModel})')

        # Push attributes to all images
        for image in self.images:
            image.filmtype = self.filmtype
            image.filmformat = self.filmformat
            for copy in image.copies:
                copy.filmtype = self.filmtype
                copy.filmformat = self.filmformat

    # filter images by rating
    def filter_by_rating(self, stars, logic, include_copies=False):
        selected = []

        for img in self.images:
            if logic == '>=' and img.rating >= stars:
                selected.append(img)
                if include_copies:
                    selected.extend(img.copies)
            elif logic == '<=' and img.rating <= stars:
                selected.append(img)
                if include_copies:
                    selected.extend(img.copies)
            elif logic == '==' and img.rating == stars:
                selected.append(img)
                if include_copies:
                    selected.extend(img.copies)

        return selected

    def reindex_images(self):
        for img in self.images:
            for copy in img.copies:
                copy.index_str = str(copy.index).zfill(2)
            img.index_str = str(img.index).zfill(2)

    def build_images_all(self):
        self.images_all = []
        for img in self.images:
            self.images_all.append(img)
            for copy in img.copies:
                self.images_all.append(copy)
        # Sort images_all by index
        self.images_all.sort(key=lambda img: (img.index))






# for img in self.images:
#     key = img.dateExposed

#     # Build dict of copies if date key matches
#     if key not in copies_dict:
#         copies_dict[key] = []
#     copies_dict[key].append(img)

# self.containsCopies = False
# for group in copies_dict.values():
#     if len(group) > 1:






    # =============== Helper Methods ============== #

    # Checks if a path contains a string. returns true/false.
    def dir_contains(self, dir, key):
        try:
            # Iterate through files in directory. Return true if key found, return false if no matches in dir.
            for file in os.listdir(dir):
                if file.lower().endswith(key.lower()):
                    return True
            if WARNING:
                print(f'\n[{self.index_str}]\t{"\033[31m"}WARNING:{"\033[0m"} did not find key in directory:\n\t\t"{key}" in {dir}') # NOTE: potentially spammy
            return False
        except Exception:
            if ERROR:
                print(f'[{self.index_str}]\t{"\033[35m"}ERROR:{"\033[0m"}: dir invalid:\n\t\t{dir}')
            return False
        
    # Returns requested exposure object
    def getImage(self, index):
        return self.images[index - 1]
    
    # Returns object of a copy version of the indexed image TODO
    def getImageCopy(self, index, copyIndex):
        # original = self.get_image(index)
        # copy = original.get_copy(copyIndex)
        return

    # run through locations on roll and choose 1-2 major ones to assign to roll
    def update_locations(self):
        # Prorities:
            # choose most common locations (2 max)

        location_counts = {}
        for img in self.images:
            location = img.location
            if location:
                if location in location_counts:
                    location_counts[location] += 1
                else:
                    location_counts[location] = 1
        
        if not location_counts:
            self.locations = []
            return
        
        # Sort locations by count
        sorted_locations = sorted(location_counts.items(), key=lambda x: x[1], reverse=True)
        top_locations = [loc[0] for loc in sorted_locations[:2]]
        self.locations = top_locations
        return


    def check_for_dupe_raw(self):
        for rawDir in self.rawDirs:
            if rawDir == -1:
                continue
            raw_files = os.listdir(rawDir)
            raw_names = [os.path.splitext(f)[0].split('-')[0] for f in raw_files]
            raw_name_counts = Counter(raw_names)
            for name, count in raw_name_counts.items():
                if count > 1:
                    db.e(f'[{self.index_str}]', f'Multiple RAW files under {name}')

    # check all img and copies match to a raw file, flag any that are duplicates or missing
    def verify_raw_files(self):
        if self.rawMissing:
            return
        # Build set of raw filenames (without extensions)
        raw_filenames = set()
        if self.rawDirs and self.rawDirs[0] != -1:
            for rawDir in self.rawDirs:
                for file in os.listdir(rawDir):
                    if file.lower().endswith(('.arw', '.dng', '.tif', '.tiff')):
                        raw_filenames.add(file)

        # Walk through all images and copies and ensure raw file exists. If exists, remove from set. Print remaining unmatched raws at end.
        unmatched_raws = raw_filenames.copy()

        for img in self.images:
            imgRawName = img.rawFileName
            if imgRawName in unmatched_raws:
                unmatched_raws.discard(imgRawName)
            else:
                db.w(f'[{self.index_str}][{img.index_str}]', f'No matching RAW file for image:', imgRawName)

            for copy in img.copies:
                copy_rawName = copy.rawFileName
                if copy_rawName in unmatched_raws:
                    unmatched_raws.discard(copy_rawName)
                else:
                    if copy.isPano and copy.isStitched:

                        # find corresponding pano raw file: eg match DSC01694.ARW <--> DSC01694-pano.dng
                        base_name = os.path.splitext(copy_rawName)[0]+'-Pano'
                        pano_raw_candidates = [f for f in raw_filenames if f.startswith(base_name) and '-Pano' in os.path.splitext(f)[0]]
                        new_raw_name = 'N/A'
                        if pano_raw_candidates:
                            new_raw_name = pano_raw_candidates[0]
                            copy.rawFileName = new_raw_name
                            copy.rawFilePath = copy.rawFilePath.replace(copy_rawName, new_raw_name)
                            unmatched_raws.discard(new_raw_name)
                            db.d(f'[{self.index_str}][{img.index_str}]', f'Adjusted panorama RAW filename:', [f'{copy.name} --> {copy_rawName} --> {new_raw_name}', copy.rawFilePath])
                        else:
                            db.e(f'[{self.index_str}][{img.index_str}]', f'No matching RAW file for panorama:', f'{copy.name} --> {copy_rawName} ({copy.original.mpx:.0f},{copy.mpx:.0f})MP at ({copy.original.aspectRatio:.2f},{copy.aspectRatio:.2f}):1 --> copy.isStitched={copy.isStitched}')

                    

        if len(unmatched_raws) > 0:
            unmatched_files = list(unmatched_raws)
            # build paths to unmatched raws
            self.unmatched_raws = []
            for rawDir in self.rawDirs:
                for rawFile in unmatched_files:
                    rawPath = os.path.join(rawDir, rawFile)
                    if os.path.exists(rawPath):
                        self.unmatched_raws.append(rawPath)

            db.w(f'[{self.index_str}]', f'Unmatched RAW files remaining:', self.unmatched_raws)

    # Verify attributes on roll and print a summary
    def verify_roll(self):
        # Check to confirm dateExposed increases with index
        # date_increasing = True
        for i in range(1, len(self.images)):
            if self.images[i].dateExposed < self.images[i-1].dateExposed:
                db.w(f'[{self.index_str}]', 'dateExposed not increasing with index between exposures', f'[{self.images[i-1].index}] {self.images[i-1].dateExposed.time()} > {self.images[i].dateExposed.time()} [{self.images[i].index}]')
                break
        for img in self.images:
            img.verify()
            for copy in img.copies:
                copy.verify()

        camera_error = 0
        camera_error_idx = []
        for img in self.images:
            if img.cameraBrand in [None, 'SONY'] or img.cameraModel in [None, 'DSLR-A550']:
                camera_error = 1
                camera_error_idx.append(img.index)
            for copy in img.copies:
                if copy.cameraBrand in [None, 'SONY'] or copy.cameraModel in [None, 'DSLR-A550']:
                    camera_error = 1
                    camera_error_idx.append(copy.index)
        if camera_error:
            db.e(self.dbIdx, 'Camera attribute cast error!')
        
