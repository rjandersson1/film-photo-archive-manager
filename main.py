
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
CLEANMODE = 0    # import from cleaned library
EXTERNAL_SSD = 0

# rolls_to_import = 'all'
# rolls_to_import = [72, 74, 83, 85]
# rolls_to_import = [3, 9, 12, 13, 35, 37, 53, 65, 66, 84] # problem rolls
# rolls_to_import = [3, 9, 12, 13]
# rolls_to_import = '19-150'
rolls_to_import = [84]


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
        library = r'/Volumes/NVME_C/Film Scanning'
        library_clean = r'/Volumes/NVME_C/photography'

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
renderer = renderTool.Renderer()
for roll in collection.rolls:
    # importer.cleanRoll(roll, library_path=library_clean, clean_raw=1, clean_jpg=0, clean_preview=0, clean_edits=0, clean_contact_sheet=0, clean_exif=0)
    # importer.cleanRoll(roll, library_path=library_clean)
    renderer.render(roll, P1=0, P2=0, P3=1, show=True)
    
    # for img in roll.images_all:
        # print(os.path.basename(img.rawFileName) if img.rawFileName else None)
    #     print(img.exif)
    #     print('\n'*3)
    #         print('\n'*1)
    #         print(img.shutterSpeed)
        # print(img.lns)
    
    continue


# =================================================================================
for i in range(3):
    print('\n')
print("===================================================================")
db.i('[I]', f"Runtime: {time() - runtime_t0:.2f}s")



# importer.generate_wallpapers_bw(collection.rolls, wallpaper_path, rating_limit=3, size_limit=1)