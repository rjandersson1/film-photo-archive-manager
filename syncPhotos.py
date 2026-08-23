# syncPhotos.py
#
# Copies a chosen set of rolls' preview images and contact sheets out of a
# library folder (a folder containing roll folders directly, eg.
# '0_Working/05_Done' or a year folder under a library's 'film/library' tree)
# into three shared iCloud staging folders, so they show up on other devices
# without syncing the whole library. Purely filesystem-driven -- doesn't
# import rolls via collectionObj/rollObj (no EXIF/metadata parsing needed,
# just copying files that are already on disk under known subfolder names).
#
# For each selected roll folder ("{index}_..."):
#   1) roll/03_previews/*                       -> DEST_PREVIEWS
#   2) roll/*contact_sheet*.png (loose in roll)  -> DEST_CONTACT_MAIN
#   3) roll/05_other/02_contact_sheets/*         -> DEST_CONTACT_ALL
#
# Destination folders are MERGED into, never wiped -- they aggregate output
# from many rolls, so clearing them first (like importTool.sync_folder_from_source
# does for a single roll's own folder) would destroy every other roll's files
# already copied there. Existing files with the same name are overwritten,
# but only after the user is shown the count and file times per overwrite and
# confirms.
#
# Usage:
#   python syncPhotos.py
#
# A Finder dialog opens; select the library folder. Then enter which rolls to
# sync:
#   all
#   1-23        (roll 1 to roll 23, skipping any that don't exist)
#   1,3,4,5
#   1,3,5,10-32

import os
import shutil
from datetime import datetime

from tkinter import Tk
from tkinter.filedialog import askdirectory

import debuggerTool

DEBUG = 0
WARNING = 1
ERROR = 1
db = debuggerTool.debuggerTool(DEBUG, WARNING, ERROR)

DEFAULT_LIBRARY_ROOT = '/Users/rja/Photography/0_Working/5_Done'

DEST_PREVIEWS = '/Users/rja/Library/Mobile Documents/com~apple~CloudDocs/photography/temp/film'
DEST_CONTACT_MAIN = '/Users/rja/Library/Mobile Documents/com~apple~CloudDocs/photography/temp/contact sheets'
DEST_CONTACT_ALL = '/Users/rja/Library/Mobile Documents/com~apple~CloudDocs/photography/temp/contact sheets all'

PREVIEWS_SUBDIR = '03_previews'
CONTACT_ALL_SUBDIR = os.path.join('05_other', '02_contact_sheets')
IMAGE_EXTS = ('.png', '.jpg', '.jpeg')
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def pick_library_folder():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    kwargs = {'title': 'Select the library folder containing roll folders'}
    if os.path.isdir(DEFAULT_LIBRARY_ROOT):
        kwargs['initialdir'] = DEFAULT_LIBRARY_ROOT
    folder = askdirectory(**kwargs)
    root.destroy()
    return folder or None


def prompt_yes_no(question, default=True):
    suffix = '[Y/n]' if default else '[y/N]'
    raw = input(f'{question} {suffix} ').strip().lower()
    if raw == '':
        return default
    return raw in ('y', 'yes')


def find_rolls(library_folder):
    """Returns {index: roll_folder_path} for every immediate subdirectory of
    library_folder whose name starts with '{int}_' (the roll-folder naming
    convention rollObj.process_directory() parses). Anything else (eg.
    .DS_Store, non-roll folders) is silently skipped."""
    rolls = {}
    for entry in sorted(os.scandir(library_folder), key=lambda e: e.name):
        if not entry.is_dir():
            continue
        try:
            index = int(entry.name.split('_')[0])
        except ValueError:
            continue
        rolls[index] = entry.path
    return rolls


def parse_roll_spec(spec, available):
    """Parses a roll-selection string ('all' / '1-23' / '1,3,4,5' /
    '1,3,5,10-32') into a sorted list of indices, intersected with
    `available` -- requested indices with no matching roll folder are
    dropped (reported by the caller), not treated as an error."""
    spec = spec.strip()
    if spec.lower() == 'all':
        return sorted(available)

    requested = set()
    for token in spec.split(','):
        token = token.strip()
        if not token:
            continue
        if '-' in token:
            start_str, end_str = token.split('-', 1)
            start, end = int(start_str.strip()), int(end_str.strip())
            if start > end:
                start, end = end, start
            requested.update(range(start, end + 1))
        else:
            requested.add(int(token))

    missing = sorted(requested - set(available))
    if missing:
        db.w('[S]', f'{len(missing)} requested roll(s) not found in library, skipping:', missing)

    return sorted(requested & set(available))


def prompt_roll_spec(available):
    while True:
        raw = input("\nWhich rolls should be synced? ('all', '1-23', '1,3,4,5', '1,3,5,10-32'): ").strip()
        try:
            indices = parse_roll_spec(raw, available)
        except ValueError:
            print(f'  Could not parse "{raw}" -- use a roll number, a comma list, or ranges like 10-32.')
            continue
        if not indices:
            print('  No matching rolls in the selected library -- try again.')
            continue
        return indices


def list_files(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(
        entry.name for entry in os.scandir(folder)
        if entry.is_file() and not entry.name.startswith('.') and not entry.name.startswith('~$')
    )


# Files this close in mtime are treated as "already synced" and skipped
# rather than re-copied -- guards against float/filesystem rounding (eg.
# iCloud's on-disk timestamp resolution) causing an identical file to be
# flagged as a spurious overwrite.
IDENTICAL_MTIME_TOLERANCE_SECONDS = 1.0


def already_synced(src, dst):
    if not os.path.exists(dst):
        return False
    return abs(os.path.getmtime(src) - os.path.getmtime(dst)) < IDENTICAL_MTIME_TOLERANCE_SECONDS


def build_sync_plan(roll_paths, indices):
    """Returns {'previews': [...], 'contact_main': [...], 'contact_all': [...]}
    where each list holds (roll_index, src_path, dst_path) tuples. Pairs
    whose destination already exists with an identical mtime are left out --
    those files are already in sync and don't need copying or an overwrite
    prompt; `skipped` reports how many of those were dropped, per category."""
    plan = {'previews': [], 'contact_main': [], 'contact_all': []}
    skipped = {'previews': 0, 'contact_main': 0, 'contact_all': 0}

    def add(category, index, src, dst):
        if already_synced(src, dst):
            skipped[category] += 1
        else:
            plan[category].append((index, src, dst))

    for index in indices:
        roll_folder = roll_paths[index]

        previews_src = os.path.join(roll_folder, PREVIEWS_SUBDIR)
        for fname in list_files(previews_src):
            add('previews', index, os.path.join(previews_src, fname), os.path.join(DEST_PREVIEWS, fname))

        contact_main_files = [
            f for f in list_files(roll_folder)
            if 'contact_sheet' in f.lower() and f.lower().endswith(IMAGE_EXTS)
        ]
        for fname in contact_main_files:
            add('contact_main', index, os.path.join(roll_folder, fname), os.path.join(DEST_CONTACT_MAIN, fname))

        contact_all_src = os.path.join(roll_folder, CONTACT_ALL_SUBDIR)
        for fname in list_files(contact_all_src):
            add('contact_all', index, os.path.join(contact_all_src, fname), os.path.join(DEST_CONTACT_ALL, fname))

    return plan, skipped


def find_overwrites(pairs):
    return [(index, src, dst) for index, src, dst in pairs if os.path.exists(dst)]


def format_mtime(path):
    return datetime.fromtimestamp(os.path.getmtime(path)).strftime(TIME_FORMAT)


CATEGORY_LABELS = {
    'previews': f'previews -> {DEST_PREVIEWS}',
    'contact_main': f'main contact sheets -> {DEST_CONTACT_MAIN}',
    'contact_all': f'all contact sheets -> {DEST_CONTACT_ALL}',
}


def review_plan(plan, skipped):
    """Prints a summary of the sync plan (counts + overwrite details) and
    asks for confirmation. Returns True to proceed."""
    total_files = sum(len(pairs) for pairs in plan.values())
    total_skipped = sum(skipped.values())
    if total_files == 0:
        if total_skipped:
            db.i('[S]', f'Nothing to sync -- all {total_skipped} file(s) already up to date.')
        else:
            db.w('[S]', 'No files found to sync for the selected rolls.')
        return False

    overwrites = {category: find_overwrites(pairs) for category, pairs in plan.items()}
    total_overwrites = sum(len(o) for o in overwrites.values())

    print('\nSync plan:')
    for category, pairs in plan.items():
        n_overwrite = len(overwrites[category])
        n_skipped = skipped[category]
        print(f'  {CATEGORY_LABELS[category]}')
        print(f'    {len(pairs)} file(s) to copy, {n_overwrite} would overwrite an existing file'
              + (f', {n_skipped} already up to date (skipped)' if n_skipped else ''))

    if total_overwrites == 0:
        return prompt_yes_no(f'\nCopy {total_files} file(s)?', default=True)

    print(f'\n{total_overwrites} existing file(s) will be OVERWRITTEN:')
    for category, entries in overwrites.items():
        if not entries:
            continue
        print(f'\n  {CATEGORY_LABELS[category]}:')
        for index, src, dst in sorted(entries, key=lambda e: (e[0], os.path.basename(e[2]))):
            print(f'    [{str(index).zfill(3)}] {os.path.basename(dst)}')
            print(f'          existing: {format_mtime(dst)}   incoming: {format_mtime(src)}')

    return prompt_yes_no(f'\nProceed and overwrite {total_overwrites} file(s) (of {total_files} total)?', default=False)


def execute_plan(plan):
    total = sum(len(pairs) for pairs in plan.values())
    progress_index = 0

    for category, pairs in plan.items():
        for index, src, dst in pairs:
            progress_index += 1
            db.progress(
                pre='[S]',
                current=progress_index,
                total=total,
                post=f'[{str(index).zfill(3)}] Copying {os.path.basename(dst)}',
                mode='info',
            )
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                db.e('[S]', f'Error copying {src} -> {dst}: {e}')

    db.s('[S]', f'Synced {total} file(s).')


def main():
    library_folder = pick_library_folder()
    if not library_folder:
        db.w('[S]', 'No library folder selected, aborting.')
        return
    library_folder = os.path.normpath(library_folder)

    roll_paths = find_rolls(library_folder)
    if not roll_paths:
        db.e('[S]', 'No roll folders found in selected library folder:', library_folder)
        return
    db.i('[S]', f'Found {len(roll_paths)} roll(s) in library folder:', library_folder)

    indices = prompt_roll_spec(sorted(roll_paths))
    db.i('[S]', f'Syncing {len(indices)} roll(s):', indices)

    plan, skipped = build_sync_plan(roll_paths, indices)

    if not review_plan(plan, skipped):
        db.w('[S]', 'Cancelled by user.')
        return

    execute_plan(plan)


if __name__ == '__main__':
    main()
