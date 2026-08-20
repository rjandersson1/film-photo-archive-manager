# importMetadata.py
#
# Applies per-frame metadata from a roll's {roll}_metadata.xlsx (built by newRoll.py)
# into Lightroom, via lrplugin-dev/metadataTool.py's existing GUI-automation pipeline.
#
# Why this exists: metadataTool.py applies rows POSITIONALLY -- it tabs through whatever
# photos are currently selected in Lightroom's filmstrip, in order, pasting row 1's data
# onto the 1st selected photo, row 2's onto the 2nd, etc. If you delete bad scans/dupes
# during editing after newRoll.py already generated the xlsx, the row count and the actual
# raw file count drift apart, and the automation will silently paste the WRONG frame's
# metadata onto a photo. There's no undo for that once it's written into Lightroom, so this
# refuses to run the automation on any mismatch, and offers to auto-fix the (disposable,
# easily regenerated) xlsx instead -- Lightroom itself is never touched until the two are
# confirmed to match.
#
# Workflow:
#   1) prompt for roll index (same LIBRARY_PATH/index convention as newRoll.py) to pick
#      the roll folder to work on
#   2) SAFEGUARD: reconcile the xlsx's rawFileName rows against what's actually still in
#      01_scans right now
#   3) hand off to lrplugin-dev/metadataTool.py for the actual Lightroom automation
#
# Usage:
#   python importMetadata.py

import os
import importlib.util

from openpyxl import load_workbook, Workbook

import collectionObj
from newRoll import LIBRARY_PATH, RAW_EXTS, METADATA_COLUMNS, list_raw_files


def find_roll_folder(library_path, index):
    index_str = str(index).zfill(3)
    matches = []
    if os.path.isdir(library_path):
        for name in sorted(os.listdir(library_path)):
            if name.startswith('.'):
                continue
            full = os.path.join(library_path, name)
            if not os.path.isdir(full):
                continue
            token = name.split('_')[0] if '_' in name else name.split(' - ')[0]
            token = token.strip()
            if token == index_str or (token.isdigit() and int(token) == index):
                matches.append(full)
    return matches


def prompt_roll_folder():
    while True:
        raw = input('Roll index: ').strip()
        if not raw.isdigit():
            print('Enter a numeric roll index.')
            continue
        index = int(raw)
        matches = find_roll_folder(LIBRARY_PATH, index)
        if len(matches) == 1:
            return matches[0], index
        if len(matches) == 0:
            print(f'No roll folder found for index {index} in {LIBRARY_PATH}')
            continue
        print(f'Multiple folders matched index {index}:')
        for m in matches:
            print(f'  {m}')
        print('Rename/clean up so only one folder matches, then retry.')


def find_metadata_xlsx(roll_root):
    candidates = [f for f in os.listdir(roll_root) if f.lower().endswith('_metadata.xlsx')]
    if len(candidates) == 0:
        return None
    if len(candidates) > 1:
        print(f'Multiple *_metadata.xlsx files found in {roll_root}: {candidates}')
        print('Leave only one and retry.')
        return None
    return os.path.join(roll_root, candidates[0])


# -------- Safeguard: reconcile xlsx rows against what's actually on disk now --------

def read_xlsx_rows(xlsx_path):
    wb = load_workbook(xlsx_path)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[1] is None:  # rawFileName
            continue
        rows.append(row)
    return wb, ws, rows


def reconcile(xlsx_path, scans_path):
    _, _, rows = read_xlsx_rows(xlsx_path)
    xlsx_files = {row[1] for row in rows}
    disk_files = set(list_raw_files(scans_path))

    missing_on_disk = sorted(xlsx_files - disk_files)   # rows referencing deleted/renamed raws
    missing_in_xlsx = sorted(disk_files - xlsx_files)   # raws with no row (rescans, renames)

    return missing_on_disk, missing_in_xlsx, len(xlsx_files), len(disk_files)


def parse_roll_tokens(roll_root):
    # folder name convention (see newRoll.py): {index}_{date}_{STK}_{CAM}_{Name...}
    name = os.path.basename(roll_root.rstrip('/'))
    parts = name.split('_')
    stk = parts[2] if len(parts) > 2 else None
    cam = parts[3] if len(parts) > 3 else None
    return stk, cam


def auto_fix_xlsx(xlsx_path, scans_path, roll_root, collection):
    """Drops rows whose raw file no longer exists, and appends rows for any raw files
    missing a row -- prefilled with Camera Make/Model + Film Stock/ISO the same way
    newRoll.py does, using the STK/CAM tokens parsed back out of the roll folder name.
    Never touches Lightroom -- this only rewrites the (disposable) xlsx."""
    wb, ws, rows = read_xlsx_rows(xlsx_path)
    disk_files = set(list_raw_files(scans_path))

    kept = [row for row in rows if row[1] in disk_files]
    kept_names = {row[1] for row in kept}
    new_names = sorted(disk_files - kept_names)

    stk_code, cam_id = parse_roll_tokens(roll_root)
    stk_entry = collection.stocklist.get(stk_code, {})
    cam_entry = {}
    for entry in collection.cameralist.values():
        if entry.get('id') == cam_id:
            cam_entry = entry
            break

    header = [cell.value for cell in ws[1]] or METADATA_COLUMNS

    new_wb = Workbook()
    new_ws = new_wb.active
    new_ws.title = 'Metadata'
    new_ws.append(header)

    combined = list(kept) + [
        (None, name, os.path.join(scans_path, name)) + (None,) * (len(header) - 3)
        for name in new_names
    ]
    # sort by rawFileName so row order matches how the files will sort in Lightroom's grid
    combined.sort(key=lambda r: r[1])

    for i, row in enumerate(combined, start=1):
        row = list(row)
        row[0] = i
        if row[1] in new_names:
            if len(row) > 12: row[12] = cam_entry.get('brand')   # Camera Make
            if len(row) > 13: row[13] = cam_entry.get('model')   # Camera Model
            if len(row) > 16: row[16] = stk_entry.get('stock')   # Film Stock
            if len(row) > 17: row[17] = stk_entry.get('boxspeed')  # Film ISO
        new_ws.append(row)

    new_wb.save(xlsx_path)
    print(f'Rewrote {xlsx_path}:')
    print(f'  kept:    {len(kept)}')
    print(f'  dropped: {len(rows) - len(kept)} stale row(s) (raw no longer on disk)')
    print(f'  added:   {len(new_names)} new row(s) (raw on disk with no row)')


def load_metadata_tool_class():
    spec_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lrplugin-dev', 'metadataTool.py')
    spec = importlib.util.spec_from_file_location('lr_metadata_tool', spec_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.metadataTool


def main():
    print(f'Importing metadata for library: {LIBRARY_PATH}')
    roll_root, index = prompt_roll_folder()
    scans_path = os.path.join(roll_root, '01_scans')

    xlsx_path = find_metadata_xlsx(roll_root)
    if xlsx_path is None:
        print(f'No *_metadata.xlsx found in {roll_root}. Run newRoll.py for this roll first.')
        return

    missing_on_disk, missing_in_xlsx, xlsx_count, disk_count = reconcile(xlsx_path, scans_path)

    if missing_on_disk or missing_in_xlsx:
        print(f'\n[{str(index).zfill(3)}] Metadata xlsx and 01_scans are out of sync:')
        print(f'  xlsx rows: {xlsx_count}')
        print(f'  raw files: {disk_count}')
        if missing_on_disk:
            print(f'  in xlsx but no longer on disk ({len(missing_on_disk)}): {missing_on_disk}')
        if missing_in_xlsx:
            print(f'  on disk but missing from xlsx ({len(missing_in_xlsx)}): {missing_in_xlsx}')

        print("\nApplying metadata positionally with a mismatch risks pasting the wrong")
        print("frame's data onto a photo in Lightroom. Refusing to proceed by default.")

        choice = input('Auto-fix the xlsx (drop stale rows / add missing rows) and re-check? [y/N] ').strip().lower()
        if choice not in ('y', 'yes'):
            print('Aborted. Lightroom was not touched. Fix the xlsx by hand and rerun.')
            return

        collection = collectionObj.collectionObj(LIBRARY_PATH)
        auto_fix_xlsx(xlsx_path, scans_path, roll_root, collection)

        missing_on_disk, missing_in_xlsx, xlsx_count, disk_count = reconcile(xlsx_path, scans_path)
        if missing_on_disk or missing_in_xlsx:
            print('Still mismatched after auto-fix -- aborting. Lightroom was not touched.')
            return

    print(f'\n[{str(index).zfill(3)}] xlsx and 01_scans match ({xlsx_count} files). Proceeding to Lightroom import.')
    print('Make sure the roll is open in Quick Collection, sorted by filename ascending, with all')
    print('frames selected before this continues.')
    input('Press Enter to start...')

    MetadataTool = load_metadata_tool_class()
    tool = MetadataTool(xlsx_path=xlsx_path, raw_folder=scans_path)
    tool.pause_field = False
    tool.pause_nextImage = False
    tool.run()


if __name__ == '__main__':
    main()
