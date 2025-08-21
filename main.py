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

# Define the file path
# fileDir = r'C:\A_Documents\Documents\Coding\Lightroom_FileFinder\testFiles\Film Scanning'
# fileDir = r'C:\A_Documents\Photography\Film Scanning' 
# fileDir = r'/Users/rja/Photography/Film Scanning'
fileDir = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/filmCollectionTest'
# fileDir = r'D:\backup film scanning 26.06.23'

collection = collectionObj.collectionObj(fileDir)

for i in range(5):
    print('\n')


roll = collection.getRoll(72)
image = roll.getImage(1)
image.getInfo()