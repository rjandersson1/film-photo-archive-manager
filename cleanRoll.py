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

import os
import sys

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


def pick_roll_folder():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    folder = askdirectory(title='Select the roll folder to clean')
    root.destroy()
    return folder or None


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
    importer = importTool.importTool()

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
