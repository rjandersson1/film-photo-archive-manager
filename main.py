#TODO: fix the shit with duplicates on roll 35 ???
    # changed all duplicated indeces to '#9XX' to try to fix it but it now half works? still finding index duplicate issues
    # also bug in copies: its passing the copy to the correct master, but the index of the copy is totally wrong to the master.
    # hardcode a solution for [083][05] location unknown error

# final check
# 0-10 good
# 10-20 good
# 20-30 good, had to rework copy finding on [25] but works now
# 30-40 needs work, [35] bologna works now, but only bc I have changed #99 for all VCs. 32 as misidentified 4 as master to 3. Reworked copy finding. [035][34] and [035][35] have location issues (fixed).
# 40-50 good, [45][46] both don't have states given (sweden/denmark). Added clause for if location but !state, then ignore location err. TODO: set state to location as fallback?
# 50-60
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

rolls_to_import = 'all'
# rolls_to_import = [72, 74, 83, 85]
# rolls_to_import = [74]
# rolls_to_import = '35-40'
# rolls_to_import = [45]

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
collection_new = collectionObj.collectionObj(cleanup_path)
importer = importTool.importTool()
db = debuggerTool.debuggerTool()
collection.build_directory_tree()
# collection_new.build_directory_tree()

# Import rolls
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
# importer.cleanRoll(collection.rolls[0], library_path=None, mode=[1,1,0,1])

for i in range(3):
    print('\n')

# =================================================================================
# =================================================================================


rolls = collection.rolls

display_preview = 0
preview_size = 33

# for roll in rolls:
#     for img in roll.images:
#         if img.containsCopies:
#             print(f'[{img.roll.index_str}][{img.index_str}]\t{img.copyCount}x')
#             print(f'\t\tMASTER\t{img.name}\t{img.copyType}\t{img.rawFileName}\t{img.fileSize/1024/1024:.2f}Mb\t{img.mpx:.2f}MP\t{img.aspectRatio:.2f}:1')
#             if display_preview: img.display(preview_size)
#             for copy in img.copies:
#                 if display_preview: copy.display(preview_size)
#                 print(f'\t\tCOPY\t{copy.name}\t{copy.copyType}\t{copy.rawFileName}\t{copy.fileSize/1024/1024:.2f}Mb\t{copy.mpx:.2f}MP\t{copy.aspectRatio:.2f}:1')
#             print('\n')




# importer.generate_wallpapers(collection, wallpaper_path, rating_limit=4, size_limit=2)



# =================================================================================
for i in range(3):
    print('\n')
print("===================================================================")
print(f"Runtime: {time() - runtime_t0:.2f}s")
