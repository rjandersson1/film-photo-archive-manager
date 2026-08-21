# syncVCs.py
#
# Syncs the metadata that Importer.lua structurally CANNOT sync to virtual
# copies / stacked companions: custom third-party plugin fields (eg.
# Negative Lab Pro's Film Stock, Film ISO, Gear Notes, etc.). Lightroom's
# SDK scopes photo:setPropertyForPlugin() to the CALLING plugin's own
# identity -- our Importer.lua (com.rja.nlpimporter) has no way to write
# into NLP's own plugin-owned fields, and virtual copies have no XMP
# sidecar/file-level metadata of their own for a file-based workaround
# either (this is also why DateTimeOriginal/DateTime can't sync to VCs).
# There's also no SDK equivalent to Lightroom's own "Sync Metadata" feature
# (confirmed: no scriptable sync call exists), so this drives the real
# native UI instead, the same way metadataTool.py drives other menu actions.
#
# Scope: only ever the CURRENT Quick Collection selection for one roll (up
# to ~40 photos) -- never catalog-wide.
#
# Prerequisites -- all must be true before running this:
#   1. Run the roll's normal metadataTool.py / JSON Import pass FIRST.
#      That's what writes lrplugin-dev/vc_manifest.txt, which this script
#      reads to know exactly how many Shift+Right presses each stack needs.
#   2. In Lightroom, with the roll's Quick Collection photos selected:
#      Photo > Stacking > Expand All Stacks -- BEFORE adding them to Quick
#      Collection / before running this script. Sync Metadata only works
#      correctly on a fully expanded stack selection; a collapsed stack
#      silently syncs nothing but the top photo.
#   3. Configure Sync Metadata's checkboxes ONCE, by hand (Metadata > Sync
#      Metadata, tick whatever fields you want synced, eg. just the NLP
#      fields, then Synchronize). Lightroom remembers this choice between
#      invocations -- this script never touches the checkboxes itself, and
#      has no way to verify what's currently checked, so get this right
#      before running.
#   4. The FIRST photo in Quick Collection (sorted by filename) is the
#      currently selected/active photo in Lightroom's filmstrip before you
#      start -- this script assumes its starting position matches the
#      manifest's first entry.
#
# This hasn't been run end-to-end yet -- test on 1-2 stacks first (edit
# TEST_LIMIT below) rather than trusting a full ~40-photo roll on the first
# attempt, particularly the fixed delay between triggering Sync Metadata and
# pressing Enter (SYNC_DIALOG_DELAY below), which is a best guess, not yet
# confirmed against a real run.
#
# Usage:
#   python syncVCs.py

import time
import subprocess
import threading

from pathlib import Path
from pynput import keyboard
from pynput.keyboard import Controller, Key


class db:
    @staticmethod
    def d(msg):
        print(f"[DEBUG] {msg}")


SCRIPT_DIR = Path(__file__).parent
# /Users/rja/Documents/Coding/film-photo-archive-manager/lrplugin-dev/vc_manifest.txt
MANIFEST_PATH = SCRIPT_DIR / "lrplugin-dev" / "vc_manifest.txt"
# Set to a small number (eg. 2) to only process the first N stacks in the
# manifest, for a safe first test run. None processes everything.
TEST_LIMIT = None

DELAY_CONST = 0.3

DELAY_DEFAULT = DELAY_CONST + 0.05
DELAY_KEYPRESS = DELAY_CONST + 0.02
DELAY_MENU_STEP = DELAY_CONST + 0.2
DELAY_SHIFT_RIGHT = DELAY_CONST + 0.08
SYNC_DIALOG_DELAY = DELAY_CONST + 0.5
# Best-guess gap between triggering the Sync Metadata menu action and the
# dialog actually being ready for Enter -- NOT yet confirmed against a real
# run. If Enter fires before the dialog's up, it'll do nothing useful and
# the next stack's selection will be wrong. Increase this first if stacks
# start getting skipped/miscounted partway through a run.


class SyncVCs:

    def __init__(self):
        self.kb = Controller()
        self.stop_flag = False
        self.listener = keyboard.Listener(on_press=self._on_press)
        self.listener.start()

    def _on_press(self, key):
        if key == keyboard.Key.esc:
            if not self.stop_flag:
                print("\nESC pressed -- stopping.\n")
            self.stop_flag = True

    def press(self, key):

        key_map = {
            "left": Key.left,
            "right": Key.right,
            "enter": Key.enter,
            "esc": Key.esc,
        }

        k = key_map.get(key, key)

        self.kb.press(k)
        time.sleep(DELAY_KEYPRESS)
        self.kb.release(k)
        time.sleep(DELAY_DEFAULT)

    def hotkey(self, *keys):

        key_map = {
            "cmd": Key.cmd,
            "alt": Key.alt,
            "shift": Key.shift,
            "right": Key.right,
            "1": "1",
        }

        parsed = [key_map.get(k, k) for k in keys]

        for k in parsed[:-1]:
            self.kb.press(k)

        self.kb.press(parsed[-1])
        self.kb.release(parsed[-1])

        for k in reversed(parsed[:-1]):
            self.kb.release(k)

        time.sleep(DELAY_DEFAULT)

    def activate_lightroom(self):
        # pynput's Controller sends system-wide keystrokes to whatever app is
        # currently frontmost -- metadataTool.py gets away without this
        # because run() there begins only after the user has manually put
        # Lightroom frontmost (there's an explicit "make sure Lightroom is
        # ready" breakpoint before it starts). This script has no such
        # breakpoint: run from Terminal, Terminal is frontmost, and every
        # keystroke -- Cmd+Option+1, Shift+Right, Enter, b -- goes to
        # Terminal instead of Lightroom, doing nothing visible there. Must
        # run before the FIRST keystroke, not just before menu clicks
        # (which already activate Lightroom themselves via AppleScript).
        subprocess.run(
            ["osascript", "-e", 'tell application "Adobe Lightroom Classic" to activate'],
            capture_output=True,
            text=True
        )
        time.sleep(0.3)

    def ensure_library_module(self):
        # Matches metadataTool.py's ensure_library_module() -- Cmd+Option+1
        # is Lightroom Classic's fixed shortcut for "go to Library module"
        # regardless of which module is currently active; the Metadata menu
        # this script needs only exists in Library.
        self.hotkey("cmd", "alt", "1")
        time.sleep(0.5)

    def trigger_sync_metadata(self):
        # Confirmed to behave identically to the panel's Sync button.
        # Lightroom remembers the last-used checkbox selection in the
        # Synchronize Metadata dialog -- this never touches checkboxes
        # itself, see prerequisite #3 above.
        script = '''
        tell application "Adobe Lightroom Classic" to activate
        delay 0.2
        tell application "System Events"
            tell process "Adobe Lightroom Classic"
                click menu bar item "Metadata" of menu bar 1
                delay 0.2
                click menu item "Sync Metadata..." of menu 1 of menu bar item "Metadata" of menu bar 1
                delay 0.2
            end tell
        end tell
        '''

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("=" * 70)
            print("ERROR: Sync Metadata menu click failed.")
            print(result.stderr.strip())
            print("=" * 70)
            self.stop_flag = True
            return False

        return True

    def read_manifest(self):

        if not MANIFEST_PATH.exists():
            raise FileNotFoundError(
                f"{MANIFEST_PATH} not found -- run the roll's normal JSON Import "
                f"pass first (metadataTool.py). That's what writes this file."
            )

        mtime = MANIFEST_PATH.stat().st_mtime
        age_min = (time.time() - mtime) / 60
        print(f"Manifest last written {age_min:.1f} minutes ago.")

        entries = []

        for line in MANIFEST_PATH.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            fname, count_str = line.rsplit("\t", 1)
            entries.append((fname, int(count_str)))

        return entries

    def sync_stack(self, fname, copy_count):

        db.d(f"{fname}: extending selection by {copy_count} (Shift+Right x{copy_count})")

        for _ in range(copy_count):
            if self.stop_flag:
                return False
            self.hotkey("shift", "right")
            time.sleep(DELAY_SHIFT_RIGHT)

        if not self.trigger_sync_metadata():
            return False

        time.sleep(SYNC_DIALOG_DELAY)

        self.press("enter")
        time.sleep(0.3)

        return True

    def run(self):

        entries = self.read_manifest()

        if TEST_LIMIT is not None:
            entries = entries[:TEST_LIMIT]
            print(f"TEST_LIMIT set -- only processing the first {TEST_LIMIT} stack(s).")

        print(f"\n{len(entries)} stack(s) to process.")
        print("Prerequisites -- confirm ALL of these before continuing:")
        print("  1. Every stack in Quick Collection is EXPANDED")
        print("     (Photo > Stacking > Expand All Stacks)")
        print("  2. Sync Metadata's checkboxes are already set the way you want")
        print("     (run it once by hand this session if you haven't)")
        print("  3. The FIRST photo in Quick Collection is currently selected")
        print("\nPress ESC anytime to stop\n")

        self.activate_lightroom()
        self.ensure_library_module()

        synced = 0
        skipped = 0

        for fname, copy_count in entries:

            if self.stop_flag:
                break

            if copy_count > 0:
                ok = self.sync_stack(fname, copy_count)
                if not ok:
                    break
                synced += 1
                db.d(f"{fname}: synced ({copy_count} VC/companion[s])")
            else:
                db.d(f"{fname}: no VCs/companions, nothing to sync")
                skipped += 1

            # Removes the whole current selection from Quick Collection
            # (not just the active photo) and auto-advances the filmstrip
            # to the next master -- confirmed behavior, same shortcut
            # metadataTool.py's finish_image() already uses.
            self.press("b")
            time.sleep(0.3)

        if self.stop_flag:
            print(f"\nStopped early. Synced {synced}, skipped {skipped}, "
                  f"{len(entries) - synced - skipped} not reached.")
        else:
            print(f"\nDone. Synced {synced} stack(s), skipped {skipped} (no VCs/companions).")


if __name__ == "__main__":
    tool = SyncVCs()
    tool.run()
