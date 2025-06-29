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
import Renderer
importlib.reload(RollMetadataDef)  # Force reload of RollMetadataDef
importlib.reload(FilmCollectionDef)  # Force reload of FilmCollectionDef
importlib.reload(Renderer)  # Force reload of Renderer

# Import the classes from the reloaded modules1
from RollMetadataDef import RollMetadata
from FilmCollectionDef import FilmCollection
from Renderer import Renderer


# Define the file path
# fileDir = r'C:\A_Documents\Documents\Coding\Lightroom_FileFinder\testFiles\Film Scanning'
# fileDir = r'C:\A_Documents\Photography\Film Scanning'
# fileDir = r'/Users/rja/Photography/Film Scanning'
fileDir = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/filmCollectionTest'
# fileDir = r'D:\backup film scanning 26.06.23'

collection = FilmCollection(fileDir)

for i in range(5):
    print('\n')

rollA = collection.getRoll(74)
# print(rollA.rollName)
# print(rollA.get_info_image())
# collection.help()
# print(rollA.camera)
# print(rollA.image_data[1])
# print(rollA.title)

renderer = Renderer(rollA)
renderer.run()