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
from ImageMetadataDef import ExposureMetadata

DEBUG = True
WARNING = True
ERROR = True



# TODO: fix 'stk' attribute and related functions
class RollMetadata:
    def __init__(self, directory, collection):
        self._collection = collection  # Collection object reference


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
        self.countAll = None                        # Total count of files in roll, derived
        self.countJpg = None                        # Count of jpg files, derived
        self.countRaw = None                        # Count of raw files, derived

        # Film stock attributes TODO
        self.stock = None                           # Film stock, derived
        self.stk = None                             # Film stock ID, cast from first exposure
        self.boxSpeed = None                        # ISO box value, derived


        # Roll attributes
        self.process = None                         # Film development process (C41, E6, BNW), derived...? [TODO]
        self.startDate = None                       # Roll start date, cast from first exposure
        self.endDate = None                         # Roll end date, cast from last exposure
        self.duration = None                        # Roll duration, derived
        self.index = None                           # Roll index, derived from folder name
        self.title = None                           # Title for the roll, derived from folder name
        self.containsCopies = None                  # Does roll contain images that are copies of a master? Derived from copy check
        self.cameras = None                         # List of cameras used in the roll, derived
        self.lenses = None                          # List of lenses used in the roll, derived
        self.exposures = None                       # List of addresses to exposures in the roll, derived
        self.format = None                          # Film format, derived from stock info

    # Main loop
    def process_roll(self):
        self.process_directory() # get data from folder names
        self.process_images() # fetch all images in the jpgDirs
        self.process_exif() # fetch exif data for all images
        self.sort_images() # sort images by exposure number (image.index)
        self.process_copies() # check for copies and nest them in the master copy object

        

    # 2) Identify filepaths & gather directory data
        # Search through all jpg files and get their filepaths.
    def process_directory(self):
        # Init
        dir = self.directory
        name = self.name

        # Grab index from name eg. "72_23-09-07 F3 P400 Flims and JPY" --> 72
        self.index = int(name.split("_")[0])

        # Identify jpg/raw dirs
        jpgDirs = []
        rawDirs = []
        if self.dir_contains(dir, 'jpg') or self.dir_contains(subDir, '.png'): jpgDirs.append(dir) # Check main directory for RAW files
        if self.dir_contains(dir, '.ARW'): rawDirs.append(dir) # Check main directory for JPG files
        
        # Search subdirs (only one tier)
        try:
            for subDir in os.path.listdir(dir):
                subDir = os.path.join(dir, subDir)
                if self.dir_contains(subDir, '.jpg') or self.dir_contains(subDir, '.png'): jpgDirs.append(subDir)
                if self.dir_contains(subDir, '.ARW'): rawDirs.append(subDir)
        except Exception:
            if DEBUG:
                print(f'[{self.index}]\tDEBUG: No subdirs to search through in:\n\t\t{dir}')

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
                print(f'[{self.index}]\tDEBUG: No JPG directories found for roll:\n\t\t{self.name}')
            return

        for dir_path in self.jpgDirs:
            dir_name = os.path.basename(dir_path).lower()

            # Skip directories with '5mb' or '5mp' in the name
            if '5mb' in dir_name or '5mp' in dir_name:
                if DEBUG:
                    print(f'[{self.index}]\tDEBUG: Skipping directory with "5mb"/"5mp" in name:\n\t\t{dir_path}')
                continue

            # Warn if directory name does not include 'jpg' or 'jpeg'
            if 'jpg' not in dir_name and 'jpeg' not in dir_name:
                if WARNING:
                    print(f'[{self.index}]\tWARNING: Folder name might not indicate valid JPG content:\n\t\t{dir_path}')
                continue

            # Process valid image files
            for file in os.listdir(dir_path):
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    file_path = os.path.join(dir_path, file)
                    image = ExposureMetadata(self, file_path)
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
                print(f'[{self.index}]\tDEBUG: No image obj to process EXIF data for roll:\n\t\t{self.name}')
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
            exif = self.fetch_exif(pathsToFetch)[0]

            # cast to back to image
            if exif is not None:
                image.set_exif(exif)
            return

        # Else, handle all files in buffer
        else:
            # Build path fetch list
            for image in self.images:
                if image.exif: 
                    pathsToFetch.append(None) # add empty placeholder to pathlist if already been processed
                else:
                    pathsToFetch.append(image.path)
            
            # Fetch exifs.
            data = self.fetch_exif(pathsToFetch)

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
                        print(f'[{self.index}] [{image.index}]\ERROR: Img path does not match exif source path:\n\t\tImage: {path}\n\t\tExif: {p}')
                    continue
                
                # cast exif to image
                image.set_exif(exif)

    # 5) Order images by exposure number
    def sort_images(self):
        indices = [img.index for img in self.images]
        if len(indices) != len(set(indices)):
            if WARNING:
                print(f"[{self.index}]\tWARNING: Duplicate exposure indices found in roll '{self.name}'")

        # Sort images by index
        self.images.sort(key=lambda img: img.index)

    # 6) Handle copies
        # Check through images to see if any have identical image.dateExposed.
        # If yes, build a list of each group of duplicate objects: list[0] == master copy. Sort by image.dateCreated. Oldest is the master.
        # Handle copies by nesting them in the master copy object.
    def process_copies(self):
        copies_dict = {}
        for img in self.images:
            key = img.dateExposed

            # Build dict of copies if date key matches
            if key not in copies_dict:
                copies_dict[key] = []
            copies_dict[key].append(img)

        self.containsCopies = False
        for group in copies_dict.values():
            if len(group) > 1:
                self.containsCopies = True
                # Sort by dateCreated, oldest is master
                group.sort(key=lambda x: x.dateCreated)

                # Define master obj
                master = group[0]
                master.isOriginal = True
                master.isCopy = False

                # Nest copies into the obj as a vector of objs
                master.copies = group[1:]

                # Update copy attributes
                for copy in master.copies:
                    copy.isOriginal = False
                    copy.isCopy = True
                    copy.index = master.index
            else:
                master = group[0]
                
                # Handle master copy attributes
                master.isOriginal = True
                master.isCopy = False
        
        if self.containsCopies:
            self.sort_images(self) # re sort images
            


    # =============== Helper Methods ============== #

    # Checks if a path contains a string. returns true/false.
    def dir_contains(self, dir, key):
        try:
            # Iterate through files in directory. Return true if key found, return false if no matches in dir.
            for file in os.listdir(dir):
                if file.lower().endswith(key.lower()):
                    return True
            if WARNING:
                print(f'[{self.index}]\tWARNING: did not find key in directory:\n\t\t"{key}" in {dir}') # NOTE: potentially spammy
            return False
        except Exception:
            if ERROR:
                print(f'[{self.index}]\tERROR: dir invalid:\n\t\t{dir}')
            return False
        
    # Returns requested exposure object
    def get_image(self, index):
        return self.images[index]
    
    # Returns object of a copy version of the indexed image TODO
    def get_image_copy(self, index, copyIndex):
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
                print(f'[{self.index}]\tERROR: Failed to open exiftool!\n')
            return None