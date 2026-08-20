import time
import json
import threading
import pyautogui
import pyperclip
import os
from pathlib import Path
from openpyxl import Workbook, load_workbook
from pynput import keyboard
from pynput.keyboard import Controller, Key
import subprocess
import sys
from tkinter import Tk, filedialog

class db:
    @staticmethod
    def d(msg):
        print(f"[DEBUG] {msg}")


class metadataTool:

    def __init__(self, xlsx_path=None, raw_folder=None):

        self.ignore_esc = False

        self.delay_default = 0.002
        self.delay_keypress = 0.002
        self.delay_paste = 0.1 # stability issues for < ~0.05
        self.delay_finish_image = 0.4 # stability issues for < ~0.3
        self.delay_start = 0.2

        self.accept_event = threading.Event()
        self.stop_flag = False

        self.acceptButton = "."
        self.pause_field = False
        self.pause_nextImage = False

        self.cameraMake_pos = None

        self.kb = Controller()

        pyautogui.FAILSAFE = True

        self.listener = keyboard.Listener(on_press=self._on_press)
        self.listener.start()

        self.script_dir = Path(__file__).parent

        # Allow an external caller (eg. importMetadata.py) to point this at a specific
        # roll's metadata xlsx / raw folder instead of always using the fixed
        # lrplugin-dev/metadata.xlsx. Calling metadataTool() with no args keeps the
        # original standalone behaviour unchanged.
        self.xlsx_path = Path(xlsx_path) if xlsx_path else self.script_dir / "metadata.xlsx"
        # NOTE: the Lightroom-side plugin (lrplugin-dev/data/nlp-importer.lrplugin/Importer.lua)
        # reads from a fixed, hardcoded path -- it has no way to know which roll we're
        # currently processing. json_path must always be that same fixed path, regardless
        # of which roll's xlsx_path was passed in. Do NOT derive this from xlsx_path (eg.
        # via .with_suffix('.json')) -- that produces a per-roll path the plugin never
        # looks at, so it silently imports stale/nonexistent data.
        self.json_path = self.script_dir / "metadata.json"
        self.raw_folder = Path(raw_folder) if raw_folder else None
        print(self.xlsx_path)

        db.d("Stage: check excel")

        if not self.xlsx_path.exists():

            if xlsx_path is not None:
                # Caller told us exactly where the roll's xlsx should be; if it's missing
                # that's an upstream error (eg. newRoll.py never ran for this roll), not
                # something to silently recover from by popping a folder picker.
                db.d(f"metadata xlsx not found at {self.xlsx_path}")
                raise FileNotFoundError(f"Expected metadata xlsx at {self.xlsx_path}")

            db.d("metadata.xlsx not found")
            db.d("Stage: select raw folder")

            raw_folder_selected = self.select_raw_folder()
            raw_files = self.get_raw_files_from_folder(raw_folder_selected)

            db.d(f"Raw files found for template: {len(raw_files)}")

            self.generate_template(raw_files=raw_files)

            db.d("Template generated. Populate metadata.xlsx and rerun.")
            sys.exit()

        db.d("Stage: process excel")
        self.data = self.process_excel()

        db.d(f"Exposure rows processed: {len(self.data)}")

        db.d("Stage: export json")
        self.export_json()

        db.d("Stage: import json")
        self.data = self.load_json()

        self.fields = [
            "nlpOriginalCameraMake",
            "nlpOriginalCameraModel",
            "nlpOriginalLensMake",
            "nlpOriginalLens",
            "nlpFilmStock",
            "nlpFilmISO",
            "nlpGearNotes",

            "nlpShotAtIso",
            "nlpAperture",
            "nlpShutterSpeed",
            "nlpFocalLength",
            "nlpDateTaken",
            "nlpShootingNotes",

            "nlpScanEquipment",
            "nlpLightSource",
            "nlpFilmHolder",
            "nlpDigitizationNotes",

            "nlpDeveloper",
            "nlpDevDilution",
            "nlpDevTimeTemp",
            "nlpDevMethod",
            "nlpDevelopmentNotes"
        ]

        self.shared_nlp = self.get_shared_nlp_fields(self.data)
        self.strip_shared_nlp_fields(self.data, self.shared_nlp)

        db.d(f"Shared NLP fields detected: {len(self.shared_nlp)}")
        if self.shared_nlp:
            db.d(f"Shared NLP field names: {list(self.shared_nlp.keys())}")




    def generate_template(self, raw_files=None):

        wb = Workbook()
        ws = wb.active
        ws.title = "Metadata"

        ws.append([
            # File info
            "Index",
            "rawFileName",
            "rawFilePath",
            
            # Date info
            "Year",
            "Month",
            "Day",

            # location info
            "Sublocation",
            "City",
            "State",
            "Country/Region",

            # ID info
            "Intellectual Genre",
            "Scene",

            # camera info
            "Camera Make",
            "Camera Model",
            "Lens Make",
            "Lens Model",

            # Film info
            "Film Stock",
            "Film ISO",
            "Gear Notes",

            # exposure info
            "Shot at ISO",
            "Aperture",
            "Shutter Speed",
            "Focal Length",
            "Shooting Notes",

            # scan info
            "Scan Equipment",
            "Light Source",
            "Film Holder",
            "Digitization Notes",
            
            # dev notes
            "Developer",
            "Dilution",
            "Dev Time/Temp",
            "Dev Method",
            "Dev Notes"
        ])

        if raw_files:
            for i, p in enumerate(raw_files, start=1):
                ws.append([
                    i,
                    p.name,
                    str(p.resolve())
                ])

        wb.save(self.xlsx_path)



    def process_excel(self):

        wb = load_workbook(self.xlsx_path)
        ws = wb.active

        data = []
        date_counter = {}

        for row in ws.iter_rows(min_row=2, values_only=True):

            (
                # File info
                idx,
                raw,
                raw_path,

                # Date info
                year,
                month,
                day,

                # location info
                sublocation,
                city,
                state,
                country,

                # ID info
                intellectual_genre,
                scene,

                # camera info
                cam_make,
                cam_model,
                lens_make,
                lens_model,

                # film info
                film_stock,
                film_iso,
                gear_notes,

                # exposure info
                shot_at_iso,
                aperture,
                shutter,
                focal_length,
                shooting_notes,

                # scan info
                scan_equipment,
                light_source,
                film_holder,
                digitization_notes,

                # dev notes
                developer,
                dev_dilution,
                dev_time_temp,
                dev_method,
                dev_notes

            ) = row

            if raw is None:
                continue

            date_created = None
            exif_datetime_original = None

            if year and month and day:

                y = int(year)
                m = int(month)
                d = int(day)

                key = f"{y:04d}-{m:02d}-{d:02d}"

                offset = date_counter.get(key, 0)
                date_counter[key] = offset + 1

                sec = offset

                date_created = f"{y:04d}-{m:02d}-{d:02d}T12:00:{sec:02d}Z"

                # Only prepare EXIF datetime if rawFilePath exists
                if raw_path not in (None, ""):
                    exif_datetime_original = f"{y:04d}:{m:02d}:{d:02d} 12:00:{sec:02d}"

            record = {
                "fileName": raw,
                "rawFilePath": raw_path,

                "standard": {
                    "location": sublocation,
                    "city": city,
                    "stateProvince": state,
                    "country": country,
                    "intellectualGenre": intellectual_genre,
                    "scene": scene,
                    "dateCreated": date_created
                },

                "exif": {
                    "dateTimeOriginal": exif_datetime_original
                },

                "nlp": {
                    "nlpOriginalCameraMake": cam_make,
                    "nlpOriginalCameraModel": cam_model,
                    "nlpOriginalLensMake": lens_make,
                    "nlpOriginalLens": lens_model,

                    "nlpFilmStock": film_stock,
                    "nlpFilmISO": film_iso,
                    "nlpGearNotes": gear_notes,

                    "nlpShotAtIso": shot_at_iso,
                    "nlpAperture": aperture,
                    "nlpShutterSpeed": shutter,
                    "nlpFocalLength": focal_length,
                    "nlpShootingNotes": shooting_notes,

                    "nlpScanEquipment": scan_equipment,
                    "nlpLightSource": light_source,
                    "nlpFilmHolder": film_holder,
                    "nlpDigitizationNotes": digitization_notes,

                    "nlpDeveloper": developer,
                    "nlpDevDilution": dev_dilution,
                    "nlpDevTimeTemp": dev_time_temp,
                    "nlpDevMethod": dev_method,
                    "nlpDevelopmentNotes": dev_notes
                }
            }

            data.append(record)

        return data




    def export_json(self):

        with open(self.json_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def load_json(self):

        with open(self.json_path, "r") as f:
            return json.load(f)

    def _on_press(self, key):

        if key == keyboard.Key.esc and not self.ignore_esc:
            self.stop_flag = True

        if hasattr(key, "char") and key.char == self.acceptButton:
            self.accept_event.set()

    def press(self, key):

        key_map = {
            "left": Key.left,
            "tab": Key.tab,
            "esc": Key.esc,
            "enter": Key.enter,
            "delete": Key.delete,
            "alt": Key.alt,
            "option": Key.alt
        }

        k = key_map.get(key, key)
        press_time = self.delay_keypress

        if key == "esc":
            self.ignore_esc = True
            press_time = 0.2

        self.kb.press(k)
        time.sleep(press_time)
        self.kb.release(k)

        if key == "esc":
            time.sleep(0.05)
            self.ignore_esc = False

        time.sleep(self.delay_default)

    def hotkey(self, *keys):

        key_map = {
            "cmd": Key.cmd,
            "ctrl": Key.ctrl,
            "shift": Key.shift,
            "alt": Key.alt,
            "tab": Key.tab,
            "v": "v",
            "a": "a",
            "d": "d",
            "1": "1",
            "enter": Key.enter
        }

        parsed = [key_map.get(k, k) for k in keys]

        for k in parsed[:-1]:
            self.kb.press(k)

        self.kb.press(parsed[-1])
        self.kb.release(parsed[-1])

        for k in reversed(parsed[:-1]):
            self.kb.release(k)

        time.sleep(self.delay_default)

    def ensure_library_module(self):
        # Both "Metadata" (top-level) and "Library > Plug-in Extras" are menus that only
        # exist while Lightroom is in the Library module -- if the last thing the user did
        # was e.g. Develop, those menu items genuinely aren't in the menu bar at all, which
        # is exactly the "-1728 Can't get menu item" error we were seeing even though the
        # menu path/title text is correct. Cmd+Option+1 is Lightroom Classic's fixed
        # shortcut for "go to Library module" regardless of which module is active.
        db.d("Stage: ensure Library module active")
        self.hotkey("cmd", "alt", "1")
        time.sleep(0.5)

    def paste_text(self, text):

        if text is None or text == "":
            return

        pyperclip.copy(str(text))
        time.sleep(self.delay_paste)
        self.hotkey("cmd", "a")
        time.sleep(self.delay_paste)
        self.hotkey("cmd", "v")
        time.sleep(self.delay_paste)

    def calibrate(self):

        print("\nCALIBRATION")
        print("Move mouse to 'Camera Make' field")
        print(f"Press <{self.acceptButton}> to capture\n")

        self.accept_event.clear()

        while not self.accept_event.is_set():

            if self.stop_flag:
                return

            time.sleep(0.01)

        self.cameraMake_pos = pyautogui.position()

        print("Captured:", self.cameraMake_pos)

    def run_metadata(self, record):

        pyautogui.moveTo(self.cameraMake_pos)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(0.2)

        for field in self.fields:

            if self.stop_flag:
                return

            value = None

            if "nlp" in record and field in record["nlp"]:
                value = record["nlp"][field]

            if value:
                self.paste_text(value)

            self.press("tab")



    def apply_lrplugin(self):

        db.d("Stage: apply Lightroom plugin")

        time.sleep(0.3)

        self.ensure_library_module()

        # deselect
        self.hotkey("cmd", "d")
        time.sleep(0.2)

        # select all
        self.hotkey("cmd", "a")
        time.sleep(0.4)

        # Menu item title/hierarchy must match lrplugin-dev/data/nlp-importer.lrplugin/Info.lua
        # exactly: LrLibraryMenuItems registers a plain "JSON Import" title (no leading
        # spaces), and "Plug-in Extras" lives under Library. Both "Library > Plug-in Extras"
        # and the top-level "Metadata" menu (see refresh_lr_metadata_from_files) only exist
        # in Lightroom's Library module -- ensure_library_module() above switches into it,
        # since that's what was actually causing the earlier "-1728 Can't get menu item"
        # failures, not the menu text/hierarchy itself.
        script = '''
        tell application "Adobe Lightroom Classic" to activate
        delay 0.3
        tell application "System Events"
            tell process "Adobe Lightroom Classic"
                click menu item "JSON Import" of menu 1 of menu item "Plug-in Extras" of menu 1 of menu bar item "Library" of menu bar 1
            end tell
        end tell
        '''

        # This is the step that actually applies Sublocation/City/State/Country/
        # Intellectual Genre/Scene/dateCreated (everything in each record's "standard"
        # block) -- it was previously run with stdout/stderr sent to DEVNULL and no
        # returncode check, so a failed menu click (eg. Lightroom not frontmost, or the
        # custom lrplugin-dev plugin not installed/enabled) looked identical to success:
        # nothing printed, script kept going, and none of that metadata ever landed.
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("=" * 70)
            print("ERROR: JSON Import menu click failed.")
            print("Sublocation/City/State/Country/Intellectual Genre/Scene/dateCreated")
            print("were NOT applied to any photo. Stopping here rather than continuing")
            print("as if it worked.")
            print(result.stderr.strip())
            print('Check that Lightroom is running and Library > Plug-in Extras >')
            print('"JSON Import" exists in the menu (Plug-in Manager > NLP Importer')
            print('must be enabled).')
            print("=" * 70)
            self.stop_flag = True
            return

        time.sleep(1.0)

        # deselect again
        self.hotkey("enter")
        self.hotkey("cmd", "d")
        self.press("left")


    def select_raw_folder(self):

        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        folder = filedialog.askdirectory(
            title="Select folder containing raw files"
        )

        root.destroy()

        if folder == "":
            return None

        return Path(folder)


    def get_raw_files_from_folder(self, folder_path):

        if folder_path is None:
            return []

        exts = {
            ".arw", ".dng", ".nef", ".cr2", ".cr3", ".raf",
            ".orf", ".rw2", ".pef", ".srw", ".tif", ".tiff"
        }

        files = []

        for p in folder_path.iterdir():
            if p.is_file() and p.suffix.lower() in exts:
                files.append(p)

        files.sort(key=lambda p: p.name.lower())

        return files



    def set_capture_time(file_path, dt_str):
        subprocess.run([
            "exiftool",
            f"-DateTimeOriginal={dt_str}",
            f"-CreateDate={dt_str}",
            f"-ModifyDate={dt_str}",
            "-overwrite_original",
            file_path
        ], check=True)


    def finish_image(self):
        self.press("esc")
        self.press("b")
        self.press("left")
        time.sleep(self.delay_finish_image)


    def save_metadata_sidecars(self):
        db.d("Stage: save metadata sidecars")
        
        # deselect all
        self.hotkey("cmd", "d")
        time.sleep(0.2)
        
        # select all
        self.hotkey("cmd", "a")
        time.sleep(0.4)
        
        # save metadata to files
        self.hotkey("cmd", "s")
        time.sleep(0.5)


    def run(self):

        db.d("Stage: run macro")

        print("\nPress ESC anytime to stop\n")
        
        self.calibrate()

        if self.stop_flag:
            return
        

        self.save_metadata_sidecars()

        self.apply_exif_dates()

        if self.stop_flag:
            return

        self.apply_lrplugin()

        if self.stop_flag:
            return

        self.apply_shared_nlp_metadata()

        if self.stop_flag:
            return

        print(f"Starting in {self.delay_start:.1f}s...")
        time.sleep(self.delay_start)

        idx = 0

        while idx < len(self.data):

            if self.stop_flag:
                break

            record = self.data[idx]

            # Shared/roll-wide nlp fields were already stripped out of every record by
            # strip_shared_nlp_fields() (and already applied once via
            # apply_shared_nlp_metadata()). If nothing unique is left for this image,
            # skip the whole click-through-every-field-and-tab sequence in run_metadata()
            # -- that's the per-image cost that was slowing this down for fields that are
            # roll-wide statics anyway. Still call finish_image() so the filmstrip
            # position advances and stays in sync with self.data.
            nlp_block = record.get("nlp", {})
            has_unique_data = any(v not in (None, "") for v in nlp_block.values())

            if has_unique_data:
                self.run_metadata(record)

                if self.stop_flag:
                    break
            else:
                db.d(f"Skip image {idx + 1}/{len(self.data)}: no unique (non-shared) metadata")

            self.finish_image()

            idx += 1

            db.d(f"Processed exposure {idx}/{len(self.data)}")

            time.sleep(self.delay_finish_image)

        print("Finished JSON records")


    def apply_exif_dates(self):

        db.d("Stage: apply EXIF DateTimeOriginal")

        changed_any = False

        for i, record in enumerate(self.data, start=1):

            raw_path = record.get("rawFilePath")
            exif_block = record.get("exif", {})
            dt_original = exif_block.get("dateTimeOriginal")

            if not raw_path or not dt_original:
                db.d(f"Skip EXIF date {i}: missing rawFilePath or dateTimeOriginal")
                continue

            # check current EXIF datetime first
            check_cmd = [
                "exiftool",
                "-s3",
                "-DateTimeOriginal",
                raw_path
            ]

            check_result = subprocess.run(check_cmd, capture_output=True, text=True)

            if check_result.returncode != 0:
                db.d(f"ExifTool read error on {raw_path}: {check_result.stderr.strip()}")
                continue

            current_dt = check_result.stdout.strip()

            if current_dt == dt_original:
                db.d(f"Skip EXIF date {i}/{len(self.data)}: already correct")
                continue

            xmp_path = Path(raw_path).with_suffix(".xmp")

            cmd = [
            "exiftool",
            f"-DateTimeOriginal={dt_original}",
            f"-CreateDate={dt_original}",
            f"-ModifyDate={dt_original}",
            "-overwrite_original",
            str(xmp_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                db.d(f"ExifTool write error on {raw_path}: {result.stderr.strip()}")
            else:
                db.d(f"EXIF date set {i}/{len(self.data)}: {raw_path}")
                changed_any = True

        if changed_any:
            self.refresh_lr_metadata_from_files()
        else:
            db.d("No EXIF date changes needed; Lightroom refresh skipped")



    def refresh_lr_metadata_from_files(self):

        db.d("Stage: Lightroom save/read metadata from files")

        self.ensure_library_module()

        # deselect all
        self.hotkey("cmd", "d")
        time.sleep(0.2)

        # select all
        self.hotkey("cmd", "a")
        time.sleep(0.4)

        db.d("Stage: refresh -- waiting for selection to settle")
        time.sleep(2)

        script = '''
        tell application "Adobe Lightroom Classic" to activate
        delay 0.3
        tell application "System Events"
            tell process "Adobe Lightroom Classic"
                click menu item "Read Metadata from File" of menu 1 of menu bar item "Metadata" of menu bar 1
            end tell
        end tell
        '''

        db.d("Stage: refresh -- running AppleScript menu click")
        time.sleep(2)

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True
        )

        db.d("Stage: refresh -- menu click done")
        time.sleep(2)

        time.sleep(1)

        if result.returncode != 0:
            # Non-fatal: apply_exif_dates() already wrote the corrected date into the
            # .xmp sidecar on disk regardless of whether Lightroom's UI picked it up here,
            # so nothing is lost -- Lightroom just won't show the updated date until it
            # re-reads that file some other way (eg. manually, or next relaunch).
            print("WARNING: 'Read Metadata from File' menu click failed -- Lightroom's")
            print("displayed date may be stale, but the .xmp sidecar on disk is correct.")
            print(result.stderr.strip())

        db.d("Stage: refresh -- done")


    def strip_shared_nlp_fields(self, data, shared_nlp):

        if not shared_nlp:
            return

        for record in data:
            nlp_block = record.get("nlp", {})

            for field in shared_nlp:
                if field in nlp_block:
                    del nlp_block[field]


    def apply_shared_nlp_metadata(self):

        if not self.shared_nlp:
            db.d("Stage: apply shared NLP metadata skipped (none detected)")
            return

        db.d("Stage: apply shared NLP metadata")

        # deselect all
        self.hotkey("cmd", "d")
        time.sleep(0.2)

        # select all
        self.hotkey("cmd", "a")
        time.sleep(0.4)

        # open metadata panel at calibrated field
        pyautogui.moveTo(self.cameraMake_pos)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(0.2)

        for field in self.fields:

            if self.stop_flag:
                return

            value = self.shared_nlp.get(field)

            if value not in (None, ""):
                self.paste_text(value)

            self.press("tab")

        # close metadata editing and return to single-image workflow
        self.press("esc")
        time.sleep(self.delay_finish_image)
        self.hotkey("cmd", "d")
        time.sleep(self.delay_finish_image)
        self.press("left")
        time.sleep(self.delay_finish_image)


    def get_shared_nlp_fields(self, data):

        shared = {}

        if not data:
            return shared

        for field in self.fields:

            first_value = data[0].get("nlp", {}).get(field)

            if first_value in (None, ""):
                continue

            same_for_all = True

            for record in data[1:]:
                value = record.get("nlp", {}).get(field)

                if value != first_value:
                    same_for_all = False
                    break

            if same_for_all:
                shared[field] = first_value

        return shared


if __name__ == "__main__":
    t1 = time.time()
    tool = metadataTool()
    tool.pause_field = False
    tool.pause_nextImage = False
    tool.run()
    t2 = time.time()

    print(f'Completed in {t2-t1:.2f}s')