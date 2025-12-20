import numpy as np
import pandas as pd
import sys
import os
from tkinter import Tk
from tkinter.filedialog import askdirectory
import shutil
import random
from debuggerTool import debuggerTool
from time import time
from PIL import Image

DEBUG = 1
WARNING = 1
ERROR = 1
db = debuggerTool(DEBUG, WARNING, ERROR) 

class importTool:
    def __init__(self):
        
        return
    
    # Opens a roll from a path and checks to confirm validity
    def get_photo_name(self, img):
        # Define new file naming convention
        #[roll index]_[YYMMDD]_[index]_[stk]_[location]_[cam]_[lns]_[rating]
        roll_index = str(img.roll.index).zfill(3)
        date = img.dateExposed
        index = img.index
        stk = img.stk
        cam = img.cam
        lns = img.lns
        location = img.state
        rating = img.rating

        date_str = date.strftime('%y%m%d') if date is not None else '??????'
        index_str = f"{int(index):02d}" if index is not None else '??'

        # handle VC
        base_name = f"{roll_index}_{date_str}_{index_str}_{stk}_{location}_{cam}_{lns}_{rating}s"

        if img.isCopy:
            if img.isStitched or img.isPano:
                new_name = f"{base_name}_pano"
            elif img.isGrayscale and img.isColor:
                new_name = f"{base_name}_BW"
            else:
                new_name = f"{base_name}_edit"
        else:
            new_name = f"{base_name}"

        return new_name


    # copy roll
    # copy jpg
    # copy raw
    # copy wallpaper

    # copy raw based on src and dest paths
    def copy_raw(self, img, dest_folder):
        src_path = img.rawFilePath
        # define dest path
        dest_path = os.path.join(dest_folder, img.rawFileName)

        if src_path is None:
            # db.e(f'[{img.roll.index}][{img.index_str}]', 'No RAW file path found for image. Cannot copy RAW.')
            return


        if not os.path.exists(os.path.dirname(dest_path)):
            os.makedirs(os.path.dirname(dest_path))
        try:
            shutil.copy2(src_path, dest_path)
            # db.d(f'[{img.roll.index}][{img.index_str}]', f'Copied RAW')
        except Exception as e:
            db.e(f'[{img.roll.index}][{img.index_str}]', f'Error copying RAW: {e}')

        for copy in img.copies:
            self.copy_raw(copy, dest_folder)

    def copy_unmatched_raws(self, roll, dest_folder):
        # check dest folder exists, if not, create it
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        if roll.unmatched_raws:
            for file in roll.unmatched_raws:
                self.copy_file(file, dest_folder)

    def copy_file(self, src_path, dest_folder):
        dest_path = os.path.join(dest_folder, os.path.basename(src_path))
        try:
            shutil.copy2(src_path, dest_path)
        except Exception as e:
            db.e(f'File Copy', f'Error copying file to {dest_path}: {e}')

    # copy simple jpg to dest folder with new naming convention
    def copy_jpg(self, img, dest_folder):
        # check dest folder exists, if not, create it
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        # grab source file
        src_path = img.filePath

        # define new naming convention
        new_name = self.get_photo_name(img) # eg [roll index]_[YYMMDD]_[index]_[stk]_[location]_[cam]_[lns]_[rating]

        # define dest path
        dest_path = os.path.join(dest_folder, new_name + os.path.splitext(src_path)[1]) # preserve original extension

        try:
            # copy jpg
            shutil.copy2(src_path, dest_path)
            # db.d(f'[{img.roll.index}][{img.index_str}]', f'Copied JPG')
        except Exception as e:
            print(f'Error copying JPG for image {img.name}: {e}')

    def copy_preview(self, img, dest_folder):
        # check dest folder exists, if not, create it
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        # define new naming convention
        new_name = self.get_photo_name(img) + '_lowres'  # eg [roll index]_[YYMMDD]_[index]_[stk]_[location]_[cam]_[lns]_[rating]

        # define dest path
        dest_path = os.path.join(dest_folder, new_name + os.path.splitext(img.fileName)[1])  # preserve original extension

        try:
            # copy preview
            self.generate_preview(img, dest_path)
            # db.d(f'[{img.roll.index}][{img.index_str}]', f'Copied preview')
        except Exception as e:
            print(f'Error copying preview for image {img.name}: {e}')


    def generate_preview(self, img, path):
        # Generate a preview image for the given image of {size} px on shortest side
        image = img.filePath

        # Calculate new size based on shortest side == {size}
        dimensions = Image.open(image).size
        size = max(dimensions) / 4
        width, height = dimensions
        if width < height:
            new_width = size
            new_height = int((size / width) * height)
        else:
            new_height = size
            new_width = int((size / height) * width)
        
        # Downscale image
        preview = Image.open(image)
        preview.thumbnail((new_width, new_height))

        # Save preview to dest_path with name
        preview.save(path)
        return


    def copy_roll(self, roll, dest_folder):

        return
    
    def copy_wallpapers(self, dest_folder, imgs):
        # create dir if not exist
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
    
        for img in imgs:
            self.copy_jpg(img, dest_folder)


    # Copies jpg to dest_folder and adheres to size_limit. Chooses random set of rolls to meet size limit [GB].
    def generate_wallpapers(self, collection, dest_folder, rating_limit, size_limit):
        # create dir if not exist
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        # Clean up all existing files in dest_folder
        for filename in os.listdir(dest_folder):
            file_path = os.path.join(dest_folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

        # Select images based on rating limit by randomly walking through rolls until size limit of selection is met
        size_limit = size_limit * 1024 * 1024 * 1024  # convert GB to bytes
        selected = []
        total_size = 0

        # Randomize roll order
        rolls = collection.rolls.copy()
        random.shuffle(rolls)

        # Iterate through rolls and images to select based on rating and size limit
        for roll in rolls:
            images = roll.images.copy()
            for img in images:
                if img.rating >= rating_limit:
                    img_size = img.fileSize
                    if total_size + img_size <= size_limit:
                        selected.append(img)
                        total_size += img_size
                for copy in img.copies:
                    if copy.rating >= rating_limit:
                        copy_size = os.path.getsize(copy.filePath)
                        if total_size + copy_size <= size_limit:
                            selected.append(copy)
                            total_size += copy_size
                if total_size >= size_limit:
                    break
            if total_size >= size_limit:
                break
        
        print(f'Selected {len(selected)} images with total size {total_size / (1024*1024*1024):.2f} GB for wallpapers.')

        # Copy into dest_folder
        for img in selected:
            self.copy_jpg(img, dest_folder)

        return


    # Cleans up a roll by copying jpg and raw files to correct folder within library
    def cleanRoll(self, roll, library_path=None, mode=[1,1,1,1]):
        t1 = time()

        db.i(f'[{roll.index_str}]', 'Cleaning roll...')

        if library_path is None:
            library_path = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/photography'
        

        # Determine index and date of roll
        index = roll.index
        date = roll.startDate
                
        # Build target directories
        # photography
            # film
                # library
                    # YYYY
                        # XXX_YY-Mo-Mo_[STK]_[CAM]_[LOCATION(S)]
                        #     01_scans
                        #     02_exports
                        #     03_previews
                        #     04_edits
                        #     05_other


        # convert locations to string list(['X','Y']) -> 'X+Y' for folder naming
        locations_str  = '+'.join(roll.locations) if roll.locations else 'Unknown'

        # Define roll folder
        # prefix zeros on index so [001-999]
        index = roll.index_str


        roll_folder_name = f"{index}_{date.strftime('%y')}-{date.strftime('%m')}-{roll.endDate.strftime('%m')}_{roll.stk}_{roll.cam}_{locations_str}"
        roll_base_path = os.path.join(library_path, 'film', 'library', date.strftime('%Y'), roll_folder_name)

        # Build subdirectories
        scans_path = os.path.join(roll_base_path, '01_scans')
        exports_path = os.path.join(roll_base_path, '02_exports')
        previews_path = os.path.join(roll_base_path, '03_previews')
        edits_path = os.path.join(roll_base_path, '04_edits')
        other_path = os.path.join(roll_base_path, '05_other')
        unmatchedRAW_path = os.path.join(other_path, '01_unmatched_raws')

        # init progress bar
        total_length = len(roll.images) * mode[0] + len(roll.images) * mode[1] + len(roll.images) * mode[2] + roll.countCopies * mode[3]
        progress_index = 0
        
        # Copy to directories
        for img in roll.images:

            # Copy raw if exists to scans
            if mode[0]:
                progress_index += 1
                db.progress(
                    pre=f"[{index}]",
                    current=progress_index,
                    total=total_length,
                    post=f"[{img.index_str}] Copying jpg...",
                    mode="info"
                )
                self.copy_raw(img, scans_path)

            # Copy main image jpg to exports
            if mode[1]:
                progress_index += 1
                db.progress(
                    pre=f"[{index}]",
                    current=progress_index,
                    total=total_length,
                    post=f"[{img.index_str}] Copying RAW...",
                    mode="info"
                )
                self.copy_jpg(img, exports_path)
            
            # Copy previews if exists to previews
            if mode[2]:
                progress_index += 1
                db.progress(
                    pre=f"[{index}]",
                    current=progress_index,
                    total=total_length,
                    post=f"[{img.index_str}] Copying preview...",
                    mode="info"
                )
                self.copy_preview(img, previews_path)

            # Copy edits / virtual copies to edits
            if mode[3]:
                for copy in img.copies:
                    progress_index += 1
                    db.progress(
                        pre=f"[{index}]",
                        current=progress_index,
                        total=total_length,
                        post=f"[{img.index_str}] Copying copies...",
                        mode="info"
                    )
                    self.copy_jpg(copy, edits_path)
                    self.copy_preview(copy, previews_path)
            

        # copy over leftover raw files just in case
        if mode[0]:
            self.copy_unmatched_raws(roll, unmatchedRAW_path)

        t2 = time()
        db.progress(
            pre=f"[{index}]",
            current=total_length,
            total=total_length,
            post=f"[{img.index_str}] Finished archiving!",
            mode="success"
        )

        


# Library to handle file loading/offloading from local drive to external drive.
# In short:
# 1. Load RAW, JPG, or PNG files from external drive to external drive.
# 2. Offload RAW, JPG, or PNG files from local drive to external drive. (re-sync)
# 3. Delete files from local drive after offloading.
# 4. Identify file changes and update accordingly.
# 5. Log operations for tracking.



# File structure

#   /photography/
#       /digital/
#           /projects/
#           /photos/
#               /astro/
#               /landscape/...
#           /videos/
#       /film/
#           /projects/
#           /library/
#               /2020/
#                   /1_22-06-06 EK100 F3 Stockholm & Flims/
#                   ...
#                   /XX_YY-MM-DD [STK] [CAM] [LOCATION(S)]/
#                       /scans/         (raw files)
#                       /exports/       (jpg/png files)
#                       /previews/      (low-res files)
#                       /edits/         (edites / virtual copies)
#                       /other/
#               /2021/
#                   ...
#           /archive/
#       /temp/
#       /other/


