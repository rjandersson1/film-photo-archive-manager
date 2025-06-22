import numpy as np
import pandas as pd
import sys
import os
from PIL import Image
from PIL.ExifTags import TAGS
import re
import glob
from datetime import datetime



# TODO: fix 'stk' attribute and related functions

class RollMetadata:
    def __init__(self, directory, collection):
        # Initialize RollMetadata with a base directory and default metadata values
        self.directory = directory # subfolder directory eg. \...\2022 - 135\2_22-06-12 Gold 200 Zurich
        self._collection = collection # address of collection that roll was added to 
        self.stock = "Unknown"  # Film stock (type of film used)
        self.startDate = "Unknown"  # Start date for the roll
        self.endDate = "Unknown"  # Start date for the roll
        self.duration = "Unknown" # Duration between start and end of roll
        self.index = "Unknown"  # Index extracted from folder name
        self.title = "Unknown"  # Title for the roll
        self.camera = "Unknown"  # Camera model used for the roll
        self.iso = "Unknown"  # ISO value, set to "Unknown" by default
        self.stk = "Uknown"
        self.sizeAll = "Unknown"
        self.sizeJpg = "Unknown"
        self.sizeRaw = "Unknown"
        self.count = "Unknown"
        self.countJpg = "Unknown"
        self.countRaw = "Unknown"

        # Processes all files and builds metadata list
        self._process_files()
        if self.jpgPath is None:
            print(f"Warning: No JPG files found in {os.path.split(self.directory)[1]}")
            del self
            return

        self.image_data = self._process_image_metadata()

        # Attribute list of items in roll
        self._attribute_list = {
            "Directory": self.directory,
            "Stock": self.stock,
            "Start Date": self.startDate,
            "End Date": self.endDate,
            "Time Frame": self.duration,
            "Index": self.index,
            "Title": self.title,
            "Camera": self.camera,
            "ISO": self.iso,
            "Stock Abbreviation (STK)": self.stk,
            "JPEG Directory": self.jpgPath,
            "RAW Directory": self.rawPath,
            "JPEG Size": self._format_size(self.sizeJpg),
            "RAW Size": self._format_size(self.sizeRaw),
            "Total Size": self._format_size(self.size),
            "Photo Count": self.count
        }

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
        self.count = self.countJpg + self.countRaw
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
    def get_info(self):
        # Print a formatted table
        print(f"\n{'Attribute':<25} | {'Value'}")
        print("-" * 60)
        for attr, value in self._attribute_list.items():
            print(f"{attr:<25} | {value}")
        print("-" * 60)

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
            print(f"Total: {self._format_size(self.size)} and {self.count} files")
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
            if not photo.endswith('.jpg'): continue # Skip file if not jpg 
            photo_path = os.path.join(self.jpgPath, photo)
            fileSize = os.path.getsize(photo_path)/(1024**2)
            exif_data = Image.open(photo_path)._getexif()

            # Gather date and check for duplicates
            date_str = exif_data.get(36867) if exif_data else None
            date = '.'.join(date_str.split(" ")[0].split(':')) if date_str else None
            time = date_str.split(" ")[1] if date_str else None

            # # Check for duplicates in image_data TODO: I dont think there is any good way to count duplicates... too many photos have identical date/time
            # duplicate_found = False
            # for item in image_data.values():
            #     if item['date'] == date and item['time'] == time:
            #         # print(f"[{self.index}] Dupe: {date} at {time} in [{photo}]")
            #         duplicate_found = True
            #         images_removed = images_removed + 1 #DEBUG
            #         break
            # if duplicate_found:
            #     continue # skip if duplicate found
            
            index = index + 1

            # gather rest of exif_data
            cameraBrand = exif_data.get(271) if exif_data else None
            cameraModel = exif_data.get(272) if exif_data else None
            iso = exif_data.get(34855) if exif_data else None
            focalLength = exif_data.get(37386) if exif_data else None
            lensBrand = exif_data.get(42035) if exif_data else None
            lensModel = exif_data.get(42036) if exif_data else None

            # Extract location, stock, rating from file name
            fileName = photo.split(".jpg")[0]  # remove extension

            if len(fileName.split(" - ")) == 1:  # Case 1
                splitName = fileName.split(' ')
                splitName = splitName[1:-1]  # trim off date and index
                location = splitName[-1]
                splitName = splitName[:-1]

                # Extract stock
                iso_list = []
                for item in splitName:
                    iso_list.append(item)
                    try:
                        int(item)  # Check if ISO number
                        break
                    except ValueError:
                        continue
                stock = ' '.join(iso_list)
                rating = None
            else:  # Case 2
                splitName = fileName.split(" - ")

                if '#' in fileName:  # Case 2.1 [23-01-01 - Zurich - Ektar 100 - F3 - 3s - #2]
                    location = splitName[1]
                    stock = splitName[2]
                    splitName = splitName[3:]

                    if len(splitName) == 1:  # Case 2.1.1 [Maxxum 7000 18-55mm #1]
                        rating = None
                    else:  # Case 2.1.2 ['F3', '3s', '#2']
                        rating = splitName[1].split('s')[0]
                else:  # Case 2.2 [23-06-04 - 1 - Falsterbo - P400 - F3 50mm1.4 - 2s]
                    try:
                        location = splitName[2]
                        stock = splitName[3]
                        rating = splitName[-1].split('s')[0]
                    except IndexError:
                        print(f"Error: out of bounds for {self.index} {splitName}")
                        location = "error"
                        stock = "error"
                        rating = "error"

            # Store each image’s metadata in the dictionary with index as key
            image_data[index] = {
                'date': date,
                'time': time,
                'cameraBrand': cameraBrand,
                'cameraModel': cameraModel,
                'stock': stock,
                'iso': iso,
                'lensBrand': lensBrand,
                'lensModel': lensModel,
                'focalLength': focalLength,
                'location': location,
                'rating': rating,
                'fileSize': fileSize
            }
        return image_data   

    def get_info_image(self):
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

        # Print each row of data with dynamically set column widths
        for index, data in self.image_data.items():
            row_data = [
                index,
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
