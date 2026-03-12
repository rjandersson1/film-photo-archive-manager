# archiver.py
import collectionObj
import debuggerTool
import importTool
import sys
import os



# Run commands from terminal to offload and onload rolls from library


# Functionality:

# offload
    # main functionality: copy files from local to external drive
        # sub functions:
            # offload all
            # offload raw --> .../01_scans/ + .../05_other/03_unmatched_raws/
            # offload jpg --> .../02_exports/ + .../04_edits/
            # offload previews --> .../03_previews/

# onload
    # main functionality: copy files from external to local
        # sub functions:
            # onload all
            # onload scans
            # onload exports
            # onload previews


# check overwrite safety: 
    # if age of file on dst is identical src --> skip + delete src
    # if age of file on dst is newer than src --> warn user + ask for overwrite confirmation (disp filepaths + dates)
    # if age of file on src is newer than dst --> warn user + ask for overwrite confirmation (disp filepaths + dates)


# identify drives:
    # list drives and let user select (only if multiple drives available!)
    # print identified directory and wait for user to confirm


PATH_LOCAL = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/archiver_data/loc/photography/film/library'
PATH_EXTERNAL = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/archiver_data/ext/photography/film/library'
ROLLS_IMPORT = [74]

DEBUG = 1
WARNING = 1
ERROR = 1
db = debuggerTool.debuggerTool(DEBUG, WARNING, ERROR)
importer = importTool.importTool()

def main():

    # init collections (loc + ext)
    collection_loc = collectionObj.collectionObj(PATH_LOCAL)
    collection_ext = collectionObj.collectionObj(PATH_EXTERNAL)

    collection_loc.build_directory_tree()
    collection_ext.build_directory_tree()

    collection_loc.import_rolls(ROLLS_IMPORT)
    collection_ext.import_rolls(ROLLS_IMPORT)

    roll = collection_loc.rolls[0]


def offload(function=None):
    return

def onload(function=None):
    return


# Copy file from src to dst
def copy_file(src, dst):
    return

# Copy file from src to dst and then del src
def copy_delete(src, dst):
    return

def get_raw_files(roll):
    rawPaths = []
    for dir in roll.rawDirs:
        for file in os.listdir(dir):
            rawPaths.append(os.path.join(dir,file))

    if len(rawPaths) != roll.rawCount:
        db.w('[A]', f'RAW path count does not match RAW count on roll {roll.index_str}', f'expected: {roll.rawCount}, found: {len(rawPaths)}')
    
    if len(rawPaths) == 0:
        return 0

    return rawPaths

def get_jpg_files(roll):
    jpgPaths = []

    for dir in roll.jpgDirs:
        for file in os.listdir(dir):
            jpgPaths.append(os.path.join(dir,file))

    if len(jpgPaths) != roll.jpgCount:
        db.w('[A]', f'JPG path count does not match JPG count on roll {roll.index_str}', f'expected: {roll.jpgCount}, found: {len(jpgPaths)}')

    if len(jpgPaths) == 0:
        return 0

    return jpgPaths

def get_preview_files(roll):
    previewPaths = []
    dir = os.path.join(roll.directory, '03_previews')

    if os.path.exists(dir):
        for file in os.listdir(dir):
            previewPaths.append(os.path.join(dir,file))
    else:
        db.w('[A]', 'Preview Folder not found!')
        return 0

    return previewPaths




if __name__ == "__main__":
    main()