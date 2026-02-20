# renderTool remake


# Import libraries
import os
from tkinter import Tk
from tkinter.filedialog import askdirectory
from PIL import Image, ImageDraw, ImageFont
import math
from concurrent.futures import ThreadPoolExecutor
import random
from debuggerTool import debuggerTool

DEBUG = 0
WARNING = 1
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
        self.fontColor = None
        self.rebate_metadata = []
        self.rebate_metadata_copies = []

    def render(self, roll, P1=1, P2=1, P3=1):
        self.roll = roll
        self.extract_data()
        self.process_metadata()
        self.prepare_sheets()
        if P1:
            self.render_P1()
        if P2:
            self.render_P2()
        if P3:
            self.render_P3()
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
            th_mm = 0.6
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
            avail_h_for_images = sheet_h - gaps
            if avail_h_for_images <= eps:
                continue

            k = min(sheet_w / total_w, avail_h_for_images / total_h_images, 1.0)

            used_w = total_w * k
            used_h = total_h_images * k + gaps

            # maximize utilized area (fraction of available sheet area)
            score = (used_w / sheet_w) * (used_h / sheet_h)

            if score > best_score + eps:
                best_score = score
                best_cols, best_rows, best_k = cols, rows, k
            elif abs(score - best_score) <= eps:
                # tie-break: prefer more columns; if tied, fewer rows
                if cols > best_cols or (cols == best_cols and rows < best_rows):
                    best_cols, best_rows, best_k = cols, rows, k

        # primt optimal grid
        db.i('[R]', f"Optimal grid: {best_cols} cols x {best_rows} rows with scale factor {best_k:.4f} (score: {best_score:.4f})")

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

# TODO: rework this shit
    def render_P3(self):
        return
        """
        Build a clean metadata table for each exposure on a fresh canvas.
        Layout: two columns if needed, with headers and truncated cells to fit.
        Uses modern Pillow sizing via draw.textbbox.
        """
        # --- Config ---
        img_w, img_h = self.sheets[2][0].size
        bg_color = (0, 0, 0, 255)
        font_color = (255, 255, 255, 255)
        grid_color = (255, 255, 255, 64)

        pad_x = self.margin
        pad_y = self.margin
        row_gap = self.to_px(0.6)  # gap between rows
        col_gap = self.to_px(1.2)  # gap between the two table columns (left/right pages)
        header_gap = self.to_px(0.8)

        font_size_header = self.to_px(4)
        font_size_cell = self.to_px(3.5)
        font_path = self.roll.fontPath

        # Fonts
        font_header = ImageFont.truetype(font_path, font_size_header)
        font_cell = ImageFont.truetype(font_path, font_size_cell)
        font_small = ImageFont.truetype(font_path, max(1, int(font_size_cell * 0.9)))

        # New canvas
        # from PIL import ImageDraw, ImageFont, Image
        info_img = Image.new("RGBA", (img_w, img_h), bg_color)
        draw = ImageDraw.Draw(info_img)

        # Utilities
        def text_size(s, font):
            bbox = draw.textbbox((0, 0), str(s), font=font)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]

        def fit_text(s, font, max_w):
            s = "" if s is None else str(s)
            if not s:
                return s
            w, _ = text_size(s, font)
            if w <= max_w:
                return s
            # binary-like trim with ellipsis
            ell = "…"
            left, right = 0, len(s)
            best = ""
            while left <= right:
                mid = (left + right) // 2
                cand = s[:mid] + ell
                w_cand, _ = text_size(cand, font)
                if w_cand <= max_w:
                    best = cand
                    left = mid + 1
                else:
                    right = mid - 1
            return best

        def yn(v):
            if v is None:
                return "—"
            return "Y" if bool(v) else "N"

        def safe_date(d):
            return d.strftime("%y.%m.%d") if d else "———"

        # Columns: (header, width_fraction_of_table)
        # Table width = (img_w - 2*pad_x - col_gap) / 2 for each side
        # Fractions roughly tuned; notes gets the remainder.
        col_defs = [
            ("#", 0.08),
            ("Date", 0.16),
            ("Cam/Lens", 0.24),
            ("Stock", 0.16),
            ("ISO", 0.08),
            ("f", 0.08),
            ("t", 0.12),
            ("★", 0.08),
            # Notes is implicit remainder in rendering step
        ]

        # Compute per-side table geometry
        side_w = (img_w - 2 * pad_x - col_gap) // 2
        # Derive absolute widths and leave remainder for Notes
        abs_widths = []
        taken = 0
        for i, (_, frac) in enumerate(col_defs):
            w_abs = int(side_w * frac)
            abs_widths.append(w_abs)
            taken += w_abs
        notes_w = side_w - taken
        abs_widths.append(notes_w)
        headers = [h for h, _ in col_defs] + ["Notes"]

        # Row height from font metrics
        _, header_h = text_size("Hg", font_header)
        _, cell_h = text_size("Hg", font_cell)
        row_h = cell_h + row_gap

        # Top labels
        title = self.roll.title if getattr(self.roll, "title", None) else "Info"
        title_w, _ = text_size(title, font_header)
        draw.text((pad_x, pad_y), title, font=font_header, fill=font_color, anchor="la")

        subtitle = (
            f"Roll {(('#' + str(int(self.roll.index))).replace('#0', '#00')):03s} | "
            f"{safe_date(getattr(self.roll, 'startDate', None))} – "
            f"{safe_date(getattr(self.roll, 'endDate', None))}"
        )
        sub_y = pad_y + header_h + self.to_px(0.5)
        draw.text((pad_x, sub_y), subtitle, font=font_small, fill=font_color, anchor="la")

        # First table top-left corner (left page)
        table_top = sub_y + header_gap + cell_h
        table_lefts = [pad_x, pad_x + side_w + col_gap]  # left and right tables

        # Header row draw function
        def draw_header(x0, y0):
            x = x0
            for i, head in enumerate(headers):
                w_col = abs_widths[i]
                text = fit_text(head, font_small, max(1, w_col))
                draw.text((x, y0), text, font=font_small, fill=font_color, anchor="la")
                x += w_col
            # underline
            y_line = y0 + cell_h + self.to_px(0.2)
            draw.line((x0, y_line, x0 + side_w, y_line), fill=grid_color, width=1)

        # How many rows fit per side?
        usable_h = img_h - table_top - pad_y
        rows_per_side = max(1, int(usable_h // row_h) - 1)  # minus header row

        # Build rows from self.roll.images
        rows = []
        for img in getattr(self.roll, "images", []):
            idx = f"{(img.index if img.index is not None else 0):02d}"
            date_s = safe_date(getattr(img, "dateExposed", None))
            cam = getattr(img, "cam", None) or getattr(img, "camera", None) or "?"
            lns = getattr(img, "lns", None) or getattr(img, "lens", None) or "?"
            cam_lns = f"{cam}/{lns}"
            stk = getattr(img, "stk", None) or getattr(img, "stock", None) or "?"
            iso = getattr(img, "iso", None) or getattr(img, "boxspeed", None) or "?"
            fnum = getattr(img, "fNumber", None)
            f_disp = f"f/{fnum:g}" if isinstance(fnum, (int, float)) else (f"{fnum}" if fnum else "—")
            sh = getattr(img, "shutterSpeed", None) or getattr(img, "exposureTime", None)
            if isinstance(sh, (int, float)) and sh > 0:
                # display as 1/x if <1
                sh_disp = f"1/{int(round(1/sh))}" if sh < 1 else f"{int(round(sh))}s"
            else:
                sh_disp = sh if sh else "—"
            rating = getattr(img, "rating", None)
            rating_disp = "—" if rating in (None, "", 0) else str(rating)
            notes = getattr(img, "notes", None) or ""

            rows.append([idx, date_s, cam_lns, stk, iso, f_disp, sh_disp, rating_disp, notes])

        # Draw tables (left then right) with pagination over rows
        row_index = 0
        for side in range(2):
            x0 = table_lefts[side]
            y0 = table_top
            # Header
            draw_header(x0, y0)
            y = y0 + row_h
            for _ in range(rows_per_side):
                if row_index >= len(rows):
                    break
                x = x0
                row = rows[row_index]
                for i, cell in enumerate(row):
                    w_col = abs_widths[i]
                    cell_txt = fit_text("" if cell is None else str(cell), font_cell, max(1, w_col))
                    draw.text((x, y), cell_txt, font=font_cell, fill=font_color, anchor="la")
                    x += w_col
                # optional row separators
                draw.line((x0, y + cell_h + self.to_px(0.15), x0 + side_w, y + cell_h + self.to_px(0.15)),
                        fill=grid_color, width=1)
                y += row_h
                row_index += 1

        # If we have more rows than fit in two sides, indicate overflow
        if row_index < len(rows):
            overflow_note = f"+{len(rows) - row_index} more…"
            note_w, _ = text_size(overflow_note, font_small)
            draw.text((img_w - pad_x - note_w, img_h - pad_y - cell_h),
                    overflow_note, font=font_small, fill=font_color, anchor="la")

        # Replace current canvas with info page
        info_img.show()

    def render_P2(self):
        if not self.roll.containsCopies: return
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
                    images.append(cpy)
                    if cpy.aspectRatio == img.aspectRatio:
                        keys.append(None)
                        rebates.append(self.get_rebate(img.filmformat))
                    elif cpy.filmformat in ['135']:
                        keys.append(None)
                        if cpy.isPano:
                            rebates.append(self.get_rebate(str(cpy.filmformat)+"-pano"))
                            # rebates.append(self.get_rebate(str(cpy.filmformat)+""))
                        if cpy.isSquare:
                            # rebates.append(self.get_rebate(str(cpy.filmformat)+"-square")) # TODO: too small to fit metadata
                            rebates.append(self.get_rebate(str(cpy.filmformat)+""))
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
                    
                    try:
                        md = self.rebate_metadata_copies[j][k]
                    except Exception:
                        db.e("[R]", "Too many frames for page, skipping!")
                        continue
                    metadata.append(md)
                j+=1

        canvasses = []
        self.grid, self.grid_text, rows, cols = self.build_grid(rebates)
        n = rows * cols
        if n < len(images):
            print(n, len(images))
            subsets = []
            for i in range(0, len(images), n):
                subsets.append((images[i:i+n], metadata[i:i+n], rebates[i:i+n], keys[i:i+n]))
            for subset in subsets:
                canvasses.append(self.render_images(canvas_temp.copy(), subset[0], subset[1], subset[2], keys=subset[3]))
        else:
            print(n, len(images))
            canvasses.append(self.render_images(canvas_temp.copy(), images, metadata, rebates, keys=keys))

        # render
        for i, canvas_i in enumerate(canvasses):
            name = f'EDITS ({i+1}/{len(canvasses)})' # title
            index = f'#{self.roll.index_str}' # index
            date_start = self.roll.startDate.strftime("%y.%m.%d") if self.roll.startDate else "??????"
            date_end = date_end = self.roll.endDate.strftime("%y.%m.%d") if self.roll.endDate else "??????"
            date_range = f"{date_start} - {date_end}"
            stock = self.roll.stk if self.roll.stk else "???"
            camera = self.roll.cameras[0] if self.roll.cameras else "???"

            title = [
                (name, index),
                (date_start, date_end, date_range),
                (stock, camera)
            ]
            canvas = self.render_title(canvas_i, title)
            canvas.show()

    def render_P1(self):
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

        # build title(s)

        name = self.roll.title # title
        name = name.split("_")[4:] if "_" in name else [name]
        name = " ".join(name)
        # Check name fits on page
        max_length = 35
        if len(name) > max_length:
            name = name[:max_length-3] + "..."
        index = f'#{self.roll.index_str}' # index
        date_start = self.roll.startDate.strftime("%y.%m.%d") if self.roll.startDate else "??????"
        date_end = date_end = self.roll.endDate.strftime("%y.%m.%d") if self.roll.endDate else "??????"
        date_range = f"{date_start} - {date_end}"
        stock = self.roll.stk if self.roll.stk else "???"
        camera = self.roll.cameras[0] if self.roll.cameras else "???"

        title = [
            (name, index),
            (date_start, date_end, date_range),
            (stock, camera)
        ]
        canvas = self.render_title(canvas_temp, title)
        canvas.show()

    def render_title(self, canvas, title):
        """
        Renders title data
        
        :param self: Description
        :param canvas: canvas img object
        :param title: title array
        """
        font_large = ImageFont.truetype(self.roll.fontPath, self.to_px(8))
        font_small = ImageFont.truetype(self.roll.fontPath, self.to_px(5))
        font_color = (255, 255, 255, 255)  # white
        draw = ImageDraw.Draw(canvas)

        name = title[0][0]
        index = title[0][1]
        date_range = title[1][2]
        stock = title[2][0]
        camera = title[2][1]

        # Padding
        padding_x = self.to_px(self.margin)
        padding_y = self.to_px(self.margin)


        # --- Top row ---
        # Left: Title
        draw.text(
            (padding_x, padding_y),
            name,
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
        bbox_title = draw.textbbox((0, 0), name, font=font_large)
        h_title = bbox_title[3] - bbox_title[1]
        row_height = max(h_index, h_title)

        # --- Second row ---
        second_row_y = padding_y + row_height + self.to_px(2)  # spacing between rows
        row_text = f"{date_range} // {stock} // {camera}"

        draw.text(
            (padding_x, second_row_y),
            row_text,
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
        font = ImageFont.truetype(self.roll.fontPath, self.to_px(3))

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
