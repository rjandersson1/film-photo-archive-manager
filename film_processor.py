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
import RollMetadataDef
import FilmCollectionDef
importlib.reload(RollMetadataDef)  # Force reload of RollMetadataDef
importlib.reload(FilmCollectionDef)  # Force reload of FilmCollectionDef

# Import the classes from the reloaded modules1
from RollMetadataDef import RollMetadata
from FilmCollectionDef import FilmCollection

# Define the file path
# fileDir = r'C:\A_Documents\Documents\Coding\Lightroom_FileFinder\testFiles\Film Scanning'
fileDir = r'C:\A_Documents\Photography\Film Scanning'
# fileDir = r'D:\backup film scanning 26.06.23'

collection = FilmCollection(fileDir)

collection.plot.cumulative_photos_over_time_with_span_and_labels('date','cameraModel','2021.01.01','2024.01.01')