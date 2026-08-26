# cleanRoll.py
#
# Interactively pick a single roll folder (native Finder dialog), choose which
# clean steps to run, and clean it -- IN PLACE at its current location when its
# folder structure already matches the expected 01_scans/02_exports layout,
# or exported to a separate library path (like the old behaviour) when it
# doesn't.
#
# Why in-place: Lightroom is pointed directly at a roll's existing folder.
# Exporting/copying everything to a brand-new location elsewhere (the old
# behaviour, still used by main.py's batch mode via importTool.cleanRoll())
# leaves Lightroom pointing at files that no longer represent the "clean"
# output -- every photo would show as missing until manually relinked, one by
# one, from scratch. A folder RENAME within the same parent directory is fine
# though: Lightroom can relink a rename in one step (folder contents/paths
# otherwise unchanged), so that's the only structural change made here.
#
# Usage:
#   python cleanRoll.py
#
# A Finder dialog opens; select the roll folder (the one containing
# 01_scans/02_exports/... or an older/legacy layout). The roll is parsed the
# same way the rest of the pipeline parses any roll.
#
#   - If the folder already matches the expected layout (01_scans/02_exports),
#     it's cleaned in place: renamed to the standard naming convention if
#     needed (same parent directory, contents untouched by the rename itself),
#     then cleaned via importTool.cleanRoll_in_place().
#   - If it doesn't match, cleaning in place isn't safe (nothing to build
#     01_scans/02_exports out of predictably) -- you're prompted whether to
#     export it to a separate library path instead, the way cleanRoll() always
#     has, defaulting to newRoll.py's own staging path. 

import json
import os
import re
import shutil
import subprocess
import sys

from datetime import datetime

from tkinter import Tk
from tkinter.filedialog import askdirectory

import collectionObj
import importTool
import debuggerTool
from newRoll import LIBRARY_PATH as DEFAULT_EXPORT_PATH

DEBUG = 0
WARNING = 1
ERROR = 1
db = debuggerTool.debuggerTool(DEBUG, WARNING, ERROR)

ROLL_FOLDER_ROOT = '/Users/rja/Photography/0_Working'
# Roll folders live one level down inside a category folder under
# ROLL_FOLDER_ROOT (eg. '1_Imports/011_26-08-08_G200_P6X7_Cedar Breaks' or
# '5_done/...'), and are always named starting with an integer index.
ROLL_NAME_RE = re.compile(r'^\d+_')
LR_EXPORTS_ROOT = '/Users/rja/Desktop/export'
VALID_EXPORT_EXTS = ('.jpg', '.jpeg', '.png')
BATCH_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
# Files exported more than this many seconds apart are treated as separate
# export batches, even when they live in the same folder (eg. loose files
# dropped directly in LR_EXPORTS_ROOT from unrelated export sessions).
BATCH_TIME_GAP_SECONDS = 600


def pick_roll_folder():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    kwargs = {'title': 'Select the roll folder to clean'}
    if os.path.isdir(ROLL_FOLDER_ROOT):
        kwargs['initialdir'] = ROLL_FOLDER_ROOT
    folder = askdirectory(**kwargs)
    root.destroy()
    return folder or None


def pick_lr_exports_folder(initialdir=None):
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    kwargs = {'title': 'Select the fresh Lightroom exports folder'}
    if initialdir and os.path.isdir(initialdir):
        kwargs['initialdir'] = initialdir
    folder = askdirectory(**kwargs)
    root.destroy()
    return folder or None


def _scan_batch(path, recursive, valid_exts):
    """Returns [(filename, mtime), ...] for image files directly in path
    (recursive=False) or anywhere under it (recursive=True)."""
    files = []
    walker = os.walk(path) if recursive else [(path, [], os.listdir(path))]
    for dirpath, _, filenames in walker:
        for f in filenames:
            if not f.lower().endswith(valid_exts) or f.startswith('._'):
                continue
            mtime = os.path.getmtime(os.path.join(dirpath, f))
            files.append((f, mtime))
    return files


def cluster_by_time(files, gap_seconds=BATCH_TIME_GAP_SECONDS):
    """
    Splits [(filename, mtime), ...] into export batches: sorted newest-first,
    a new batch starts wherever the gap to the next-newest file exceeds
    gap_seconds. Returns a list of batches (each a list of (filename,
    mtime)), most recent batch first. Files exported within the same
    Lightroom session land in one batch even if a folder mixes several
    sessions' loose files together.
    """
    if not files:
        return []
    ordered = sorted(files, key=lambda e: e[1], reverse=True)
    clusters = [[ordered[0]]]
    for entry in ordered[1:]:
        if clusters[-1][-1][1] - entry[1] <= gap_seconds:
            clusters[-1].append(entry)
        else:
            clusters.append([entry])
    return clusters


def find_most_recent_batch(export_root, valid_exts=VALID_EXPORT_EXTS):
    """
    Groups files under export_root by location -- the loose files sitting
    directly in export_root form one location, and each immediate
    subdirectory (Lightroom's own numbered re-export folders) forms another
    -- and returns the location with the most recently modified file, as
    (path, files, latest_mtime) where files is [(filename, mtime), ...] for
    every image file in that location. Returns None if export_root doesn't
    exist or has no image files anywhere.

    A single location can still mix multiple time-separated export batches
    (eg. loose files from several unrelated sessions sitting directly in
    export_root) -- use cluster_by_time() on the returned files to split
    those apart for display/confirmation.
    """
    if not os.path.isdir(export_root):
        return None

    locations = []

    files = _scan_batch(export_root, recursive=False, valid_exts=valid_exts)
    if files:
        locations.append((max(m for _, m in files), export_root, files))

    for entry in os.scandir(export_root):
        if entry.is_dir():
            files = _scan_batch(entry.path, recursive=True, valid_exts=valid_exts)
            if files:
                locations.append((max(m for _, m in files), entry.path, files))

    if not locations:
        return None

    latest, path, files = max(locations, key=lambda b: b[0])
    return path, files, latest


def iter_roll_folders(search_root=ROLL_FOLDER_ROOT):
    """
    Yields every roll folder under search_root: one level down inside each
    category folder (eg. '1_Imports', '5_done'), matching only folders
    whose name starts with an integer index (eg.
    '011_26-08-08_G200_P6X7_Cedar Breaks') -- ie. actual roll folders, not
    stray files or non-roll subfolders a category folder might contain.
    """
    if not os.path.isdir(search_root):
        return
    for category in os.scandir(search_root):
        if not category.is_dir():
            continue
        for roll in os.scandir(category.path):
            if roll.is_dir() and ROLL_NAME_RE.match(roll.name):
                yield roll.path


def get_preserved_raw_filenames(file_paths):
    """
    Reads each JPG's embedded XMP-xmpMM:PreservedFileName tag via exiftool
    -- the original RAW file's basename, written by Negative Lab Pro at
    export time (see exposureObj._update_from_exif(), which relies on the
    same tag). The export's own filenames are human-renamed (eg. '25-07-11
    - 01 - Cedar Breaks - ... .jpg') and carry no relation to the RAW
    basenames, so this is the only reliable way to identify the source RAW.
    Returns {file_path: raw_filename_or_None}, or {} if exiftool isn't
    available or file_paths is empty.
    """
    if not file_paths or not shutil.which('exiftool'):
        return {}
    cmd = ['exiftool', '-j', '-fast2', '-SourceFile', '-XMP-xmpMM:PreservedFileName'] + file_paths
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    try:
        data = json.loads(result.stdout or '[]')
    except json.JSONDecodeError:
        return {}
    return {entry.get('SourceFile'): entry.get('PreservedFileName') for entry in data}


def find_matching_roll(batch_dir, batch_files, search_root=ROLL_FOLDER_ROOT):
    """
    Given the JPGs in a freshly-detected export batch, reads the original
    RAW basename out of each one's PreservedFileName EXIF tag (see
    get_preserved_raw_filenames()), then searches every roll folder under
    search_root (see iter_roll_folders()) for RAW files in 01_scans whose
    basename matches. Returns the best-matching roll folder path, or None
    if no PreservedFileName tags were found or no roll's RAW files overlap
    with the batch at all.
    """
    file_paths = [os.path.join(batch_dir, f) for f, _ in batch_files]
    preserved = get_preserved_raw_filenames(file_paths)
    raw_basenames = {os.path.basename(n) for n in preserved.values() if n}
    if not raw_basenames:
        db.w('[C]', 'No PreservedFileName EXIF tags found in export batch -- cannot match a roll automatically.')
        return None

    best_path, best_count = None, 0
    for roll_path in iter_roll_folders(search_root):
        scans_path = os.path.join(roll_path, '01_scans')
        if not os.path.isdir(scans_path):
            continue
        scan_names = {f for f in os.listdir(scans_path) if not f.startswith('._')}
        overlap = len(raw_basenames & scan_names)
        if overlap > best_count:
            best_path, best_count = roll_path, overlap

    return best_path


def prompt_yes_no(question, default=True):
    suffix = '[Y/n]' if default else '[y/N]'
    raw = input(f'{question} {suffix} ').strip().lower()
    if raw == '':
        return default
    return raw in ('y', 'yes')


def prompt_clean_steps():
    print('\nWhich clean steps should run?')
    return {
        'clean_raw': prompt_yes_no('  Copy/rename RAW files?'),
        'clean_jpg': prompt_yes_no('  Copy/rename JPG exports?'),
        'clean_preview': prompt_yes_no('  Build previews?'),
        'clean_edits': prompt_yes_no('  Copy/rename edits (virtual copies)?'),
        'clean_contact_sheet': prompt_yes_no('  Build contact sheets?'),
        'clean_exif': prompt_yes_no('  Export EXIF JSON?'),
    }


def prompt_export_path(default_path):
    raw = input(f'Export path [{default_path}]: ').strip()
    return raw or default_path


def pick_lr_export_batch():
    """
    Detects the most recent Lightroom export batch under LR_EXPORTS_ROOT and
    confirms it with the user (falling back to a manual folder picker if
    none is found or the detected one is rejected). Returns
    (lr_exports_folder, lr_exports_filenames, batch_files) where
    lr_exports_filenames is None when the folder was picked manually
    (meaning "use everything in it") and batch_files is the raw
    [(filename, mtime), ...] list for the chosen batch (empty when picked
    manually, since roll-matching has nothing to go on in that case).
    """
    detected = find_most_recent_batch(LR_EXPORTS_ROOT)
    if not detected:
        db.w('[C]', 'No export batches found under', LR_EXPORTS_ROOT)
        return pick_lr_exports_folder(initialdir=LR_EXPORTS_ROOT), None, []

    batch_path, batch_files, batch_mtime = detected
    clusters = cluster_by_time(batch_files)
    most_recent = clusters[0]
    when = datetime.fromtimestamp(batch_mtime).strftime(BATCH_TIME_FORMAT)

    print(f'\nMost recent export location detected:')
    print(f'  {batch_path}')
    print(f'  {len(batch_files)} image files total, last modified {when}')
    print(f'  {len(clusters)} export batch{"es" if len(clusters) != 1 else ""} identified by time (>{BATCH_TIME_GAP_SECONDS // 60}min gap)')
    print(f'\nMost recent batch ({len(most_recent)} files):')
    for f, _ in sorted(most_recent):
        print(f'  {f}')
    if len(clusters) > 1:
        print(f'\nNote: this folder mixes {len(clusters)} time-separated batches -- if you '
              f'only want the most recent one, clean up the older files before continuing.')

    if prompt_yes_no('Use this as the fresh exports batch?', default=True):
        # Only the most recent time-cluster, even if batch_path (eg. loose
        # files in LR_EXPORTS_ROOT) also holds older, unrelated batches.
        return batch_path, [f for f, _ in most_recent], most_recent

    return pick_lr_exports_folder(initialdir=LR_EXPORTS_ROOT), None, []


def apply_lr_exports_sync(importer, folder, lr_exports_folder, lr_exports_filenames):
    """
    Refreshes folder/02_exports (and clears folder/04_edits) from an
    already-chosen Lightroom exports folder, so the roll parses the CURRENT
    Lightroom state -- stale/renamed/deleted VCs from a previous clean don't
    linger. Only applies to a roll that already has an 02_exports folder
    (an already-cleaned/in-place roll being refreshed).
    """
    exports_path = os.path.join(folder, '02_exports')
    edits_path = os.path.join(folder, '04_edits')

    if not os.path.isdir(exports_path):
        db.w('[C]', 'No existing 02_exports folder -- skipping LR-exports sync.', folder)
        return

    if not lr_exports_folder:
        db.w('[C]', 'No LR-exports folder selected, skipping sync.')
        return
    lr_exports_folder = os.path.normpath(lr_exports_folder)

    # Guard against wiping the roll's own exports using itself (or its
    # parent) as the "fresh" source.
    real_folder = os.path.realpath(folder)
    real_lr = os.path.realpath(lr_exports_folder)
    if real_lr == real_folder or real_lr.startswith(real_folder + os.sep) or real_folder.startswith(real_lr + os.sep):
        db.e('[C]', 'LR-exports folder overlaps the roll folder, aborting sync to avoid data loss:', lr_exports_folder)
        return

    if lr_exports_filenames is not None:
        new_count = len([f for f in lr_exports_filenames
                          if f.lower().endswith(VALID_EXPORT_EXTS) and not f.startswith('._')])
    else:
        new_count = len([f for f in os.listdir(lr_exports_folder)
                          if f.lower().endswith(VALID_EXPORT_EXTS) and not f.startswith('._')])
    if new_count == 0:
        db.e('[C]', 'No image files found in LR-exports folder, aborting sync:', lr_exports_folder)
        return

    old_exports_count = len(os.listdir(exports_path)) if os.path.isdir(exports_path) else 0
    old_edits_count = len(os.listdir(edits_path)) if os.path.isdir(edits_path) else 0

    print(f'\nThis will replace the contents of 02_exports and 04_edits:')
    print(f'  02_exports: {old_exports_count} existing files -> {new_count} fresh files from {lr_exports_folder}')
    print(f'  04_edits:   {old_edits_count} existing files -> rebuilt from the fresh exports')

    if not prompt_yes_no('Proceed with sync? This deletes the files listed above.', default=False):
        db.w('[C]', 'Cancelled by user.')
        return

    # 04_edits must be cleared BEFORE the roll is parsed: process_images()
    # scans 04_edits into roll.images before process_copies() groups
    # copies by dateExposed, so stale 04_edits content would corrupt VC
    # grouping on this run.
    importer.clear_folder(edits_path)
    importer.sync_folder_from_source(lr_exports_folder, exports_path, extensions=VALID_EXPORT_EXTS, filenames=lr_exports_filenames)
    db.i('[C]', f'Synced {new_count} files from LR-exports into 02_exports.', exports_path)


def clean_in_place(collection, importer, roll, folder, steps):
    new_name = roll.newName
    current_name = os.path.basename(folder)
    target_path = os.path.join(os.path.dirname(folder), new_name)

    if new_name != current_name:
        print(f'\nFolder will be renamed:\n  {current_name}\n  -> {new_name}')
        print(f'(same location -- only the folder name changes: {os.path.dirname(folder)})')

        if not prompt_yes_no('Proceed with rename + in-place clean?'):
            db.w(roll.dbIdx, 'Cancelled by user.')
            return

        if os.path.exists(target_path):
            db.e(roll.dbIdx, 'Rename target already exists, aborting to avoid overwriting it:', target_path)
            return

        os.rename(folder, target_path)
        db.i(roll.dbIdx, 'Renamed folder', f'{folder} -> {target_path}')

        # Every path the roll/exposure objects hold (img.filePath,
        # img.rawFilePath, etc.) was resolved against the OLD directory string
        # and is now stale -- re-parsing from the renamed location is simpler
        # and safer than trying to patch every stored path in place.
        roll = collection.import_roll_from_path(target_path)
        if roll is None:
            db.e('[C]', 'Failed to re-import roll after rename.', target_path)
            return
    else:
        if not prompt_yes_no(f'Clean this roll in place at {folder}?'):
            db.w(roll.dbIdx, 'Cancelled by user.')
            return

    importer.cleanRoll_in_place(roll, **steps)


def clean_to_export_path(importer, roll, steps):
    print('\nThis folder does not match the expected 01_scans/02_exports layout.')
    print("It can't be safely cleaned in place.")

    if not prompt_yes_no('Export this roll to a separate library path instead?', default=False):
        db.w(roll.dbIdx, 'Cancelled by user.')
        return

    export_path = prompt_export_path(DEFAULT_EXPORT_PATH)

    if not prompt_yes_no(f'[{roll.index_str}] Clean this roll into {export_path}?'):
        db.w(roll.dbIdx, 'Cancelled by user.')
        return

    importer.cleanRoll(roll, library_path=export_path, **steps)


def main():
    importer = importTool.importTool()

    lr_exports_folder = None
    lr_exports_filenames = None

    if prompt_yes_no('Import fresh JPG exports from the export folder?', default=True):
        lr_exports_folder, lr_exports_filenames, batch_files = pick_lr_export_batch()

        folder = None
        if batch_files:
            matched_folder = find_matching_roll(lr_exports_folder, batch_files)
            if matched_folder:
                print(f'\nMatching roll folder found:\n  {matched_folder}')
                if prompt_yes_no('Use this roll?', default=True):
                    folder = matched_folder
            else:
                db.w('[C]', 'No matching roll folder found under', ROLL_FOLDER_ROOT)

        if not folder:
            folder = pick_roll_folder()
    else:
        folder = pick_roll_folder()

    if not folder:
        db.w('[C]', 'No folder selected, aborting.')
        return

    folder = os.path.normpath(folder)
    db.i('[C]', 'Selected roll folder:', folder)

    # collectionObj only needs *a* directory to build its stocklist/cameralist
    # lookups (those load from this project's own data/ folder, not from the
    # library path) -- it is not used to scan the whole library for a
    # single-roll clean.
    collection = collectionObj.collectionObj(os.path.dirname(folder))

    if lr_exports_folder:
        apply_lr_exports_sync(importer, folder, lr_exports_folder, lr_exports_filenames)

    roll = collection.import_roll_from_path(folder)
    if roll is None:
        db.e('[C]', 'Failed to import roll from selected folder.', folder)
        return

    db.i(roll.dbIdx, 'Roll imported', [
        f'name:       {roll.name}',
        f'newName:    {roll.newName}',
        f'stk:        {roll.stk}',
        f'cam:        {roll.cam}',
        f'exposures:  {roll.countExposures}',
        f'copies:     {roll.countCopies}',
        f'raw:        {roll.countRaw}',
        f'structure:  {"valid (01_scans/02_exports layout)" if roll.isNewCollection else "NOT recognized -- legacy/unexpected layout"}',
    ])

    steps = prompt_clean_steps()

    if roll.isNewCollection:
        clean_in_place(collection, importer, roll, folder, steps)
    else:
        clean_to_export_path(importer, roll, steps)


if __name__ == '__main__':
    main()
