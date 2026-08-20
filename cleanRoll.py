# cleanRoll.py
#
# Interactively pick a single roll folder (native Finder dialog) and run the standard
# cleanRoll() pipeline (raw/jpg copy, previews, contact sheets, exif export) on just that
# roll -- instead of the batch "loop over collection.rolls" that main.py does.
#
# Usage:
#   python cleanRoll.py
#
# A Finder dialog opens; select the roll folder (the one containing 01_scans/02_exports/...).
# The roll is parsed the same way the rest of the pipeline parses any roll, then cleaned into
# LIBRARY_CLEAN below (edit this constant, same convention as main.py / archiver.py).

import os
import sys

from tkinter import Tk
from tkinter.filedialog import askdirectory

import collectionObj
import importTool
import debuggerTool

DEBUG = 0
WARNING = 1
ERROR = 1
db = debuggerTool.debuggerTool(DEBUG, WARNING, ERROR)

# Destination for the cleaned/archived roll. Matches the default library_clean used
# elsewhere (main.py / importTool.cleanRoll's own default). Edit as needed.
LIBRARY_CLEAN = r'/Users/rja/Photography/Temporary'


def pick_roll_folder():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    folder = askdirectory(title='Select the roll folder to clean')
    root.destroy()
    return folder or None


def main():
    folder = pick_roll_folder()
    if not folder:
        db.w('[C]', 'No folder selected, aborting.')
        return

    folder = os.path.normpath(folder)
    db.i('[C]', 'Selected roll folder:', folder)

    # collectionObj only needs *a* directory to build its stocklist/cameralist lookups
    # (those load from this project's own data/ folder, not from the library path) --
    # it is not used to scan the whole library for a single-roll clean.
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
    ])

    confirm = input(f'[{roll.index_str}] Clean this roll into {LIBRARY_CLEAN}? [Y/n] ').strip().lower()
    if confirm not in ('', 'y', 'yes'):
        db.w(roll.dbIdx, 'Cancelled by user.')
        return

    importer.cleanRoll(roll, library_path=LIBRARY_CLEAN)


if __name__ == '__main__':
    main()
