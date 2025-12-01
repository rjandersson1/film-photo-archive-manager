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

DEBUG = False
WARNING = False
ERROR = True


class rollObj:
    def __init__(self, directory, collection):
        self.collection = collection  # Collection object reference


        # File handling
        self.directory = directory                  # subfolder directory eg. \...\2022 - 135\2_22-06-12 Gold 200 Zurich
        self.name = os.path.basename(directory)     # eg. '2_22-06-12 Gold 200 Zurich'
        self.jpgDirs = None                         # sPath to folder with jpg files
        self.rawDirs = None                         # Path to folder with raw files
        self.images = None                          # List of ExposureMetadata objects, derived

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
        self.title = None                           # Title for the roll, derived from folder name
        self.containsCopies = None                  # Does roll contain images that are copies of a master? Derived from copy check
        self.cameras = []                         # List of cameras used in the roll, derived
        self.cam = None
        self.lenses = None                          # List of lenses used in the roll, derived
        self.exposures = None                       # List of addresses to exposures in the roll, derived
        self.filmtype = None                      # Film format, derived from stock info. eg 135, 120, 45, 810
        self.filmformat = None                      # Exposure format, eg 135, 6x7, 6x6, half frame, xpan

    # Main loop
    def process_roll(self):
        self.process_directory() # get data from folder names
        self.process_images() # fetch all images in the jpgDirs
        self.process_exif() # fetch exif data for all images
        self.sort_images() # sort images by exposure number (image.index)
        self.process_copies() # check for copies and nest them in the master copy object
        self.update_metadata() # update film emulsion info for roll and other metadata

        

    # 2) Identify filepaths & gather directory data
        # Search through all jpg files and get their filepaths.
    def process_directory(self):
        # Init
        dir = self.directory
        name = self.name

        # Grab index from name eg. "72_23-09-07 F3 P400 Flims and JPY" --> 72
        index = int(name.split("_")[0])
        self.index = index

        # Identify jpg/raw dirs
        jpgDirs = []
        rawDirs = []

        # Search main directory
        for file in os.listdir(dir):
            path = os.path.join(dir, file)
            # Skip if a file
            if os.path.isfile(path): continue

            # Check main directory for jpg or raw files
            for file in os.listdir(dir):
                if file.lower().endswith('.jpg') or file.lower().endswith('.png'):
                    jpgDirs.append(dir)
                    break
            for file in os.listdir(dir):
                if file.lower().endswith('.arw') or file.lower().endswith('.dng'):
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
                if WARNING and os.path.isdir(os.path.join(path,file)):
                    print(f'\n[{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} additional subfolders in image directory:\n\t\t"{file}" in {path}')

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
                    jpgDirs.append(path)
                    break
            for file in os.listdir(path):
                if file.lower().endswith('.arw') or file.lower().endswith('.dng'):
                    rawDirs.append(path)
                    break



        # Print warnings if no jpg/raw files found
        if jpgDirs == []:
            if ERROR:
                print(f'[{self.index}]\t{"\033[35m"}ERROR:{"\033[0m"} JPG missing')
        if rawDirs == []:
            if WARNING:
                print(f'[{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} RAW missing')
                rawDirs.append(-1)

        # Print warnings if multiple jpg/raw dirs identified
        if len(jpgDirs) > 1:
            if WARNING:
                print(f'[{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} {len(jpgDirs)} JPG dirs found!')            
        if len(rawDirs) > 1:
            if WARNING:
                print(f'[{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} {len(rawDirs)} RAW dirs found!')

        # Update attributes
        if len(jpgDirs): self.jpgDirs = jpgDirs 
        else: self.jpgDirs = None

        if len(rawDirs): self.rawDirs = rawDirs
        else: self.rawDirs = None

        return
    
    # 3) Process all image directories and generate ExposureMetadata objects
    # Only process files that are explicitly valid (e.g. skip '5mb' folders or misnamed files)
    def process_images(self):
        images = []
        
        if not self.jpgDirs:
            if DEBUG:
                print(f'[{self.index}]\t{"\033[33m"}DEBUG:{"\033[0m"} No JPG directories found for roll:\n\t\t{self.name}')
            return

        for dir_path in self.jpgDirs:
            dir_name = os.path.basename(dir_path).lower()

            # Skip directories with '5mb' or '5mp' in the name
            if '5mb' in dir_name or '5mp' in dir_name:
                if DEBUG:
                    print(f'[{self.index}]\t{"\033[33m"}DEBUG:{"\033[0m"} Skipping directory with "5mb"/"5mp" in name:\n\t\t{dir_path}')
                continue

            # Warn if directory name does not include 'jpg' or 'jpeg'
            if 'jpg' not in dir_name and 'jpeg' not in dir_name:
                if WARNING:
                    print(f'[{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} Folder name might not indicate valid JPG content:\n\t\t{dir_path}')
                continue

            # Process valid image files
            for file in os.listdir(dir_path):
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    file_path = os.path.join(dir_path, file)
                    image = exposureObj(self, file_path)
                    images.append(image)
        
        # Update image list attribute
        self.images = images

    # 4) Bulk process EXIF data for all images. Overflow to process a single exif if requested
        # exif process approach:
        # - build filepath list. check each file if exif already processed.
        # - then fetch exif data. returns a data vector, with each data[i] being the correspnding exif data that needs to be passed back to the image obj
        # - cast each exif to the correct object (image.exif = data[i])
        # - call image.update_from_exif() to update image attributes
    def process_exif(self, image=None):
        if not self.images:
            if DEBUG:
                print(f'[{self.index}]\t{"\033[33m"}DEBUG:{"\033[0m"} No image obj to process EXIF data for roll:\n\t\t{self.name}')
            return
        
        pathsToFetch = []

        # If a single image obj was passed, process it
        if image is not None or len(self.images) == 1:
            if image is None:
                image = self.images[0]
            if image.exif:
                return # skip if processed
            
            path = image.filePath
            
            # Grab exif
            pathsToFetch.append(path)
            if DEBUG:
                print(f'[{self.index}]\t{"\033[33m"}DEBUG:{"\033[0m"} Fetching EXIF...')
            exif = self.fetch_exif(pathsToFetch)[0]

            # cast to back to image
            if exif is not None:
                if DEBUG:
                    print(f'\t\t\t{"\033[32m"}SUCCESS{"\033[0m"}')
                image.set_exif(exif)
            else:
                if DEBUG:
                    print(f'\t\t\t{"\033[31m"}FAILED{"\033[0m"}')
            return

        # Else, handle all files in buffer
        else:
            # Build path fetch list
            for image in self.images:
                if image.exif: 
                    pathsToFetch.append(None) # add empty placeholder to pathlist if already been processed
                else:
                    pathsToFetch.append(image.filePath)
            
            # Fetch exifs.
            if DEBUG:
                print(f'[{self.index}]\t{"\033[33m"}DEBUG:{"\033[0m"} Fetching EXIF...')
            data = self.fetch_exif(pathsToFetch)
            # Print success
            if data is not None:
                if DEBUG:
                    print(f'\t\t\t{"\033[32m"}SUCCESS{"\033[0m"}')
            else:
                if DEBUG:
                    print(f'\t\t\t{"\033[31m"}FAILED{"\033[0m"}')
            # Cast data back to image. Assert paths must match!
            for i in range(len(pathsToFetch)):
                path = pathsToFetch[i]
                if not path: continue # skip if path empty; i.e. already been processed

                exif = data[i] # single exif data
                p = exif.get("SourceFile") # original filepath of exif
                image = self.images[i]

                # Assert path match
                if p != path:
                    if ERROR:
                        print(f'[{self.index}] [{image.index}]\\ERROR: Img path does not match exif source path:\n\t\tImage: {path}\n\t\tExif: {p}')
                    continue
                
                # cast exif to image
                image.set_exif(exif)

    # 5) Order images by exposure number
    def sort_images(self):
        indices = [img.index for img in self.images]
        if len(indices) != len(set(indices)):
            if WARNING:
                print((indices), len(set(indices)))
                print(f"[{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} Duplicate exposure indices found in roll '{self.name}'")

        # Sort images by index
        self.images.sort(key=lambda img: img.index)

    # 6) Handle copies
        # Check through images to see if any have identical image.dateExposed.
        # If yes, build a list of each group of duplicate objects: list[0] == master copy. Sort by image.dateCreated. Oldest is the master.
        # Handle copies by nesting them in the master copy object.
    def process_copies(self):
        copies_dict = {}
        copies_to_remove = []
        master_list = []
        for img in self.images:
            key = img.dateExposed

            # Build dict of copies if date key matches
            if key not in copies_dict:
                copies_dict[key] = []
            copies_dict[key].append(img)

        self.containsCopies = False
        for group in copies_dict.values():

            if len(group) > 1:
                if DEBUG:
                    print(f'[{group[0].roll.index}]\t{"\033[33m"}DEBUG:{"\033[0m"} copy found between:')
                    for image in group:
                        print(f'\t\t[{image.index}] {image.dateExposed}: {image.name}')

                if group[0].roll.index == 12:
                    print(f'\n[{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} hardcode workaround --> skipping copy check on roll 12...')
                    for image in group:
                        master = image
                        
                        # Handle master copy attributes
                        master.isOriginal = True
                        master.isCopy = False
                        master.containsCopies = False
                        master.copyCount = 0
                        master.original = master
                    continue

                if group[0].roll.index == 6:
                    print(f'\n[{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} hardcode workaround --> skipping copy check on roll 6...')
                    for image in group:
                        master = image
                        
                        # Handle master copy attributes
                        master.isOriginal = True
                        master.isCopy = False
                        master.containsCopies = False
                        master.copyCount = 0
                        master.original = master
                    continue


                self.containsCopies = True

                # Prefer non-stitched / non-grayscale, then newest dateCreated
                master = max(
                    group,
                    key=lambda x: (
                        0 if (x.isStitched or x.isGrayscale) else 1,  # base (1) > derived (0)
                        x.dateCreated
                    )
                )

                copies = [img for img in group if img is not master]


                oldest_index = min(img.index for img in group)
                master.index = oldest_index


                master.isOriginal = True
                master.containsCopies = True
                master.isCopy = False

                master.copies = copies
                master.copyCount = len(copies)

                for copy in master.copies:
                    copy.isOriginal = False
                    copy.containsCopies = False
                    copy.isCopy = True
                    copy.index = master.index
                    copy.original = master

                # Handle removal of copies from main list and index offset
                for copy in master.copies:
                    copies_to_remove.append(copy)
                    master_list.append((master.index, len(master.copies)))
            else:
                master = group[0]
                
                # Handle master copy attributes
                master.isOriginal = True
                master.isCopy = False
                master.containsCopies = False
                master.copyCount = 0
                master.original = master
        
        if not self.containsCopies:
            return
        
        # Handle removal of copies and reindexing
        copies_set = set(copies_to_remove)
        self.images = [img for img in self.images if img not in copies_set]
        master_list.sort(key=lambda x: x[0])  # Sort by index

        # Reindex images based on the index offset

        for img in self.images:
            if img.containsCopies: # subtract the number of copies from the index for all subsequent images
                idx = img.index
                n = len(img.copies)
                for image in self.images[idx:]:
                    image.index -= n

                # Re index copies
                for copy in img.copies:
                    copy.index = img.index


        self.sort_images() # re sort images

    # 7) Update final film-specific metadata
    def update_metadata(self):
        self.update_filmformat()
        self.update_stock_metadata()

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
            print(f'\n[{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} stk not in stocklist:\n\t\t"{key}" in {self.collection.stocklist.keys()}')


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
                print(f'[{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} multiple cameras found in roll: {self.cameras}')

            
            


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


        
        # Check to confirm dateExposed increases with index
        # date_increasing = True
        for i in range(1, len(self.images)):
            if self.images[i].dateExposed < self.images[i-1].dateExposed:
                # date_increasing = False
                if WARNING:
                    print(f'[{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} dateExposed not increasing with index between exposures {self.images[i-1].index} and {self.images[i].index}')
                break


    def update_filmformat(self):
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

        if WARNING and not camfound:
            print(f'\n[{self.index}]\t\033[31mWARNING:\033[0m '
                f'cam not in cameralist:\n\t\t"brand:{cameraBrand} model:{cameraModel}"')

        # Push attributes to all images
        for image in self.images:
            image.filmtype = self.filmtype
            image.filmformat = self.filmformat
            for copy in image.copies:
                copy.filmtype = self.filmtype
                copy.filmformat = self.filmformat











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
                print(f'\n[{self.index}]\t{"\033[31m"}WARNING:{"\033[0m"} did not find key in directory:\n\t\t"{key}" in {dir}') # NOTE: potentially spammy
            return False
        except Exception:
            if ERROR:
                print(f'[{self.index}]\t{"\033[35m"}ERROR:{"\033[0m"}: dir invalid:\n\t\t{dir}')
            return False
        
    # Returns requested exposure object
    def getImage(self, index):
        return self.images[index - 1]
    
    # Returns object of a copy version of the indexed image TODO
    def getImageCopy(self, index, copyIndex):
        # original = self.get_image(index)
        # copy = original.get_copy(copyIndex)
        return

    # generate exiftool command and run it. returns list of data[i] with each item being exif data for that path
    def fetch_exif(self, pathList):
        if shutil.which("exiftool"): # Attempt to open terminal
            # build command
            cmd = ["exiftool", "-j"]
            cmd += ["-a", "-u", "-g1"]
            cmd += pathList

            # build result
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )

            # save data
            data = json.loads(result.stdout or "[]")
            return data if data else None
        else:
            if ERROR:
                print(f'[{self.index}]\t{"\033[35m"}ERROR:{"\033[0m"}: Failed to open exiftool!\n')
            return None