#TODO: fix the shit with duplicates on roll 35 ???
    # changed all duplicated indeces to '#9XX' to try to fix it but it now half works? still finding index duplicate issues
    # also bug in copies: its passing the copy to the correct master, but the index of the copy is totally wrong to the master.
    # hardcode a solution for [083][05] location unknown error

# final check
# 0-10 good, [8] has STD folder conflicts --> rename to 5mb. [8] also has location error on two images
# 10-20 good
# 20-30 good, had to rework copy finding on [25] but works now
# 30-40 needs work:
#           [35] bologna works now, but only bc I have changed #99 for all VCs. 32 as misidentified 4 as master to 3. Reworked copy finding. [035][34] and [035][35] have location issues (fixed).
#           [33] and [36] had camera exif issues on some images (model='SONY'), (make='DSLR-A550') --> hardcoded a fix in verify_camera in exposureObj
# 40-50 good, [45][46] both don't have states given (sweden/denmark). Added clause for if location but !state, then ignore location err.
#             [41] had camera exif issues on some images (model='SONY'), (make='DSLR-A550') --> hardcoded a fix in verify_camera in exposureObj  
# 50-60 good
# 60-70 good, [65] and [66] missing jpg but expected. [67][7] wrong master/copy rel. [68] [02]&[03] have identical date, so copy is checked. Hardcode to avoid checking copies on this roll
# 70-80 good, had to remove jpgDirs when 5mb/5mp was in jpgdirs, fixed double rawDir path setting. [78] has camera cast error (fixed), and raw missing for [78][15] (fixed): [78][15] had tif panorama quirks
# 80-90 good, [84] was never exported? no jpegs?? need to reexport...
# 90-92 good

# TODO:
# reexport [84]
# handle HDR
# refactor functions and clean everything up...


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
DEVMODE = 0         # If true, work in local dir. If false, work in production dir. Contains rolls 72, 74, 83, 85

# rolls_to_import = 'all'
# rolls_to_import = [72, 74, 83, 85]
# rolls_to_import = '91-95'
rolls_to_import = [9]


# deine wallpaper path
wallpaper_path = r'/Users/rja/Documents/Wallpapers/wallpapers-1'

# define library path for cleaning up
cleanup_path = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/photography/film/library'


# ====================================================================

runtime_t0 = time()
# Set library path
if DEVMODE:
    # Set abspath and reference library to this workspace
    sys.path.append(os.path.abspath(r'C:\A_Documents\Documents\Coding\Lightroom_FileFinder'))
    library = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/filmCollectionTestAll'
else:
    sys.path.append(os.path.abspath(r'C:\A_Documents\Documents\Coding\Lightroom_FileFinder'))
    library = r'/Users/rja/Photography/Film Scanning'

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


display_preview = 1
display_preview = 0
display_info = 0
display_info = 1

preview_size = 75
for roll in collection.rolls:
    for img in roll.images:
        if img.containsCopies and display_info:
            print(f'[{img.roll.index_str}][{img.index_str}]\t{img.copyCount}x')
            print(f'\t\tMASTER\t{img.index_original}\t{img.copyType}\t{img.rawFileName}\t{img.fileSize/1024/1024:.0f}Mb\t{img.mpx:.0f}MP\t{img.aspectRatio:.2f}:1\tisColor:{int(img.isColor)}\tisBlackAndWhite:{int(img.isBlackAndWhite)}\tisGrayscale:{int(img.isGrayscale)}')
            if display_preview: img.display(preview_size)
            for copy in img.copies:
                if display_preview: copy.display(preview_size)
                print(f'\t\tCOPY\t{copy.index_original}\t{copy.copyType}\t{copy.rawFileName}\t{copy.fileSize/1024/1024:.0f}Mb\t{copy.mpx:.0f}MP\t{copy.aspectRatio:.2f}:1\tisColor:{int(copy.isColor)}\tisBlackAndWhite:{int(copy.isBlackAndWhite)}\tisGrayscale:{int(copy.isGrayscale)}')
            print('\n')


# importer.generate_wallpapers_bw(collection.rolls, wallpaper_path, rating_limit=3, size_limit=1)

for img in collection.rolls[0].images_all:
    print(img.index, img.location, img.state, img.country)


# =================================================================================
for i in range(3):
    print('\n')
print("===================================================================")
db.i('[I]', f"Runtime: {time() - runtime_t0:.2f}s")
