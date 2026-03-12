# archiver.py
import collectionObj
import debuggerTool
import importTool
import sys
import os
import shutil



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
PATH_DEBUG = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/archiver_data/temp'
ROLLS_IMPORT = 'all'

DEBUG = 0
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

    for i in range(len(collection_ext.rolls)):
        roll_loc = collection_loc.rolls[i]
        roll_ext = collection_ext.rolls[i]

        # offload(roll_loc, roll_ext, 'all')
        onload(roll_ext, 'all')


def offload(roll_loc, roll_ext, function=None):
    srcs, dsts = get_paths(roll_loc, roll_ext, function)

    if srcs == 0 or dsts == 0:
        db.e('[A]', 'offload() aborted: invalid path lists')
        return

    if len(srcs) == 0:
        db.d('[A]', 'No files to offload')
        return

    pairs = match_paths(srcs, dsts)

    if pairs == 0:
        db.e('[A]', 'offload() aborted: failed to match paths')
        return

    for pair in pairs:
        check = check_pair(pair)

        # dst does not exist yet --> copy to dst and delete src
        if check == 0:
            copy_delete(pair[0], pair[1])

        # src is equal or older than dst --> remove src only
        elif check == 1:
            move_file(pair[0], pair[1])

        # src is newer than dst --> copy to dst and delete src
        elif check == -1:
            copy_delete(pair[0], pair[1])

    return

def onload(roll_ext, function=None):
    srcs, dsts = get_paths_onload(roll_ext, function)

    if srcs == 0 or dsts == 0:
        db.e('[A]', 'onload() aborted: invalid path lists')
        return

    if len(srcs) == 0:
        db.d('[A]', 'No files to onload')
        return

    pairs = match_paths(srcs, dsts)

    if pairs == 0:
        db.e('[A]', 'onload() aborted: failed to match paths')
        return

    for pair in pairs:
        check = check_pair(pair)

        if check == 0:
            copy_file(pair[0], pair[1])
        elif check == 1:
            copy_file(pair[0], pair[1])
        elif check == -1:
            copy_file(pair[0], pair[1])

    return

# Build path list for source/destination based on mode
def get_paths(roll_loc, roll_ext, function):
    srcs = []

    if function is None or function.lower() == 'all':
        srcs.extend(get_jpg_files(roll_loc))
        srcs.extend(get_raw_files(roll_loc))
        # srcs.extend(get_preview_files(roll_loc))

    elif function.lower() == 'jpg':
        srcs.extend(get_jpg_files(roll_loc))

    elif function.lower() == 'raw':
        srcs.extend(get_raw_files(roll_loc))

    elif function.lower() == 'previews':
        srcs.extend(get_preview_files(roll_loc))

    else:
        db.e('[A]', 'Unknown offload/onload mode:', function)
        return 0, 0

    if len(srcs) == 0:
        db.d('[A]', 'get_paths(): No source files found for mode:', function)
        return [], []

    dsts = []
    for src in srcs:
        rel_path = os.path.relpath(src, roll_loc.directory)
        dst = os.path.join(roll_ext.directory, rel_path)
        dsts.append(dst)

    return srcs, dsts

def get_paths_onload(roll_ext, function):
    srcs = []

    if function is None or function.lower() == 'all':
        srcs.extend(get_jpg_files(roll_ext))
        srcs.extend(get_raw_files(roll_ext))
        # srcs.extend(get_preview_files(roll_ext))

    elif function.lower() == 'jpg':
        srcs.extend(get_jpg_files(roll_ext))

    elif function.lower() == 'raw':
        srcs.extend(get_raw_files(roll_ext))

    elif function.lower() == 'previews':
        srcs.extend(get_preview_files(roll_ext))

    else:
        db.e('[A]', 'Unknown onload mode:', function)
        return 0, 0

    if len(srcs) == 0:
        db.d('[A]', 'get_paths_onload(): No source files found for mode:', function)
        return [], []

    dsts = []
    for src in srcs:
        rel_path = os.path.relpath(src, PATH_EXTERNAL)
        dst = os.path.join(PATH_LOCAL, rel_path)
        dsts.append(dst)

    return srcs, dsts

# Ensure src file matches to dst filename
def match_paths(srcs, dsts):
    if srcs == 0 or dsts == 0:
        db.e('[A]', 'Source or Destination path list is invalid!')
        return 0

    if len(srcs) != len(dsts):
        db.e('[A]', 'Source and destination path list lengths do not match!')
        return 0

    matched_pairs = []
    for i in range(len(srcs)):
        matched_pairs.append((srcs[i], dsts[i]))

    return matched_pairs

# Check a) dst exists --> return 0 if no, b) if yes, check file date: if src older or equal to dst, return 1, if src newer than dst, return -1 
def check_pair(pair):
    src = pair[0]
    dst = pair[1]

    if not os.path.exists(dst):
        return 0

    src_mtime = os.path.getmtime(src)
    dst_mtime = os.path.getmtime(dst)

    if src_mtime <= dst_mtime:
        return 1
    else:
        return -1


# Copy file from src to dst
def copy_file(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    db.d('[A]', f'Copied:', f'{src} -> {dst}')
    return

# Copy file from src to dst and then del src
def copy_delete(src, dst):
    try:
        copy_file(src, dst)
    except Exception as e:
        db.e('[A]', f'Copy failed:', e)
        return

    if DEBUG:
        try:
            # copy src to temp folder before deleting for safety: path = PATH_DEBUG/tree2/tree1/img_file.jpg
            debug_dst = os.path.join(PATH_DEBUG, os.path.relpath(src, PATH_LOCAL))
            os.makedirs(os.path.dirname(debug_dst), exist_ok=True)
            shutil.copy2(src, debug_dst)
            db.d('[A]', f'Saved before del to:', debug_dst)
        except Exception as e:
            db.e('[A]', f'Debug copy failed:', e)
            return

    try:
        os.remove(src)
        db.d('[A]', f'Deleted:', src)
    except Exception as e:
        db.e('[A]', f'Delete failed:', e)

    return

# Move a file from src to dst: no copy needed if dst exists
def move_file(src, dst):
    try:
        if os.path.exists(dst):
            db.d('[A]', f'Destination exists, removing source:', src)
            
            if DEBUG:
                try:
                    # copy src to temp folder before deleting for safety: path = PATH_DEBUG/tree2/tree1/img_file.jpg
                    debug_dst = os.path.join(PATH_DEBUG, os.path.relpath(src, PATH_LOCAL))
                    os.makedirs(os.path.dirname(debug_dst), exist_ok=True)
                    shutil.copy2(src, debug_dst)
                    db.d('[A]', f'Saved before del to:', debug_dst)
                except Exception as e:
                    db.e('[A]', f'Debug copy failed:', e)
                    return
            
            os.remove(src)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            db.d('[A]', f'Moved:', f'{src} -> {dst}')
    except Exception as e:
        db.e('[A]', f'Move failed:', e)
    return

def get_raw_files(roll):
    rawPaths = []

    if roll.rawDirs == [-1] or roll.rawDirs is None:
        return rawPaths

    for dir in roll.rawDirs:
        if not os.path.exists(dir):
            continue
        for file in os.listdir(dir):
            rawPaths.append(os.path.join(dir, file))

    if roll.countRaw is not None and len(rawPaths) != roll.countRaw:
        db.w('[A]', f'RAW path count does not match RAW count on roll {roll.index_str}', f'expected: {roll.countRaw}, found: {len(rawPaths)}')

    return rawPaths

def get_jpg_files(roll):
    jpgPaths = []

    if roll.jpgDirs is None:
        return jpgPaths

    for dir in roll.jpgDirs:
        if not os.path.exists(dir):
            continue
        for file in os.listdir(dir):
            jpgPaths.append(os.path.join(dir, file))

    if roll.countJpg is not None and len(jpgPaths) != roll.countJpg:
        db.w('[A]', f'JPG path count does not match JPG count on roll {roll.index_str}', f'expected: {roll.countJpg}, found: {len(jpgPaths)}')

    return jpgPaths

def get_preview_files(roll):
    previewPaths = []
    dir = os.path.join(roll.directory, '03_previews')

    if not os.path.exists(dir):
        return previewPaths

    for file in os.listdir(dir):
        previewPaths.append(os.path.join(dir, file))

    return previewPaths


if __name__ == "__main__":
    main()