# archiver.py
import collectionObj
import debuggerTool
import importTool
import sys
import os
import shutil
from time import time

# TODO: add size debug info, and final checks before running (copy count, size to copy, delete amount...)


# Run commands from terminal to offload and onload rolls from library


# Functionality:

# offload
#     main functionality: copy files from local to external drive
#         sub functions:
#             offload all
#             offload raw --> .../01_scans/ + .../05_other/03_unmatched_raws/
#             offload jpg --> .../02_exports/ + .../04_edits/
#             offload previews --> .../03_previews/

# onload
#     main functionality: copy files from external to local
#         sub functions:
#             onload all
#             onload scans
#             onload exports
#             onload previews


# check overwrite safety:
#     if age of file on dst is identical src --> skip + delete src
#     if age of file on dst is newer than src --> warn user + ask for overwrite confirmation (disp filepaths + dates)
#     if age of file on src is newer than dst --> warn user + ask for overwrite confirmation (disp filepaths + dates)


# identify drives:
#     list drives and let user select (only if multiple drives available!)
#     print identified directory and wait for user to confirm


PATH_LOCAL = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/archiver_data/photography/film/library'
PATH_EXTERNAL = r'/Volumes/NVME_C/photography-testing/film/library'
PATH_DEBUG = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/archiver_data/temp'
ROLLS_IMPORT = 'all'

DEBUG = 0
WARNING = 1
ERROR = 1
db = debuggerTool.debuggerTool(DEBUG, WARNING, ERROR)
importer = importTool.importTool()


def main():
    t1 = time()
    db.d('[A]', 'Archiver start')
    db.d('[A]', 'Configured paths', [
        f'PATH_LOCAL:    {PATH_LOCAL}',
        f'PATH_EXTERNAL: {PATH_EXTERNAL}',
        f'PATH_DEBUG:    {PATH_DEBUG}',
        f'ROLLS_IMPORT:  {ROLLS_IMPORT}',
        f'DEBUG:         {DEBUG}',
        f'WARNING:       {WARNING}',
        f'ERROR:         {ERROR}',
    ])

    # init collections (loc + ext)
    collection_loc = collectionObj.collectionObj(PATH_LOCAL)
    collection_ext = collectionObj.collectionObj(PATH_EXTERNAL)

    collection_loc.build_directory_tree()
    collection_ext.build_directory_tree()

    collection_loc.import_rolls(ROLLS_IMPORT)
    collection_ext.import_rolls(ROLLS_IMPORT)

    print('\n'*3)

    size_loc = 0
    size_ext = 0
    for roll in collection_loc.rolls:
        for dirpath, dirnames, filenames in os.walk(roll.directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                size_loc += safe_getsize(filepath)
    for roll in collection_ext.rolls:
        for dirpath, dirnames, filenames in os.walk(roll.directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                size_ext += safe_getsize(filepath)
    
    db.d('[A]', 'Total size summary', [
    f'local total size:    {format_bytes(size_loc)}',
    f'external total size: {format_bytes(size_ext)}',
    ])


    
    db.i('[A]', 'Collections imported', [
        f'local rolls:    {len(collection_loc.rolls)} :: {format_bytes(size_loc)}',
        f'external rolls: {len(collection_ext.rolls)} :: {format_bytes(size_ext)}',
    ])

    if len(collection_loc.rolls) != len(collection_ext.rolls):
        db.w('[A]', 'Local/external roll counts differ', [
            f'local:    {len(collection_loc.rolls)}',
            f'external: {len(collection_ext.rolls)}',
        ])

    for i in range(len(collection_ext.rolls)):
        roll_loc = collection_loc.rolls[i]
        roll_ext = collection_ext.rolls[i]

        db.d('[A]', f'Processing roll {i + 1}/{len(collection_ext.rolls)}', [
            f'roll_loc.index: {roll_loc.index_str}',
            f'roll_ext.index: {roll_ext.index_str}',
            f'local dir:      {roll_loc.directory}',
            f'external dir:   {roll_ext.directory}',
        ])

        # offload(roll_loc, roll_ext, 'all')
        onload(roll_ext, 'all')

    size_loc_end = 0
    size_ext_end = 0
    for roll in collection_loc.rolls:
        for dirpath, dirnames, filenames in os.walk(roll.directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                size_loc_end += safe_getsize(filepath)
    for roll in collection_ext.rolls:
        for dirpath, dirnames, filenames in os.walk(roll.directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                size_ext_end += safe_getsize(filepath)

    delta_loc = size_loc_end - size_loc
    delta_ext = size_ext_end - size_ext


    t2 = time()
    db.s('[A]', f'Archiver finished in {t2-t1:.2f}s', [
        f'loc: {format_bytes(size_loc)}\t--> {format_bytes(size_loc_end)}\tdelta= ({format_bytes(delta_loc)})',
        f'ext: {format_bytes(size_ext)}\t--> {format_bytes(size_ext_end)}\tdelta= ({format_bytes(delta_ext)})'
        ])


def offload(roll_loc, roll_ext, function=None):
    db.d('[A]', f'offload() start', [
        f'roll:     {roll_loc.index_str}',
        f'mode:     {function}',
        f'src root: {roll_loc.directory}',
        f'dst root: {roll_ext.directory}',
    ])

    srcs, dsts = get_paths(roll_loc, roll_ext, function)

    if srcs == 0 or dsts == 0:
        db.e('[A]', 'offload() aborted: invalid path lists')
        return

    if len(srcs) == 0:
        db.i(f'[A]{roll_loc.dbIdx}', 'offload() no files to process', f'mode: {function}')
        return

    pairs = match_paths(srcs, dsts)

    if pairs == 0:
        db.e('[A]', 'offload() aborted: failed to match paths')
        return

    summary = summarize_pairs(pairs)
    db.d('[A]', 'offload() plan', [
        f'roll:                    {roll_loc.index_str}',
        f'mode:                    {function}',
        f'total files:             {summary["total_files"]}',
        f'total src size:          {format_bytes(summary["total_src_bytes"])}',
        f'copy+delete count:       {summary["copy_delete_count"]}',
        f'copy+delete bytes:       {format_bytes(summary["copy_delete_bytes"])}',
        f'delete-only count:       {summary["delete_only_count"]}',
        f'delete-only bytes:       {format_bytes(summary["delete_only_bytes"])}',
        f'overwrite newer dst:     {summary["dst_older_count"]}',
        f'overwrite newer dst GB:  {format_bytes(summary["dst_older_bytes"])}',
        f'missing dst count:       {summary["missing_dst_count"]}',
    ])

    size = 0
    if function == 'raw':
        size = roll_ext.sizeRaw
    if function == 'jpg':
        size = roll_ext.sizeJpg
    if function == 'all':
        size = roll_ext.sizeAll

    db.i(f'[A]{roll_ext.dbIdx}', 'Offloading...', format_bytes(size))

    processed = 0
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

        processed += 1



    db.s('[A]', 'offload() complete', f'{roll_loc.index_str} :: {format_bytes(size)}')
    return


def onload(roll_ext, function=None):
    db.d('[A]', 'onload() start', [
        f'roll:     {roll_ext.index_str}',
        f'mode:     {function}',
        f'src root: {roll_ext.directory}',
        f'dst root: {PATH_LOCAL}',
    ])

    srcs, dsts = get_paths_onload(roll_ext, function)

    if srcs == 0 or dsts == 0:
        db.e('[A]', 'onload() aborted: invalid path lists')
        return

    if len(srcs) == 0:
        db.i('[A]', 'onload() no files to process', [
            f'roll: {roll_ext.index_str}',
            f'mode: {function}',
        ])
        return

    pairs = match_paths(srcs, dsts)

    if pairs == 0:
        db.e('[A]', 'onload() aborted: failed to match paths')
        return

    summary = summarize_pairs(pairs)
    db.d('[A]', 'onload() plan', [
        f'roll:                 {roll_ext.index_str}',
        f'mode:                 {function}',
        f'total files:          {summary["total_files"]}',
        f'total src size:       {format_bytes(summary["total_src_bytes"])}',
        f'copy-if-missing:      {summary["missing_dst_count"]}',
        f'copy-if-src-newer:    {summary["dst_older_count"]}',
        f'skip older/equal dst: {summary["dst_exists_count"] - summary["dst_older_count"]}',
    ])

    size = 0
    if function == 'raw':
        size = roll_ext.sizeRaw
    if function == 'jpg':
        size = roll_ext.sizeJpg
    if function == 'all':
        size = roll_ext.sizeAll
    db.i(f'[A]{roll_ext.dbIdx}', 'Onloading...', format_bytes(size))

    copied = 0
    skipped = 0

    for pair in pairs:
        check = check_pair(pair)

        # dst missing -> copy
        if check == 0:
            copy_file(pair[0], pair[1])
            copied += 1

        # src older or equal to dst -> skip copy
        elif check == 1:
            db.d('[A]', 'onload() skipped: dst already up-to-date', [
                f'src: {pair[0]}',
                f'dst: {pair[1]}',
            ])
            skipped += 1

        # src newer than dst -> copy
        elif check == -1:
            copy_file(pair[0], pair[1])
            copied += 1

    db.d('[A]', 'onload() complete', [
        f'roll:          {roll_ext.index_str}',
        f'mode:          {function}',
        f'copied files:  {copied}',
        f'skipped files: {skipped}',
    ])
    return

# Build path list for source/destination based on mode
def get_paths(roll_loc, roll_ext, function):
    srcs = []

    if function is None or function.lower() == 'all':
        jpgs = get_jpg_files(roll_loc)
        raws = get_raw_files(roll_loc)
        previews = []
        # previews = get_preview_files(roll_loc)

        srcs.extend(jpgs)
        srcs.extend(raws)
        # srcs.extend(previews)

    elif function.lower() == 'jpg':
        jpgs = get_jpg_files(roll_loc)
        srcs.extend(jpgs)

    elif function.lower() == 'raw':
        raws = get_raw_files(roll_loc)
        srcs.extend(raws)

    elif function.lower() == 'previews':
        previews = get_preview_files(roll_loc)
        srcs.extend(previews)

    else:
        db.e('[A]', 'Unknown offload/onload mode:', function)
        return 0, 0

    if len(srcs) == 0:
        db.d(f'[A][{roll_loc.dbIdx}]', 'get_paths(): no source files found', f'mode: {function}')
        return [], []

    dsts = []
    for src in srcs:
        rel_path = os.path.relpath(src, roll_loc.directory)
        dst = os.path.join(roll_ext.directory, rel_path)
        dsts.append(dst)

    db.d('[A]', 'get_paths() built path lists', [
        f'roll:      {roll_loc.index_str}',
        f'mode:      {function}',
        f'src count:  {len(srcs)}',
        f'dst count:  {len(dsts)}',
        f'src bytes:  {format_bytes(sum_file_sizes(srcs))}',
    ])

    return srcs, dsts


def get_paths_onload(roll_ext, function):
    srcs = []

    db.d('[A]', 'get_paths_onload() collecting source files', [
        f'roll:      {roll_ext.index_str}',
        f'mode:      {function}',
        f'source dir: {roll_ext.directory}',
        f'dst root:   {PATH_LOCAL}',
    ])

    if function is None or function.lower() == 'all':
        jpgs = get_jpg_files(roll_ext)
        raws = get_raw_files(roll_ext)
        previews = []
        # previews = get_preview_files(roll_ext)

        srcs.extend(jpgs)
        srcs.extend(raws)
        # srcs.extend(previews)


    elif function.lower() == 'jpg':
        jpgs = get_jpg_files(roll_ext)
        srcs.extend(jpgs)

    elif function.lower() == 'raw':
        raws = get_raw_files(roll_ext)
        srcs.extend(raws)

    elif function.lower() == 'previews':
        previews = get_preview_files(roll_ext)
        srcs.extend(previews)

    else:
        db.e('[A]', 'Unknown onload mode:', function)
        return 0, 0

    if len(srcs) == 0:
        db.i('[A]', 'get_paths_onload(): no source files found', [
            f'roll: {roll_ext.index_str}',
            f'mode: {function}',
        ])
        return [], []

    dsts = []
    for src in srcs:
        rel_path = os.path.relpath(src, PATH_EXTERNAL)
        dst = os.path.join(PATH_LOCAL, rel_path)
        dsts.append(dst)

    db.d('[A]', 'get_paths_onload() built path lists', [
        f'roll:      {roll_ext.index_str}',
        f'mode:      {function}',
        f'src count:  {len(srcs)}',
        f'dst count:  {len(dsts)}',
        f'src bytes:  {format_bytes(sum_file_sizes(srcs))}',
    ])

    return srcs, dsts


# Ensure src file matches to dst filename
def match_paths(srcs, dsts):
    if srcs == 0 or dsts == 0:
        db.e('[A]', 'Source or Destination path list is invalid!')
        return 0

    if len(srcs) != len(dsts):
        db.e('[A]', 'Source and destination path list lengths do not match!', [
            f'len(srcs): {len(srcs)}',
            f'len(dsts): {len(dsts)}',
        ])
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
    try:
        src_size = os.path.getsize(src) if os.path.exists(src) else 0
    except Exception:
        src_size = 0

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    db.d('[A]', 'Copied:', f'{src} -> {dst}')
    return


# Copy file from src to dst and then del src
def copy_delete(src, dst):
    try:
        src_size = os.path.getsize(src) if os.path.exists(src) else 0
    except Exception:
        src_size = 0

    try:
        copy_file(src, dst)
    except Exception as e:
        db.e('[A]', 'Copy failed:', e)
        return

    if DEBUG:
        try:
            # copy src to temp folder before deleting for safety: path = PATH_DEBUG/tree2/tree1/img_file.jpg
            debug_dst = os.path.join(PATH_DEBUG, os.path.relpath(src, PATH_LOCAL))
            os.makedirs(os.path.dirname(debug_dst), exist_ok=True)
            shutil.copy2(src, debug_dst)
            db.d('[A]', 'Saved before del to:', debug_dst)
        except Exception as e:
            db.e('[A]', 'Debug copy failed:', e)
            return

    try:
        os.remove(src)
        db.d('[A]', 'Deleted:', src)
    except Exception as e:
        db.e('[A]', 'Delete failed:', e)

    return


# Move a file from src to dst: no copy needed if dst exists
def move_file(src, dst):
    try:
        src_size = os.path.getsize(src) if os.path.exists(src) else 0
    except Exception:
        src_size = 0

    try:
        if os.path.exists(dst):
            db.d('[A]', 'Destination exists, removing source:', src)

            if DEBUG:
                try:
                    # copy src to temp folder before deleting for safety: path = PATH_DEBUG/tree2/tree1/img_file.jpg
                    debug_dst = os.path.join(PATH_DEBUG, os.path.relpath(src, PATH_LOCAL))
                    os.makedirs(os.path.dirname(debug_dst), exist_ok=True)
                    shutil.copy2(src, debug_dst)
                    db.d('[A]', 'Saved before del to:', debug_dst)
                except Exception as e:
                    db.e('[A]', 'Debug copy failed:', e)
                    return

            os.remove(src)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            db.d('[A]', 'Moved:', f'{src} -> {dst}')
            db.i('[A]', 'move_file() move path complete', [
                f'moved: {src} -> {dst}',
                f'size:  {format_bytes(src_size)}',
            ])
    except Exception as e:
        db.e('[A]', 'Move failed:', e)
    return


def get_raw_files(roll):
    rawPaths = []

    if roll.rawDirs == [-1] or roll.rawDirs is None:
        db.d('[A]', 'get_raw_files(): no raw dirs', [
            f'roll: {roll.index_str}',
            f'rawDirs: {roll.rawDirs}',
        ])
        return rawPaths

    for dir in roll.rawDirs:
        if not os.path.exists(dir):
            db.w('[A]', 'RAW dir missing on disk', dir)
            continue
        for file in os.listdir(dir):
            rawPaths.append(os.path.join(dir, file))

    # if roll.countRaw is not None and len(rawPaths) != roll.countRaw:
    #     db.w('[A]', f'RAW path count does not match RAW count on roll {roll.index_str}', f'expected: {roll.countRaw}, found: {len(rawPaths)}')

    db.d('[A]', 'get_raw_files() summary', [
        f'roll:      {roll.index_str}',
        f'file count: {len(rawPaths)}',
        f'total size: {format_bytes(sum_file_sizes(rawPaths))}',
    ])

    return rawPaths


def get_jpg_files(roll):
    jpgPaths = []

    if roll.jpgDirs is None:
        db.i('[A]', 'get_jpg_files(): no jpg dirs', [
            f'roll: {roll.index_str}',
            f'jpgDirs: {roll.jpgDirs}',
        ])
        return jpgPaths

    for dir in roll.jpgDirs:
        if not os.path.exists(dir):
            db.w('[A]', 'JPG dir missing on disk', dir)
            continue
        for file in os.listdir(dir):
            jpgPaths.append(os.path.join(dir, file))

    if roll.countJpg is not None and len(jpgPaths) != roll.countJpg:
        db.w('[A]', f'JPG path count does not match JPG count on roll {roll.index_str}', f'expected: {roll.countJpg}, found: {len(jpgPaths)}')

    db.d('[A]', 'get_jpg_files() summary', [
        f'roll:      {roll.index_str}',
        f'file count: {len(jpgPaths)}',
        f'total size: {format_bytes(sum_file_sizes(jpgPaths))}',
    ])

    return jpgPaths


def get_preview_files(roll):
    previewPaths = []
    dir = os.path.join(roll.directory, '03_previews')

    if not os.path.exists(dir):
        db.i('[A]', 'get_preview_files(): preview dir missing', [
            f'roll: {roll.index_str}',
            f'dir:  {dir}',
        ])
        return previewPaths

    for file in os.listdir(dir):
        previewPaths.append(os.path.join(dir, file))

    db.d('[A]', 'get_preview_files() summary', [
        f'roll:      {roll.index_str}',
        f'file count: {len(previewPaths)}',
        f'total size: {format_bytes(sum_file_sizes(previewPaths))}',
    ])

    return previewPaths


def format_bytes(num_bytes):
    if num_bytes is None:
        return '0 B'

    sign = '-' if num_bytes < 0 else ''
    size = abs(float(num_bytes))
    units = ['B', 'KB', 'MB', 'GB', 'TB']

    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == 'B':
                return f'{sign}{int(size)} {unit}'
            return f'{sign}{size:.2f} {unit}'
        size /= 1024.0


def safe_getsize(path):
    try:
        if os.path.exists(path):
            return os.path.getsize(path)
    except Exception:
        pass
    return 0


def sum_file_sizes(paths):
    total = 0
    for path in paths:
        total += safe_getsize(path)
    return total


def summarize_pairs(pairs):
    summary = {
        'total_files': 0,
        'total_src_bytes': 0,
        'copy_delete_count': 0,
        'copy_delete_bytes': 0,
        'delete_only_count': 0,
        'delete_only_bytes': 0,
        'dst_older_count': 0,
        'dst_older_bytes': 0,
        'missing_dst_count': 0,
        'dst_exists_count': 0,
    }

    for pair in pairs:
        src, dst = pair
        src_size = safe_getsize(src)
        status = check_pair(pair)

        summary['total_files'] += 1
        summary['total_src_bytes'] += src_size

        if status == 0:
            summary['missing_dst_count'] += 1
            summary['copy_delete_count'] += 1
            summary['copy_delete_bytes'] += src_size

        elif status == 1:
            summary['dst_exists_count'] += 1
            summary['delete_only_count'] += 1
            summary['delete_only_bytes'] += src_size

        elif status == -1:
            summary['dst_exists_count'] += 1
            summary['dst_older_count'] += 1
            summary['dst_older_bytes'] += src_size
            summary['copy_delete_count'] += 1
            summary['copy_delete_bytes'] += src_size

    return summary


if __name__ == "__main__":
    main()