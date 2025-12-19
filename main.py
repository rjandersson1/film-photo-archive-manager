#TODO: fix the shit with duplicates on roll 35 ???
    # changed all duplicated indeces to '#9XX' to try to fix it but it now half works? still finding index duplicate issues
    # also bug in copies: its passing the copy to the correct master, but the index of the copy is totally wrong to the master.



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
importlib.reload(rollObj)  
importlib.reload(exposureObj) 
importlib.reload(collectionObj)  
importlib.reload(renderTool)
importlib.reload(importTool)

# ===================d===== Setup Vars ================================
DEVMODE = 1         # If true, work in local dir. If false, work in production dir.

# rolls_to_import = 'all'
# rolls_to_import = [29, 32, 35, 37] # problem rolls (29 has G200 OM accura issue, hardcode fix) (32 has dateIncreasing issue (ignored)) [35] is bologna shitshow, [37] missing
# rolls_to_import = [35]
# rolls_to_import = [72, 74, 83, 85]
rolls_to_import = [72]
# rolls_to_import = [83]
# rolls_to_import = '1-10'
# rolls_to_import = '70-80'
# rolls_to_import = [68]

# deine wallpaper path
wallpaper_path = r'/Users/rja/Documents/Wallpapers/wallpapers-1'

# define library path for cleaning up
cleanup_path = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/photography'


# ====================================================================


# Set library path
if DEVMODE:
    # Set abspath and reference library to this workspace
    sys.path.append(os.path.abspath(r'C:\A_Documents\Documents\Coding\Lightroom_FileFinder'))
    library = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/filmCollectionTestAll'
    library = cleanup_path
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
collection.build_directory_tree()
t1 = time()
collection.import_rolls(rolls_to_import)
t2 = time()
print(f'Import completed in {t2 - t1:.2f} seconds.')

# Example rendering
# for roll in collection.rolls:
#     img = roll.images[0]
#     contact_sheet = renderTool.Renderer(roll)
#     contact_sheet.render()

# Example wallpaper generation
# importer.generate_wallpapers(collection, wallpaper_path, rating_limit=3, size_limit=3)

# Example Clean up library
# importer.cleanRoll(roll, library_path=None, mode=[0,0,1,1])

for i in range(3):
    print('\n')








for i in range(3):
    print('\n')
print("===================================================================")
