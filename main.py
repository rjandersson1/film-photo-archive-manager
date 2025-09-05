import numpy as np
import pandas as pd
import sys
import os
from PIL import Image
from PIL.ExifTags import TAGS
import re
import glob
import importlib  # Import the importlib module

# Set the path
sys.path.append(os.path.abspath(r'C:\A_Documents\Documents\Coding\Lightroom_FileFinder'))

# Import and reload modules
import collectionObj
import rollObj 
import exposureObj 
import renderTool 
importlib.reload(rollObj)  
importlib.reload(exposureObj) 
importlib.reload(collectionObj)  
importlib.reload(renderTool)

print("===================================================================")
print("===================================================================")
print("===================================================================")
for i in range(20):
    print('\n')


# Define the file path
library = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/filmCollectionTest'

# Initialize
collection = collectionObj.collectionObj(library)
collection.build_directory_tree()

# Import rolls
collection.import_rolls([1,2,3])


# Examples of other import options:
# collection.import_rolls('1-99')
# collection.import_rolls([1,2,3])
# collection.import_rolls('all')
# collection.import_roll(10)



for i in range(3):
    print('\n')
print("===================================================================")
