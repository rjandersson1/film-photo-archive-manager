
# TODO:
# reexport [84]
# handle HDR
# refactor functions and clean everything up...

# reworking exif saving: (tests done for 072, 074, 083, 085)
# - v0: cmd request fetch exif every image (batched by roll, with +10s savings).
#               benchmark time:     65.00s (full! old library)
#               time to clean rolls:     80.00s 
#               benchmark time:     3.08s (old library)
#               benchmark time:     3.08s (cleaned library)
# - v1: export jsons
#              time to clean rolls:     70.00s
# - v2: import from existing exif
#              time to clean rolls:     81.00s
#              benchmark time:      2.51 (cleaned, json exif import)


# 1-10
# 11-20
# 21-30
# 31-40 124s        [40] has two cameras on the roll!
# 41-50
# 51-60
# 61-70
# 71-80
# 81-90
# 91-100

import numpy as np
import pandas as pd
import sys
import os
from PIL import Image
from PIL.ExifTags import TAGS
import re
import glob
import importlib  # Import the importlib module
from time import time

# Import and reload modules
import collectionObj
import rollObj 
import exposureObj 
import renderTool 
import importTool
import debuggerTool
importlib.reload(rollObj)  
importlib.reload(exposureObj) 
importlib.reload(collectionObj)  
importlib.reload(renderTool)
importlib.reload(importTool)

# ======================== Setup Vars ================================
DEVMODE = 1         # If true, work in local dir. If false, work in production dir. Contains rolls 72, 74, 83, 85
CLEANMODE = 1    # import from cleaned library
EXTERNAL_SSD = 0

rolls_to_import = 'all'
# rolls_to_import = [72, 74, 83, 85]
# rolls_to_import = '31-40'
# rolls_to_import = [72]


# deine wallpaper path
wallpaper_path = r'/Users/rja/Documents/Wallpapers/wallpapers-1'

# define library path for cleaning up
library_clean = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/photography'


# ====================================================================

runtime_t0 = time()
# Set library path
if DEVMODE:
    # Set abspath and reference library to this workspace
    sys.path.append(os.path.abspath(r'C:\A_Documents\Documents\Coding\Lightroom_FileFinder'))
    library = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/filmCollectionTestAll'
    if CLEANMODE:
        library = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/photography/film/library'
else:
    sys.path.append(os.path.abspath(r'C:\A_Documents\Documents\Coding\Lightroom_FileFinder'))
    library = r'/Users/rja/Photography/Film Scanning'
    if EXTERNAL_SSD:
        library = r'/Volumes/NVME_B/backup_NVME_A_08.05.2025/A_Documents/Photography/Film Scanning'
        library_clean = r'/Volumes/NVME_B/photography'

print("===================================================================")
print("===================================================================")
print("===================================================================")
for i in range(20):
    print('\n')


# Initialize collection
collection = collectionObj.collectionObj(library)
importer = importTool.importTool()
db = debuggerTool.debuggerTool()
collection.build_directory_tree()

# Import rolls
t1 = time()
collection.import_rolls(rolls_to_import)
t2 = time()
db.i('[I]', f'Import completed in {t2 - t1:.2f}s')

# Example rendering
# for roll in collection.rolls:
#     img = roll.images[0]
#     contact_sheet = renderTool.Renderer(roll)
#     contact_sheet.render()

# Example wallpaper generation
# importer.generate_wallpapers(collection.rolls, wallpaper_path, rating_limit=3, size_limit=1)

# Example Clean up library
# importer.cleanRoll(collection.rolls[0], library_path=None, mode=[1,1,0,1])

for i in range(3):
    print('\n')

# =================================================================================
# =================================================================================




# for roll in collection.rolls:
#     importer.cleanRoll(roll, library_path=library_clean, mode=[1,1,1,1,0,1])

# TODO: bug when exporting a roll, raw missing?

# for roll in collection.rolls:
#     print('Cameras on roll:', roll.cameras)
#     for img in roll.images_all:
#         print(img.index, img.camera, '  -->  ', img.cam)








# =================================================================================
for i in range(3):
    print('\n')
print("===================================================================")
db.i('[I]', f"Runtime: {time() - runtime_t0:.2f}s")

# display_preview = 1
# display_preview = 0
# display_info = 0
# display_info = 1

# preview_size = 75
# for roll in collection.rolls:
#     for img in roll.images:
#         if img.containsCopies and display_info:
#             print(f'[{img.roll.index_str}][{img.index_str}]\t{img.copyCount}x')
#             print(f'\t\tMASTER\t{img.index_original}\t{img.copyType}\t{img.rawFileName}\t{img.fileSize/1024/1024:.0f}Mb\t{img.mpx:.0f}MP\t{img.aspectRatio:.2f}:1\tisColor:{int(img.isColor)}\tisBlackAndWhite:{int(img.isBlackAndWhite)}\tisGrayscale:{int(img.isGrayscale)}')
#             if display_preview: img.display(preview_size)
#             for copy in img.copies:
#                 if display_preview: copy.display(preview_size)
#                 print(f'\t\tCOPY\t{copy.index_original}\t{copy.copyType}\t{copy.rawFileName}\t{copy.fileSize/1024/1024:.0f}Mb\t{copy.mpx:.0f}MP\t{copy.aspectRatio:.2f}:1\tisColor:{int(copy.isColor)}\tisBlackAndWhite:{int(copy.isBlackAndWhite)}\tisGrayscale:{int(copy.isGrayscale)}')
#             print('\n')


# importer.generate_wallpapers_bw(collection.rolls, wallpaper_path, rating_limit=3, size_limit=1)