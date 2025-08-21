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



# TODO: fix 'stk' attribute and related functions
class RollMetadata:
    def __init__(self, directory, collection):
        self._collection = collection  # Collection object reference


        # File handling
        self.directory = directory                  # subfolder directory eg. \...\2022 - 135\2_22-06-12 Gold 200 Zurich
        self.name = os.path.basename(directory)     # eg. '2_22-06-12 Gold 200 Zurich'
        self.jpgPath = None                         # Path to folder with jpg files
        self.rawPath = None                         # Path to folder with raw files

        # File data
        self.sizeAll = None                         # Total size of roll, derived
        self.sizeJpg = None                         # Size of jpg files, derived
        self.sizeRaw = None                         # Size of raw files, derived
        self.countAll = None                        # Total count of files in roll, derived
        self.countJpg = None                        # Count of jpg files, derived
        self.countRaw = None                        # Count of raw files, derived


        # Film stock attributes
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


        # Helper
        self._exif_cache = {} # Cache for EXIF data to avoid repeated reads



        # Initialize RollMetadata with a base directory and default metadata values
        self.camera = None  # Camera model used for the roll
        self._exif_cache = {}
        self.NEEDED_TAGS = ["IsMergedPanorama", "ConvertToGrayscale", "Megapixels", "ModifyDate"]

        #TODO: implement
        self.format = "Unknown"
        

        # Processes all files and builds metadata list
        self._process_files()
        if self.jpgPath is None:
            print(f"Warning: No JPG files found in {os.path.split(self.directory)[1]}")
            del self
            return

        self.image_data = self._process_image_metadata()

        # Check for virtual copies
        self._virtualCopy_identifier()




    def _process_directory(self):
        dir = self.directory
        name = self.name

        # Process directory name for attributes


    # 
    def _process_files(self):
        # Process file count and file size only if paths are defined
        self._get_index()
        self._get_title()
        self.jpgPath = self._get_path_jpg()
        self.rawPath = self._get_path_raw()

        if self.jpgPath:
            self.countJpg, self.sizeJpg = self._count_files(self.jpgPath, ['jpg', 'png'])
        else:
            # print(f"No JPEG or PNG files found in {self.directory}")
            self.jpgPath = None
            self.countJpg, self.sizeJpg = 0, 0
            return

        if self.rawPath:
            self.countRaw, self.sizeRaw = self._count_files(self.rawPath, ['arw', 'dng', 'tiff', 'tif'])
        else:
            # print(f"No RAW files found in {self.directory}")
            self.countRaw, self.sizeRaw = 0, 0

        # Set total count and size
        self.countAll = self.countJpg + self.countRaw
        self.size = self.sizeRaw + self.sizeJpg

        # Fill out metadata attributes only if jpgPath exists
        if self.jpgPath:
            self._get_metadata()

        self.stk = self._get_stk()

    # Main method to process metadata from the first jpg file
    def _get_metadata(self):
        jpg_files = [file for file in os.listdir(self.jpgPath) if file.lower().endswith(('.jpg'))]

        try:
            first_jpg_file = os.path.join(self.jpgPath, jpg_files[0])
            last_jpg_file = os.path.join(self.jpgPath, jpg_files[-1])

            # Process the start date
            with Image.open(first_jpg_file) as img:
                exif_data = img._getexif()
                if exif_data:
                    self._get_metadata_camera(exif_data)
                    self._get_metadata_stock(exif_data)
                    self._get_metadata_iso(exif_data)
                    start_date_str = self._get_metadata_date(exif_data)
                    if start_date_str:  # Ensure date string is not None
                        self.startDate = datetime.strptime(start_date_str, '%Y.%m.%d')
                    else:
                        print("Start date not found.")

            # Process the end date
            with Image.open(last_jpg_file) as img:
                exif_data = img._getexif()
                if exif_data:
                    end_date_str = self._get_metadata_date(exif_data)
                    if end_date_str:  # Ensure date string is not None
                        self.endDate = datetime.strptime(end_date_str, '%Y.%m.%d')
                    else:
                        print("End date not found.")

        except Exception as e:
            print(f"Error reading metadata from {first_jpg_file} or {last_jpg_file}: {e}")

        # Calculate the duration only if both dates are available and valid
        if isinstance(self.startDate, datetime) and isinstance(self.endDate, datetime):
            self.duration = (self.endDate - self.startDate).days + 1
        else:
            self.duration = None

    # Helper method to extract camera information
    def _get_metadata_camera(self, exif_data):
        try:
            description = exif_data.get(270, "Unknown")
            description_parts = description.split('\r\n')
            
            if description and description.startswith('SONY'):
                if len(description_parts) > 2:
                    if len(description_parts) > 5:
                        camera = description_parts[2].split('|')[0]
                    else:
                        description_parts = description_parts[2].split(',')
                        camera = description_parts[0]
                    self.camera = camera.strip() if camera else "Unknown"  # Remove trailing spaces
                else:
                    print("Camera metadata is incomplete.")
            elif description:
                self.camera = description.split(',')[0].strip()  # Remove trailing spaces
            elif not description_parts[0].startswith('SONY'):  # Hardcode fix
                length = len(description.split('\r\n'))
                if length == 7:  # still not working for roll 6
                    self.camera = description_parts[2].split('|')[0].strip()  # Remove trailing spaces
                if length == 3:
                    self.camera = description_parts[0].split(',')[0].strip()  # Remove trailing spaces
        except IndexError:
            print("Error extracting camera metadata: List index out of range.")
        except Exception as e:
            print(f"{self.index} Unexpected error in _get_metadata_camera: {e}")

    # Helper method to extract film stock information
    def _get_metadata_stock(self, exif_data):
        try:
            description = exif_data.get(270, "Unknown")
            description_parts = description.split('\r\n')
            if description:
                if description.startswith('SONY'):
                    if len(description_parts) > 2:
                        description_parts = description_parts[2].split('|')
                        stock = ' '.join(description_parts[-1].split(" ")[2:-1])
                        if '@' in stock:
                            stock = ' '.join(stock.split(' ')[0:-2])
                        self.stock = stock if stock else "Unknown"
                elif not description_parts[0].startswith('SONY'): # Hardcode fix
                    length = len(description.split('\r\n'))
                    if length == 7:
                        self.stock = ' '.join(description_parts[2].split('|')[2].split(' ')[1:-1])
                    if length == 3:
                        self.stock = ' '.join(description_parts[0].split(',')[-1].split(' ')[1:-1])
                else:
                    stock = ' '.join(description.split(',')[2].split()[1:-1])
                    self.stock = stock if stock else "Unknown"
        except IndexError:
            print("")
            # print("Error extracting stock metadata: List index out of range.")
        except Exception as e:
            print(f"{self.index} Unexpected error in _get_metadata_stock: {e}")

    # Helper method to extract ISO information
    def _get_metadata_iso(self, exif_data):
        try:
            description = exif_data.get(270, "Unknown")
            description_parts = description.split('\r\n')
            if description:
                if description.startswith('SONY'):
                    if len(description_parts) > 2:
                        description_parts = description_parts[2].split('|')
                        iso = description_parts[-1].split(" ")[-1]
                        self.iso = iso if iso else "Unknown"
                elif not description_parts[0].startswith('SONY'): # Hardcode fix
                    length = len(description.split('\r\n'))
                    if length == 7:
                        self.iso = description_parts[2].split('|')[2].split(' ')[-1]
                    if length == 3:
                        self.iso = description_parts[0].split(',')[-1].split(' ')[-1]
        except IndexError:
            print(f"{self.index}: Error extracting ISO metadata: List index out of range.")
        except Exception as e:
            print(f"{self.index} Unexpected error in _get_metadata_iso: {e}")

    # Helper method to extract date information
    def _get_metadata_date(self, exif_data):
        try:
            date_str = exif_data.get(36867)
            if date_str:
                # Format the date string as 'YYYY.MM.DD'
                date = '.'.join(date_str.split(" ")[0].split(':'))
                return date
            else:
                print(f"{self.index} No date found in EXIF metadata.")
                return None
        except Exception as e:
            print(f"{self.index} Unexpected error in _get_metadata_date: {e}")
            return None  # Return None if an error occurs

    def _get_title(self):
        # get title of roll
        folder_name = os.path.basename(self.directory)
        self.title = ' '.join(folder_name.split()[1:])
    
    def _get_index(self):
        folder_name = os.path.basename(self.directory)
        self.index = folder_name.split()[0].split('_')[0]
        
    # Prints info about roll
    def get_info(self): # TODO
        return

    def _get_dir(self):

        splitDirectory = os.path.split(self.directory)
        splitSplitDirectory = splitDirectory[0].split('\\')
        directory = os.path.join("...",splitSplitDirectory[-2], splitSplitDirectory[-1],splitDirectory[1])
        return directory
    
    def _get_stk(self):
        self._collection.update_stock_list()
        tempDict = self._collection.stock_list # TODO: I cant access dictionary keys in this, even though it is built correctly..? oh well
        # print(self._collection.stock_list)
        # print(tempDict['HP5 Plus 400'])
        # self.stk = list[self.stock]

    def get_stockList(self):
        print(self._collection.stock_list)

    # Returns path with jpg or png files
    def _get_path_jpg(self):
        jpg_paths = []
        path = self.directory

        if self._path_contains(path, 'jpg') or self._path_contains(path, 'png'):
            jpg_paths.append(path)

        if os.path.isdir(path):
            for folder in os.listdir(path):
                folder_path = os.path.join(path, folder)
                
                # If folder_path contains any .jpg add it to jpg_paths
                if self._path_contains(folder_path, 'jpg'):
                    jpg_paths.append(folder_path)
        
        # Check that jpg_paths is not empty before choosing paths
        if not jpg_paths:
            return None

        # Resolve path conflicts if more than one path is found
        while len(jpg_paths) > 1:
            path1, path2 = jpg_paths[:2]
            chosen_path = self._choose_path(path1, path2)
            if chosen_path == path1:
                jpg_paths.pop(1)  # Remove path2
            else:
                jpg_paths.pop(0)  # Remove path1

        return jpg_paths[0] if jpg_paths else None

    # Returns path with raw files
    def _get_path_raw(self):
        searchKeys = ['arw', 'tiff', 'dng']
        raw_paths = []
        path = self.directory

        for key in searchKeys:
            if self._path_contains(path, key):
                raw_paths.append(path)
            if os.path.isdir(path):
                for folder in os.listdir(path):
                    folder_path = os.path.join(path, folder)
                    if self._path_contains(folder_path, key):
                        raw_paths.append(folder_path)

        # Check that raw_paths is not empty before returning a path
        if not raw_paths:
            return None

        # Remove duplicates
        raw_paths = list(set(raw_paths))

        return raw_paths[0] if raw_paths else None

    # Checks if filepath contains files of filetype
    def _path_contains(self, path, filetype):
        # Check if the path is a directory; if not, return False
        if not os.path.isdir(path):
            return False
        
        # Define the file extension to look for (e.g., ".jpg")
        extension = '.' + filetype
        # Iterate through items in the directory to find any files with the specified extension
        for filename in os.listdir(path):
            if filename.lower().endswith(extension.lower()):
                return True  # Return True if a matching file is found
        return False  # Return False if no matching file is found
    
    # Chooses between two paths in case of a file conflict. Returns desired path
    def _choose_path(self, path1, path2):
        # Get the name of the directory where the conflict is found
        directory = os.path.split(os.path.dirname(path1))[1]

        # Extract the folder names for each conflicting path
        folder_name1 = os.path.split(path1)[1]
        folder_name2 = os.path.split(path2)[1]

        # Print message indicating the conflict and the folders in question
        # print(f"Folder conflict found in \{directory}:")

        # Select a sample file from each path to help in resolving the conflict
        file1 = os.listdir(path1)[0]
        file2 = os.listdir(path2)[0]

        # Compare the lengths of the filenames split by spaces to determine path preference
        length1 = len(file1.split(' '))
        length2 = len(file2.split(' '))
        
        # Choose the path based on filename length or prompt the user if unclear
        # Eg. for file1 "23-02-07 Ars Imago 320 Oerlikon 9.jpg" vs file2 "20230207_125245.jpg" it will choose file1
        if length1 != 1:
            if length2 != 1 and "final" not in folder_name1.lower() and "5mp" not in folder_name1.lower() and "5mb" not in folder_name1.lower():
                # If both have filenames with spaces, ask the user to choose
                print(f"Unsolvable conflict, choose correct path:")
                print(f"1: {os.path.split(path1)[0]}\n...\{os.path.split((os.path.split(path1)[0]))[1]}\{folder_name1}")
                print(f"2: {os.path.split(path2)[0]}\n...\{os.path.split((os.path.split(path2)[0]))[1]}\{folder_name2}\n")
                choice = input()
                if choice == '1': return path1
                if choice == '2': return path2
            elif "5mp" in folder_name1.lower() or "5mb" in folder_name1.lower():
                return path2
            else:
                return path1
        else:
            if length2 != 1:
                # If path1 has filenames without spaces, prefer path2
                # print(f"Conflict \{directory}: [{folder_name1}, {folder_name2}] --> {folder_name2}\n")
                return path2
            if length2 == 1:
                # If both have filenames without spaces, ask the user to choose
                print(f"Unsolvable conflict, choose correct path:")
                print(f"1: {os.path.split(path1)[0]}\n...\{os.path.split((os.path.split(path1)[0]))[1]}\{folder_name1}")
                print(f"2: {os.path.split(path2)[0]}\n...\{os.path.split((os.path.split(path2)[0]))[1]}\{folder_name2}\n")
                choice = input()
                if choice == '1': return path1
                if choice == '2': return path2

    # Counts files of extension in filepath, returns count and size (MB)
    def _count_files(self, filepath, extensions):
        files = [file for ext in extensions for file in glob.glob(os.path.join(filepath, f"*.{ext}"))]
        size = round(sum(os.path.getsize(file) for file in files)/(1024**2),0)
        return len(files), size

    # Prints a formatted size of roll, with inputs for 'jpg' or 'raw' if needed
    def get_size(self, extension=None):
        if extension is None:
            # Print size and count for both JPG and RAW, and the total
            print(f"JPG: {self._format_size(self.sizeJpg)} and {self.countJpg} files")
            print(f"RAW: {self._format_size(self.sizeRaw)} and {self.countRaw} files")
            print(f"Total: {self._format_size(self.size)} and {self.countAll} files")
        elif extension.lower() == "jpg":
            # Print size and count only for JPG
            print(f"JPG: {self._format_size(self.sizeJpg)} and {self.countJpg} files")
        elif extension.lower() == "raw":
            # Print size and count only for RAW
            print(f"RAW: {self._format_size(self.sizeRaw)} and {self.countRaw} files")

    def _format_size(self, size_mb):
        # Convert to GB if size is greater than 1 GB (1024 MB)
        if size_mb >= 1024:
            return f"{size_mb / 1024:.1f} GB"
        else:
            return f"{size_mb:.1f} MB"

    def _process_image_metadata(self):
        image_data = {}
        index = -1
        images_removed = 0

        for photo in os.listdir(self.jpgPath):
            if not photo.lower().endswith('.jpg'):
                continue  # Skip if not jpg

            photo_path = os.path.join(self.jpgPath, photo)
            fileSize = os.path.getsize(photo_path) / (1024**2)

            try:
                exif_data = Image.open(photo_path)._getexif()
            except Exception:
                exif_data = None

            # Gather date/time
            date_str = exif_data.get(36867) if exif_data else None  # DateTimeOriginal
            if date_str:
                # e.g. '2023:09:07 12:05:32' -> date '2023.09.07', time '12:05:32'
                parts = date_str.split(' ')
                date = '.'.join(parts[0].split(':')) if len(parts) > 0 else None
                time = parts[1] if len(parts) > 1 else None
            else:
                date, time = None, None

            # defaults in case parsing fails
            exposure = None
            location = None
            stock = None
            rating = None

            fileName = photo[:-4]  # strip ".jpg" TODO: what is this?

            # ---- filename parsing ----
            # Case 1: 22-10-02 Ektar 100 Seebach 1.jpg
            if ' - ' not in fileName:
                splitName = fileName.split(' ')  # [22-10-02, Ektar, 100, Seebach, 1]
                try:
                    exposure = int(splitName[-1])
                except Exception:
                    exposure = None
                location = splitName[-2] if len(splitName) >= 2 else None
                stock = ' '.join(splitName[1:-2]) if len(splitName) > 3 else None
                rating = None

            # Case 2: 22-07-28 - 1 - Flims - Superia 400 -  - 5s.jpg
            elif ' - ' in fileName and '#' not in fileName:
                splitName = fileName.split(' - ')  # [22-07-28, 1, Flims, Superia 400, , 5s]
                try:
                    exposure = int(splitName[1])
                except Exception:
                    exposure = None
                location = splitName[2] if len(splitName) > 2 else None
                stock = splitName[3] if len(splitName) > 3 else None
                last = splitName[-1] if splitName else ''
                rating = last.split('s')[0] if 's' in last else None

            # Case 3: 23-01-01 - Zurich - Ektar 100 - F3 - 3s - #2.jpg
            elif ' - ' in fileName and '#' in fileName:
                splitName = fileName.split(' - ')  # [23-01-01, Zurich, Ektar 100, F3, 3s, #2]
                try:
                    exposure = int(splitName[-1].split('#')[-1])
                except Exception:
                    exposure = None
                location = splitName[1] if len(splitName) > 1 else None
                stock = splitName[2] if len(splitName) > 2 else None
                rating_field = splitName[-2] if len(splitName) > 1 else ''
                rating = rating_field.split('s')[0] if 's' in rating_field else None

            else:
                print(f"Error: Unrecognized file name format for {photo}. Skipping this file.")
                exposure = None
                location = "error"
                stock = "error"
                rating = None

            index += 1

            cameraBrand   = exif_data.get(271)    if exif_data else None
            cameraModel   = exif_data.get(272)    if exif_data else None
            iso           = exif_data.get(34855)  if exif_data else None
            focalLength   = exif_data.get(37386)  if exif_data else None
            lensBrand     = exif_data.get(42035)  if exif_data else None
            lensModel     = exif_data.get(42036)  if exif_data else None

            # Grab file metadata & exif data (TODO: very slow to process exif for each image. parallelize or process in bulk)
            exif_data = "TODO"
            # exif_data = self._process_image_exif(photo_path, ["DateTimeOriginal", "Make", "Model"]) if exif_data else {}
            # meta_data = "TODO"
            meta_data = Image.open(photo_path)._getexif()

            image_data[exposure] = {
                'exposure': exposure,
                'date': date,
                'time': time,
                'path': photo_path,
                'filename': fileName,
                'cameraBrand': cameraBrand,
                'cameraModel': cameraModel,
                'stock': stock,
                'iso': iso,
                'lensBrand': lensBrand,
                'lensModel': lensModel,
                'focalLength': focalLength,
                'location': location,
                'rating': rating,
                'fileSize': fileSize,
                'exif': exif_data,
                'metadata': meta_data
            }

        # ---- sort by date, then time ----
        # Fill Nones so sorting doesn't crash; push Nones to the end by using a high sentinel.
        sentinel_date = '9999.99.99'
        sentinel_time = '99:99:99'
        sorted_items = sorted(
            image_data.items(),
            key=lambda kv: (
                kv[1]['date'] if kv[1]['date'] else sentinel_date,
                kv[1]['time'] if kv[1]['time'] else sentinel_time
            )
        )

        return OrderedDict(sorted_items)
    

    def _bulk_exif(self, paths, tags=None):
        """
        Fills self._exif_cache for the given paths using a single exiftool call.
        If exiftool is unavailable, you can fall back to your existing get_exif,
        but preferably do nothing (cache miss) and let checks handle it gracefully.
        """
        if not paths:
            return

        # Already cached? Skip.
        to_fetch = [p for p in paths if p not in self._exif_cache]
        if not to_fetch:
            return

        if shutil.which("exiftool"):
            cmd = ["exiftool", "-j"]
            if tags:
                cmd += [f"-{t}" for t in tags]
            else:
                cmd += ["-a", "-u", "-g1"]
            cmd += to_fetch

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            data = json.loads(result.stdout or "[]")
            for d in data:
                src = d.get("SourceFile")
                if src:
                    self._exif_cache[src] = d
        else:
            # (Optional) fallback loop using your existing single-file get_exif
            for p in to_fetch:
                self._exif_cache[p] = self.get_exif(p, tags=tags)

    def _virtualCopy_identifier(self):
        # timestamp -> list[ {exposure, path} ]
        timestamp_dict = {}

        for _, data in self.image_data.items():
            date = data.get('date')
            time = data.get('time')
            exp  = data.get('exposure')
            if date and time:
                ts = f"{date} {time}"
                timestamp_dict.setdefault(ts, []).append({"exposure": exp, "path": data["path"]})

        # only timestamps with duplicates
        duplicates = {k: v for k, v in timestamp_dict.items() if len(v) > 1}

        if not duplicates:
            return False

        # collect every file once, then fetch EXIF in bulk
        unique_paths = {item["path"] for lst in duplicates.values() for item in lst}
        self._bulk_exif(unique_paths, tags=self.NEEDED_TAGS)

        for timestamp, items in duplicates.items():
            if len(items) > 2:
                # Find item with earliest ModifyDate
                original_item = min(
                    items,
                    key=lambda x: self._exif_cache.get(x["path"], {}).get("ModifyDate", "9999:99:99 99:99:99")
                )
                exposure = original_item["exposure"]

                print(f'[{self.index}]\tFound {len(items)} duplicates, keeping original #{exposure}')

            fileA, fileB = items[0]["path"], items[1]["path"]
            print(f"[{self.index}]\tDuplicates @ {timestamp}:\n\t\t[A] {os.path.basename(fileA)}\n\t\t[B] {os.path.basename(fileB)}")

            if not self._check_pano_cached(fileA, fileB):
                if not self._check_bnw_copy_cached(fileA, fileB):
                    if not self._check_crop_copy_cached(fileA, fileB):
                        print("\t\t❌❌❌ Could not ID virtual copy")
        return True

    def _check_pano_cached(self, fileA, fileB):
        exifA = self._exif_cache.get(fileA, {})
        exifB = self._exif_cache.get(fileB, {})

        if exifA.get("IsMergedPanorama"):
            print("\t\t--> [A] is a pano")
            return fileA
        if exifB.get("IsMergedPanorama"):
            print("\t\t--> [B] is a pano")
            return fileB
        return 0

    def _check_bnw_copy_cached(self, fileA, fileB):
        exifA = self._exif_cache.get(fileA, {})
        exifB = self._exif_cache.get(fileB, {})

        a_bw = exifA.get("ConvertToGrayscale")
        b_bw = exifB.get("ConvertToGrayscale")

        if a_bw and not b_bw:
            print("\t\t--> [A] is a bnw copy")
            return fileA
        if b_bw and not a_bw:
            print("\t\t--> [B] is a bnw copy")
            return fileB
        return 0

    def _check_crop_copy_cached(self, fileA, fileB):
        exifA = self._exif_cache.get(fileA, {})
        exifB = self._exif_cache.get(fileB, {})

        mpxA = exifA.get("Megapixels")
        mpxB = exifB.get("Megapixels")
        dateA = exifA.get("ModifyDate")
        dateB = exifB.get("ModifyDate")

        if mpxA != mpxB:
            # newer file = original (per your logic)
            if dateA and dateB and dateA > dateB:
                print("\t\t--> [B] is a crop")
                return fileA
            else:
                print("\t\t--> [A] is a crop")
                return fileB
        return 0




    def get_exif(self, path: str, tags: Union[str, Iterable[str], None] = None) -> str:
        """
        If `tags` is:
        - None  -> return all metadata (EXIF/IPTC/XMP when exiftool is available)
        - str   -> split on spaces/commas: "DateTimeOriginal Make Model LensModel"
        - iterable -> use as-is (['DateTimeOriginal', 'Make', ...])

        Returns a pretty-printed JSON string.
        """
        # Normalize tags to a list[str] or None
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.replace(',', ' ').split() if t.strip()]
        elif tags is not None:
            tags = list(tags)

        if shutil.which("exiftool"):
            # Build the exiftool command
            cmd = ["exiftool", "-j"]
            if tags:
                cmd += [f"-{t}" for t in tags]
            else:
                # keep your original wide grab
                cmd += ["-a", "-u", "-g1"]
            cmd.append(path)

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            data = json.loads(result.stdout or "[]")
            return data[0] if data else {}

    def get_info_image(self, exposure=None):
        # Define headers and column widths
        headers = [
            "|Index", "|Date", "|Time", "|Camera Brand", "|Camera Model", "|Stock", "|ISO",
            "|Lens Brand", "|Lens Model", "|Focal Length", "|Location", "|Rating", "|File Size"
        ]
        column_widths = [10, 12, 10, 15, 15, 10, 6, 15, 20, 14, 12, 8, 10]
        
        # Create formatted header string
        header_str = "".join(f"{header:<{width}}" for header, width in zip(headers, column_widths))
        print(header_str)
        print("-" * sum(column_widths))  # Separator line matching total width


        # Filter image_data based on exposure # if provided
        if exposure is not None:
            if isinstance(exposure, (list, tuple, set)):
                # Filter for any exposure in the list/tuple
                self.image_data = {
                    index: data
                    for index, data in self.image_data.items()
                    if data.get('exposure') in exposure
                }
            else:
                # Filter for single exposure
                self.image_data = {
                    index: data
                    for index, data in self.image_data.items()
                    if data.get('exposure') == exposure
                }

        for index, data in self.image_data.items():
            row_data = [
                # index,
                data.get('exposure', 'N/A'),
                data.get('date', 'N/A'),
                data.get('time', 'N/A'),
                data.get('cameraBrand', 'N/A'),
                data.get('cameraModel', 'N/A'),
                data.get('stock', 'N/A'),
                data.get('iso', 'N/A'),
                data.get('lensBrand', 'N/A'),
                data.get('lensModel', 'N/A'),
                data.get('focalLength', 'N/A'),
                data.get('location', 'N/A'),
                data.get('rating', 'N/A'),
                self._format_size(data.get('fileSize', 'N/A'))
            ]

            # Create formatted row string by dynamically applying column widths
            row_str = "".join(f"{str(value):<{width}}" for value, width in zip(row_data, column_widths))
            print(row_str)




