# renderTool remake


# Import libraries
import os
from tkinter import Tk
from tkinter.filedialog import askdirectory
from PIL import Image, ImageDraw, ImageFont
import math
from concurrent.futures import ThreadPoolExecutor
import random

from pyparsing import line
from debuggerTool import debuggerTool
import subprocess
import sys

DEBUG = 0
WARNING = 0
ERROR = 1
db = debuggerTool(DEBUG, WARNING, ERROR)

FORMATS = {
    # 35mm / 135 film
    "half": {            # 18×24 mm on 135
        "filmformat": "135",
        "film_w": 24.0 * 1.0857142857,          # frame pitch for half-frame not standardized in still; leaving blank
        "film_h": 35.0,          # nominal film width
        "frame_w": 24.0,
        "frame_h": 18.0,
    },
    "135": {            # 24×36 mm on 135
        "filmformat": "135",
        "film_w": 38.00,         # 8 perforations @ 4.75 mm incl. 2 mm gap
        "film_h": 35.0,          # nominal film width
        "frame_w": 36.0,
        "frame_h": 24.0,
    },
    "panoramic": {       # XPan-style on 135
        "filmformat": "135",
        "film_w": 65.0 + 4.0,          # per-frame advance varies by body
        "film_h": 35.0,
        "frame_w": 65.0,         # Hasselblad XPan spec
        "frame_h": 24.0,
    },

    # 120 roll film (actual frame areas per ISO 732 table)
    "645": {
        "filmformat": "120",
        "film_w": None,          # spacing varies by back/camera
        "film_h": 61.0,          # modern films ≈61 mm wide
        "frame_w": 56.0,
        "frame_h": 41.5,
    },
    "6x4.5": {           # alias of 645
        "filmformat": "120",
        "film_w": None,
        "film_h": 61.0,
        "frame_w": 56.0,
        "frame_h": 41.5,
    },
    # "6x6": {
    #     "filmformat": "120",
    #     "film_w": None,
    #     "film_h": 61.0,
    #     "frame_w": 56.0,
    #     "frame_h": 56.0,
    # },
    "6x6": {
        "filmformat": "120",
        "film_w": 74.0,
        "film_h": 61.0,
        "frame_h": 56.0,
        "frame_w": 56.0,
    },
    "6x7": {
        "filmformat": "120",
        "film_w": 74.0,
        "film_h": 61.0,
        "frame_h": 56.0,
        "frame_w": 70.0,
    },
    "6x8": {
        "filmformat": "120",
        "film_w": None,
        "film_h": 61.0,
        "frame_w": 56.0,
        "frame_h": 77.0,
    },
    "6x9": {
        "filmformat": "120",
        "film_w": None,
        "film_h": 61.0,
        "frame_w": 56.0,
        "frame_h": 84.0,
    },
    "6x12": {
        "filmformat": "120",
        "film_w": None,
        "film_h": 61.0,
        "frame_w": 56.0,
        "frame_h": 118.0,
    },
    # "6x17": {
    #     "filmformat": "120",
    #     "film_w": None,
    #     "film_h": 61.0,
    #     "frame_w": 56 * 2.708333333333333,
    #     "frame_h": 56.0,  # 6x17 frame height is 2.7083... times the 6x6 height
    "6x17": {
        "filmformat": "120",
        "film_w": 74.0,
        "film_h": 61.0,
        "frame_h": 25.846153846153849,
        "frame_w": 70.0,
    },
    "6x24": {
        "filmformat": "120",
        "film_w": None,
        "film_h": 61.0,
        "frame_w": 56.0,
        "frame_h": 224.0,
    },

    # Large format sheet film (sheet size nominal; image area often smaller)
    "4x5": {
        "filmformat": "sheet",
        "film_w": 127.0,         # sheet width
        "film_h": 102.0,         # sheet height
        "frame_w": 120.0,        # typical image area
        "frame_h": 95.0,
    },
    "5x7": {
        "filmformat": "sheet",
        "film_w": 178.0,
        "film_h": 127.0,
        "frame_w": None,         # varies by holder/mask
        "frame_h": None,
    },
    "8x10": {
        "filmformat": "sheet",
        "film_w": 254.0,
        "film_h": 203.0,
        "frame_w": None,         # image area depends on holder; leaving blank
        "frame_h": None,
    },
    "11x14": {
        "filmformat": "sheet",
        "film_w": 356.0,
        "film_h": 279.0,
        "frame_w": None,
        "frame_h": None,
    },

    # catch-all
    "custom": {
        "filmformat": None,
        "film_w": None,
        "film_h": None,
        "frame_w": None,
        "frame_h": None,
    },
}

class Renderer:
    def __init__(self):
        self.roll = None
        # Sheet attributes
        self.dpi = 300              # dots per inch
        self.sheet_size = [210, 297]  # sheet dimensions
        self.margin = 5      # page side margins
        self.margin_top = self.margin * 3
        self.margin_rows = 4 # mm between rows
        self.sheet_print_size = [self.sheet_size[0] - 2 * self.margin, self.sheet_size[1] - 2 * self.margin]
        self.rebate_size = None
        self.film_size = None
        self.grid = None
        self.grid_text = None

        # Canvas Objects
        self.sheets = []

        # Data
        self.film_size = None
        self.rebate = None
        self.rebate_size = None
        self.framecount = None
        self.emulsion = None
        self.font = None
        self.fontPath = "fonts/JMH Typewriter mono Bold.ttf"
        self.fontColor = None
        self.rebate_metadata = []
        self.rebate_metadata_copies = []

    def render(self, roll, P1=1, P2=1, P3=1, save=False, show=False, output_folder=None, save_path=None):
        self.roll = roll
        self.extract_data()
        self.process_metadata()
        self.prepare_sheets()
        canvasses = []
        if P1:
            canvasses.append((self.render_P1(), None))
        if P2 and self.roll.containsCopies:
            for i, canvas in enumerate(self.render_P2()):
                canvasses.append((canvas, f"copies_{i+1}"))
        if P3:
            canvasses.append((self.render_P3(), "info"))

        if show:
            db.d("[R]", "Rendering complete. Displaying sheets...")
            for canvas in canvasses:
                canvas[0].show()
        
        if save:
            db.d("[R]", "Rendering complete. Saving sheets...")
            for canvas, name in canvasses:
                if output_folder:
                    basename = os.path.join(output_folder, f"{self.roll.index_str}_contact_sheet")
                else:
                    basename = f"output/{self.roll.index_str}_contact_sheet"
                suffix = ".png"
                path = f"{basename}_{name}{suffix}" if name else f"{basename}{suffix}"
                os.makedirs(os.path.dirname(path), exist_ok=True)
                canvas.save(path)
            if save_path:
                # also save main sheet to specified path
                path = os.path.join(save_path, f"{self.roll.index_str}_contact_sheet.png")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                canvasses[0][0].save(path)
        self.cleanup()

    def extract_data(self):
        # Roll Data
        self.framecount = self.roll.countExposures
        self.emulsion = (self.roll.isColor, self.roll.isBlackAndWhite, self.roll.isSlide)

        # Font data
        try:
            self.font = ImageFont.truetype(self.roll.fontPath, size=self.to_px(3))  # pick size you want
            self.fontColor = self.roll.fontColor
            if self.font is None or self.fontColor is None:
                db.e("[R]", 'Font error roll:', self.roll.dbIdx)
        except Exception:
            db.e("[R]", 'Font error roll:', self.roll.dbIdx)
        
        
        # Derived attributes
        self.rebate_size, self.film_size = self.get_format(self.roll.filmformat)
        return

    def get_format(self, key):
        """
        Processes format info from LUT.

        :param key: LUT Key. <roll.filmformat>

        :return rebate_size: Tuple (film_w, film_h)
        :return film_size: Tuple (frame_w, frame_h)
        """
        format = FORMATS.get(key)
        if not format:
            raise KeyError(f"Format {key} not found in FORMATS")
        rebate_size = (format["film_w"], format["film_h"]) # in mm
        film_size = (format["frame_w"], format["frame_h"]) # in mm
        return rebate_size, film_size

    def prepare_sheets(self):
        """
        Prepares layout for contact sheets. Grid dimensions, margins, sheet size.
        """

        # init all three pages canvas objects
        P1_main = self.init_canvas()
        P2_copies = self.init_canvas()
        P3_info = self.init_canvas()
        self.sheets = [P1_main, P2_copies, P3_info]


        return

    def init_canvas(self):
        """
        Prepares canvas objects
        
        :return (canvas, draw, canvas_temp): Canvas + Draw objects
        """

        canvas = Image.new("RGBA", (self.to_px(self.sheet_size[0]), self.to_px(self.sheet_size[1])), (0, 0, 0, 255))
        canvas_temp = canvas.copy()
        draw = ImageDraw.Draw(canvas)

        return(canvas, draw, canvas_temp)

    def cleanup(self):
        """
        Resets all parameters
        """
        self.__init__()
        return

    def build_text_coords(self, rebates, n):
        """
        Calculate text box anchors for each image/metadata, per-image (rebate) size.

        rebates[i] is an image object; w_px, h_px = rebates[i].size

        :param rebates: list of rebate image objects (already in px)
        :return coords: list[dict] with keys {TL,TC,TR,BL,BC,BR} -> (x, y, align)
        """
        # margins in mm → px
        tm_mm = 1.5
        th_mm = 0.0
        if self.roll.filmformat in ['6x7', '6x6', '6x4.5']:
            tm_mm = 2.5
            th_mm = 0.8
        tm = int(round(self.to_px(tm_mm)))
        th = int(round(self.to_px(th_mm)))

        coords = []
        for i in range(n):
            w_px, h_px = rebates[i].size

            left  = tm
            right = w_px - tm
            top   = th
            bot   = h_px - th
            cx    = w_px // 2

            coords.append({
                "TL": (left,  top, "lt"),
                "TC": (cx,    top, "mt"),
                "TR": (right, top, "rt"),
                "BL": (left,  bot, "lb"),
                "BC": (cx,    bot, "lb"),
                "BR": (right, bot, "rb"),
            })

        return coords

    def get_rebate(self, key):
        """
        Open rebate file
        
        :param key: LUT key {roll.filmformat}
        :return rebate: Image obj
        """
        path = os.path.join(os.path.dirname(__file__), 'data', 'rebates', f'{key}.png')
        if not os.path.exists(path):
            db.e('[R]', f"Rebate image for format <{key}> not found. Skipping rebates.", path)
            return None
        rebate = Image.open(path).convert("RGBA")

        return rebate

    def get_optimal_grid(self, sheet_px, rebates, n):
        """
        Grid search over (cols, rows). Sizes are in pixels.
        - rebates[i] is an image object; (w,h)=rebates[i].size are px
        - row gap (self.margin_rows) is mm on paper, treated as constant on paper -> convert to px and do NOT scale it

        :param sheet_px: (W_px, H_px) available area in px (typically print_area in px)
        :param rebates: list of image objects
        :param n: number of images to place
        :return: (best_cols, best_rows, best_k)
        """
        eps = 1e-12
        buffer_px = float(self.to_px(self.margin_rows))

        n = min(int(n), len(rebates))
        if n <= 0:
            return 0, 0, 0.0

        best_cols, best_rows, best_k = 1, n, 0.0
        best_score = -1.0

        sheet_w, sheet_h = float(sheet_px[0]), float(sheet_px[1])

        for cols in range(1, n + 1):
            rows = math.ceil(n / cols)

            col_widths = [0.0] * cols
            row_heights = [0.0] * rows

            for i in range(n):
                w_i, h_i = rebates[i].size  # px
                c = i % cols
                r = i // cols
                if r >= rows:
                    break
                if w_i > col_widths[c]:
                    col_widths[c] = float(w_i)
                if h_i > row_heights[r]:
                    row_heights[r] = float(h_i)

            total_w = sum(col_widths)
            total_h_images = sum(row_heights)

            if total_w <= eps or total_h_images <= eps:
                continue

            # Constant row gaps (paper spacing) consume sheet height directly
            gaps = buffer_px * max(0, rows - 1)
            avail_h_for_images = (sheet_h - gaps) - 125
            if avail_h_for_images <= eps:
                continue

            k = min(sheet_w / total_w, avail_h_for_images / total_h_images, 1.0)

            used_w = total_w * k
            used_h = total_h_images * k + gaps


            col_bias = 1.0
            if self.roll.filmformat in ['35mm', '135']:
                if cols == 6:
                    col_bias = 1.05 # prefer 6 cols
                if cols < 6:
                    col_bias = 0.95 # penalize fewer cols
                
            


            # maximize utilized area (fraction of available sheet area)
            score = (used_w / sheet_w) * (used_h / sheet_h) * col_bias

            if score > best_score + eps:
                best_score = score
                best_cols, best_rows, best_k = cols, rows, k
            elif abs(score - best_score) <= eps:
                # tie-break: prefer more columns; if tied, fewer rows
                if cols > best_cols or (cols == best_cols and rows < best_rows):
                    best_cols, best_rows, best_k = cols, rows, k

        # primt optimal grid
        db.d('[R]', f"Optimal grid: {best_cols} cols x {best_rows} rows with scale factor {best_k:.4f} (score: {best_score:.4f})")

        return best_cols, best_rows, best_k

    def build_grid(self, rebates):
        """
        Prepare grid coordinates (image centers) in pixels with origin top-left.

        Assumptions:
        - sheet_size, margin, margin_top, margin_rows are in mm
        - rebates[i].size is in px
        """
        # mm -> px
        sheet_px = (float(self.to_px(self.sheet_size[0])), float(self.to_px(self.sheet_size[1])))

        margin_px = float(self.to_px(self.margin))
        margin_top_px = float(self.to_px(self.margin_top))
        buffer_px = float(self.to_px(self.margin_rows))

        # define print area anchored by margins (not centered)
        print_area_px = (
            float(self.to_px(self.sheet_size[0] - 2 * self.margin)),
            float(self.to_px(self.sheet_size[1] - self.margin_top - self.margin)),
        )

        n = min(int(self.framecount), len(rebates))

        cols, rows, k = self.get_optimal_grid(print_area_px, rebates, n)
        self.k = k
        n_max = cols * rows
        if len(rebates) < n_max:
            n_max = len(rebates)

        # scaled sizes per image (px)
        sizes = []
        for i in range(n_max):
            w_i, h_i = rebates[i].size
            sizes.append((float(w_i) * k, float(h_i) * k))

        # per-column / per-row max sizes (scaled)
        col_widths = [0.0] * cols
        row_heights = [0.0] * rows
        for i in range(n):
            w_i, h_i = sizes[i]
            c = i % cols
            r = i // cols
            if r >= rows:
                break
            if w_i > col_widths[c]:
                col_widths[c] = w_i
            if h_i > row_heights[r]:
                row_heights[r] = h_i

        total_w = sum(col_widths)
        total_h = sum(row_heights) + buffer_px * max(0, rows - 1)

        # print area origin (top-left) from margins
        x_print0 = margin_px
        y_print0 = margin_top_px

        # center grid block within print area
        x0 = x_print0 + (print_area_px[0] - total_w) * 0.5
        y0 = y_print0 + (print_area_px[1] - total_h) * 0.5

        # starts
        col_starts = [x0]
        for c in range(1, cols):
            col_starts.append(col_starts[-1] + col_widths[c - 1])

        row_starts = [y0]
        for r in range(1, rows):
            row_starts.append(row_starts[-1] + row_heights[r - 1] + buffer_px)

        # centers
        grid = []
        for i in range(n_max):
            c = i % cols
            r = i // cols
            if r >= rows:
                break

            w_i, h_i = sizes[i]
            cell_w = col_widths[c]
            cell_h = row_heights[r]

            x = col_starts[c] + 0.5 * cell_w + 0.5 * (w_i - cell_w)
            y = row_starts[r] + 0.5 * cell_h + 0.5 * (h_i - cell_h)
            grid.append((x, y))

        text_coords = self.build_text_coords(rebates, n_max)
        return grid, text_coords, rows, cols

    def process_metadata(self):
        """
        Processes relevant metadata and returns relevant dicts
        
        :return rebate_metadata: array of metadata dict {TL = cam/lns, TC = index, TR = stk, BL = date, BR = rating}
        :return rebate_metadata_copy: array of metadata tuples of dicts (md_main, arr_copies)
        """
        # TL = cam/lns
        # TC = index
        # TR = stk
        # BL = date
        # BR = rating
        
        # Build metadata for each image
        metadata = []
        metadata_copies = [] # tuple with (md_main, array[md_copies])

        for img in self.roll.images:
        # build camlens and handle cases where lens is missing
            cam = img.cam
            lns = img.lns if img.lns else "???"
            camlns = cam + "/" + lns if cam and lns else cam
            md = {
                "TL": camlns,
                "BC": str(img.index) if img.index else "???",
                "TR": img.stk if img.stk else "???",
                "BL": img.dateExposed.strftime("%y%m%d") if img.dateExposed else "???",
                "BR": (str(img.rating) + 's') if img.rating else "???",
            }
            metadata.append(md)
            
            # Handle copies
            if img.containsCopies:
                i = 0
                n = len(img.copies)
                md_main = md.copy()
                md_main["BC"] = (str(img.index)+".0") if img.index else "???"

                md_copies = []
                md_copies.append(md_main)
                for copy in img.copies:
                    i += 1
                    md_copy = md_main.copy()
                    md_copy["BC"] = str(copy.index)+"."+str(i) if copy.index else "???"
                    md_copy["BR"] = (str(copy.rating) + 's') if copy.rating else "???"
                    md_copies.append(md_copy)
                metadata_copies.append(md_copies)
        
        self.rebate_metadata = metadata
        self.rebate_metadata_copies = metadata_copies

        return metadata, metadata_copies

    def render_P3(self):
        db.d("[R]", "Rendering contact sheet...", "Metadata")
        def get_str(img, max_lengths=None):
            string_arr = []

            if img.isOriginal:
                string_arr.append(img.index_str)
                string_arr.append(img.dateExposed.strftime("%y-%m-%d") if img.dateExposed else "???")
                string_arr.append((str(img.rating) + "s") if img.rating else "???")
                string_arr.append(img.lensModel if img.lensModel else "---")

                string_arr.append(f"f/{img.fNumber}" if img.fNumber else "-")
                string_arr.append(str(img.shutterSpeed) if img.shutterSpeed else "-")

                string_arr.append(img.location if img.location else "---")
                string_arr.append(img.state if img.state else "---")
                string_arr.append(img.rawFileName.split(".")[0] if img.rawFileName else "???")

            if img.isCopy:
                string_arr.append("")   # index
                string_arr.append("")   # date
                string_arr.append((str(img.rating) + "s") if img.rating else "???")
                string_arr.append(img.copyType if img.copyType else "???")
                string_arr.append("")   # fnum
                string_arr.append("")   # shutter
                string_arr.append("")   # location
                string_arr.append("")   # state

            if max_lengths is not None:
                string_arr = [
                    s.ljust(max_lengths[i]) if i < len(max_lengths) else s
                    for i, s in enumerate(string_arr)
                ]

            string = "  ".join(string_arr)
            return string, string_arr
        
        def get_max_lengths(roll):
            # get max string lengths for each, and return tuple of max lengths for formatting
            max_lengths_arr = []
            for img in roll.images_all:
                _, string_arr = get_str(img)
                for i, s in enumerate(string_arr):
                    if len(max_lengths_arr) <= i:
                        max_lengths_arr.append(len(s))
                    else:
                        if len(s) > max_lengths_arr[i]:
                            max_lengths_arr[i] = len(s)
            return max_lengths_arr

        canvas = self.sheets[2][0].copy()
        font_color = (255,255,255,255)
        font_size = self.to_px(2.5) # mm
        row_gap = self.to_px(0.75)
        font = ImageFont.truetype(
            "fonts/JMH Typewriter mono Bold.ttf",
            font_size
        )

        # Define row coordinates
        roll = self.roll
        max_lengths = get_max_lengths(roll)
        n = len(roll.images_all)
        rows = []
        
        # print str on each row
        draw = ImageDraw.Draw(canvas)
        lines = []
        # build main image metadata
        for i in range(len(roll.images)):
            img = roll.images[i]
            string, _ = get_str(img, max_lengths)
            lines.append(string)
        
        # build copy metadata and insert after main image metadata
        if roll.containsCopies:
            lines.append("")
            lines.append("")
            lines.append("")
            lines.append("Edits")
            lines.append("")
            for i in range(len(roll.images)):
                img = roll.images[i]
                if img.containsCopies:
                    # get original string
                    original_str, _ = get_str(img, max_lengths)
                    lines.append(original_str)

                    # handle copies
                    for copy in img.copies:
                        copy_str, _ = get_str(copy, max_lengths)
                        lines.append(copy_str)  # insert copy metadata after main image metadata

        # Draw all
        for i, line in enumerate(lines):
            y = self.to_px(self.margin_top * 1.2) + font_size + row_gap + i * (font_size + row_gap)
            draw.text((self.to_px(self.margin), y), line, font=font, fill=font_color, anchor="la")
            
        self.render_title(canvas, "METADATA")
        return canvas

    def render_P2(self):
        if not self.roll.containsCopies: return
        db.d("[R]", "Rendering contact sheet...", "Copies")
        tup = self.sheets[1]
        canvas = tup[0]
        draw = tup[1]
        canvas_temp = tup[2]
        images = []
        metadata = []
        rebates = []
        keys = []
        grid_text_backup = self.grid_text


        j = 0
        for img in self.roll.images:
            if img.containsCopies:
                images.append(img)
                md = self.rebate_metadata_copies[j][0]
                metadata.append(md)
                rebates.append(self.get_rebate(self.roll.filmformat))
                keys.append(None)
                k = 0
                for cpy in img.copies:
                    k+=1
                    
                    try:
                        md = self.rebate_metadata_copies[j][k]
                    except Exception:
                        db.e("[R]", "Too many frames for page, skipping!")
                        continue
                    images.append(cpy)
                    metadata.append(md)

                    if cpy.aspectRatio == img.aspectRatio:
                        keys.append(None)
                        rebates.append(self.get_rebate(img.filmformat))
                    elif cpy.filmformat in ['135', '35mm']:
                        keys.append(None)
                        if cpy.isPano:
                            rebates.append(self.get_rebate(str(cpy.filmformat)+"-pano"))
                            # rebates.append(self.get_rebate(str(cpy.filmformat)+""))
                        if cpy.isSquare:
                            # rebates.append(self.get_rebate(str(cpy.filmformat)+"-square")) # TODO: too small to fit metadata
                            rebates.append(self.get_rebate(str(cpy.filmformat)+""))
                        else:
                            rebates.append(self.get_rebate(str(cpy.filmformat)))
                    elif cpy.filmformat in ['6x7', '6x6', '6x4.5']:
                        if cpy.isSquare:
                            rebates.append(self.get_rebate("6x6"))
                            keys.append("6x6")
                        if cpy.isPano:
                            keys.append("6x17")
                            rebates.append(self.get_rebate("6x17"))
                    else:
                        keys.append(None)
                        db.e("[R]", "Could not ID format for copy!")
                    
                j+=1

        canvasses = []
        self.grid, self.grid_text, rows, cols = self.build_grid(rebates)
        n = rows * cols
        if n < len(images):
            subsets = []
            for i in range(0, len(images), n):
                subsets.append((images[i:i+n], metadata[i:i+n], rebates[i:i+n], keys[i:i+n]))
            for subset in subsets:
                canvasses.append(self.render_images(canvas_temp.copy(), subset[0], subset[1], subset[2], keys=subset[3]))
        else:
            canvasses.append(self.render_images(canvas_temp.copy(), images, metadata, rebates, keys=keys))

        # render
        for i, canvas_i in enumerate(canvasses):
            name = f'EDITS ({i+1}/{len(canvasses)})' # title
            canvas = self.render_title(canvas_i, title=name)
            canvasses[i] = canvas
        return canvasses

    def render_P1(self):
        db.d("[R]", "Rendering contact sheet...", "Main")
        tup = self.sheets[0]
        canvas = tup[0]
        draw = tup[1]
        canvas_temp = tup[2]
        images = self.roll.images
        metadata = self.rebate_metadata
        rebates = [self.get_rebate(self.roll.filmformat) for _ in images]
        self.grid, self.grid_text, _, _ = self.build_grid(rebates)

        canvas = self.render_images(canvas_temp, images, metadata, rebates)
        canvas_temp = canvas.copy()
        canvas = self.render_title(canvas_temp)
        return canvas

    def render_title(self, canvas, title=None, subtitle=None):
        """
        Renders title data
        
        :param self: Description
        :param canvas: canvas img object
        :param title: title array
        """
        index = f'#{self.roll.index_str}' # index
        if title is None:
            name = self.roll.title # title
            name = name.split("_")[4:] if "_" in name else [name]
            name = " ".join(name)
            max_length = 35
            if len(name) > max_length:
                name = name[:max_length-3] + "..."
            title = name.upper() if name else "UNTITLED ROLL"
            

        if subtitle is None:
            date_start = self.roll.startDate.strftime("%y.%m.%d") if self.roll.startDate else "??????"
            date_end = date_end = self.roll.endDate.strftime("%y.%m.%d") if self.roll.endDate else "??????"
            date_range = f"{date_start} - {date_end}"
            stock = self.roll.stk if self.roll.stk else "???"
            camera = self.roll.cameras[0] if self.roll.cameras else "???"
            subtitle = f"{date_range} // {stock} // {camera}"
            subtitle = subtitle.upper()


        font_large = ImageFont.truetype(self.fontPath, self.to_px(6))
        font_small = ImageFont.truetype(self.fontPath, self.to_px(4))
        font_color = (255, 255, 255, 255)  # white
        draw = ImageDraw.Draw(canvas)

        # Padding
        padding_x = self.to_px(self.margin)
        padding_y = self.to_px(self.margin)


        # --- Top row ---
        # Left: Title
        draw.text(
            (padding_x, padding_y),
            title,
            font=font_large,
            fill=font_color,
            anchor="la"   # left aligned
        )

        # Right: Roll Index
        w, h = canvas.size
        bbox_index = draw.textbbox((0, 0), index, font=font_large)
        w_index = bbox_index[2] - bbox_index[0]
        h_index = bbox_index[3] - bbox_index[1]

        draw.text(
            (w - padding_x, padding_y),
            index,
            font=font_large,
            fill=font_color,
            anchor="ra"   # right aligned
        )

        # Compute row height from tallest element in top row
        bbox_title = draw.textbbox((0, 0), title, font=font_large)
        h_title = bbox_title[3] - bbox_title[1]
        row_height = max(h_index, h_title)

        # --- Second row ---
        second_row_y = padding_y + row_height + self.to_px(2)  # spacing between rows


        draw.text(
            (padding_x, second_row_y),
            subtitle,
            font=font_small,
            fill=font_color,
            anchor="la"
        )

        return canvas

    def render_images(self, canvas, images, metadata, rebates, keys=[None]):
        n = len(images)
        with ThreadPoolExecutor(max_workers=min(8, n)) as executor:
            futures = [executor.submit(self.render_image, images[i], metadata[i], rebates[i], i, keys=keys) for i in range(n)]
            results = [f.result() for f in futures]

        # canvas should be RGBA if using alpha compositing
        if canvas.mode != "RGBA":
            canvas = canvas.convert("RGBA")

        for i in range(n):
            img = results[i]
            try:
                cx, cy = self.grid[i]  # already px
            except Exception:
                db.e("[R]", "Too many photos for sheet, skipping!")
                continue

            x0 = int(round(cx - img.width / 2))
            y0 = int(round(cy - img.height / 2))

            # optional: skip if completely off-canvas (debug aid)
            # if x0 >= canvas.width or y0 >= canvas.height or (x0 + img.width) <= 0 or (y0 + img.height) <= 0:
            #     continue

            canvas.paste(img, (x0, y0), img)

        return canvas

    def render_image(self, image, md, rebate_orig, i, keys=[None]):
        """
        Render single image and metadata based on position i and image object
        
        :param image: ExposureObj
        :param md: metadata dict
        :param i: index
        """
        path = image.filePath
        # set rebate object to grayscale if black and white
        if self.roll.isBlackAndWhite:
            rebate = rebate_orig.copy()
            rebate = rebate.convert("LA").convert("RGBA")
        else:
            rebate = rebate_orig.copy()
        
        base = rebate.copy()
        img = Image.open(path).convert("RGBA")

        # rotate
        if image.isVertical:
            img = img.rotate(90, expand=True)
    
        # resize
        if len(keys) > 1 and keys[i] is not None:
            bbox_h = int(FORMATS[keys[i]]["frame_h"])         # mm
            bbox_w = int(FORMATS[keys[i]]["frame_w"]) * 2     #
        else:
            bbox_h = int(self.film_size[1])         # mm
            bbox_w = int(self.film_size[0]) * 2     # mm
        img.thumbnail((self.to_px(bbox_w), self.to_px(bbox_h)), Image.LANCZOS)

        # paste image onto rebate
        px = (base.width - img.width) // 2
        py = (base.height - img.height) // 2
        base.paste(img, (px, py), img)

        # paste rebate on top
        base.paste(rebate, (0, 0), rebate)

        # render metadata
        base = self.render_rebate(base, md, i)

        # scale
        scaled_w = max(1, int(round(base.width * self.k)))
        scaled_h = max(1, int(round(base.height * self.k)))
        base = base.resize((scaled_w, scaled_h), Image.LANCZOS)

        return base

    def render_rebate(self, base_orig, md, i):
        """
        Pupulate and render metadata text around image rebate
        
        :param base_orig: img canvas object
        :param md: metadata dict
        :param i: index
        :return base: populated img canvas object
        """
        base = base_orig.copy()
        if i >= len(self.grid_text):
            db.e("[R]", "Too many photos on page! Skipping")
            return base
        coords = self.grid_text[i]
        font = ImageFont.truetype(self.roll.fontPath, self.to_px(2))

        # draw text
        for pos, text in md.items():
            if not text or pos not in coords:
                continue
            x = self.to_px(coords[pos][0])
            y = self.to_px(coords[pos][1])

            x = coords[pos][0]
            y = coords[pos][1]
            anchor = coords[pos][2]

            draw = ImageDraw.Draw(base)
            draw.text(
                (int(round(x)), int(round(y))),
                text,
                fill=self.fontColor,
                font=font,
                anchor=anchor
            )
        return base

    def to_px(self, mm):
        """
        Converts mm to pixels based on self.dpi

        :param mm: mm to convert
        :return px: corresponding pixels
        """
        return round(mm * self.dpi / 25.4)




if __name__ == "__main__":
    subprocess.run(
        [sys.executable, "/Users/rja/Documents/Coding/film-photo-archive-manager/main.py"],
        check=True
    )