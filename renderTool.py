# renderTool remake


# Import libraries
import os
from tkinter import Tk
from tkinter.filedialog import askdirectory
from PIL import Image, ImageDraw, ImageFont
import math
from concurrent.futures import ThreadPoolExecutor
import random

class Renderer:
    def __init__(self, roll):
        print("\n\n\n\n\n\n\n\n\n")
        self.roll = roll            # roll metadata object
        self.framecount = roll.countExposures
        self.emulsion = (self.roll.isColor, self.roll.isBlackAndWhite, self.roll.isSlide)
        self.dpi = 300              # dots per inch
        self.sheet_size = [210, 297]  # sheet dimensions
        self.margin = 5      # page side margins
        self.margin_top = self.margin * 3
        self.margin_rows = 4 # mm between rows
        self.sheet_print_size = [self.sheet_size[0] - 2 * self.margin, self.sheet_size[1] - 2 * self.margin]
        self.canvas = None          # PIL image canvas
        self.canvas_2 = None
        self.draw = None            # PIL draw context
        self.rebate_metadata = []
        self.font = ImageFont.truetype(self.roll.fontPath, size=self.to_px(3))  # pick size you want
        self.fontColor = self.roll.fontColor
        self.rebate_size = None
        self.film_size = None

    def render(self):
        # 1. prepare layout + assets
        self.load_format()

        # 2. build canvas + grid
        self.build_canvas()
        self.build_grid()
        
        # 3. Handle metadata
        self.process_metadata()

        # 4. Render elements
        # self.paste_images()
        # self.paste_rebates()
        # self.paste_metadata()
        # self.paste_all()
        self.render_images()
        self.render_header()

        # 5. Show
        self.canvas.show()

    # Loads film format (35mm, 6x7 etc)
    def load_format(self):
        key = self.roll.filmformat
        format = FORMATS.get(key)
        if not format:
            raise KeyError(f"Format {key} not found in FORMATS")
        self.rebate_size = (format["film_w"], format["film_h"]) # in mm
        self.film_size = (format["frame_w"], format["frame_h"]) # in mm

    # Builds initial sheet with dimensions
    def build_canvas(self):
        DEBUG = False
        canvas = Image.new("RGBA", (self.to_px(self.sheet_size[0]), self.to_px(self.sheet_size[1])), (0, 0, 0, 255))
        draw = ImageDraw.Draw(canvas)
        if DEBUG:
            draw = self.debug_draw_margins(draw)
        
        self.canvas = canvas
        self.canvas_2 = canvas.copy()
        self.draw = draw

    # draws pink guidelines around self.sheet_print_size inside the sheet
    def debug_draw_margins(self, draw):
        w, h = self.sheet_size[0], self.sheet_size[1]
        w_p, h_p = self.sheet_print_size[0], self.sheet_print_size[1]

        d_x = (w - w_p) / 2
        d_y = (h - h_p) / 2

        # coords of printable area
        x0, y0 = self.to_px(d_x), self.to_px(d_y)
        x1, y1 = self.to_px(w - d_x), self.to_px(h - d_y)

        # draw lines (pink)
        color = (255, 0, 128, 255)
        width = 3
        draw.line([(x0, y0), (x1, y0)], fill=color, width=width)  # top
        draw.line([(x0, y1), (x1, y1)], fill=color, width=width)  # bottom
        draw.line([(x0, y0), (x0, y1)], fill=color, width=width)  # left
        draw.line([(x1, y0), (x1, y1)], fill=color, width=width)  # right

        return draw
    
    # Build a grid of coordinates for center points for each photo
    def build_grid(self):
        sheet = (self.sheet_size[0], self.sheet_size[1])
        print_area = (self.sheet_print_size[0], self.sheet_print_size[1])
        rebate = (self.rebate_size[0], self.rebate_size[1]) # frame size of rebate (incl margins) w,h

        # calculate optimal grid size
        cols, rows, k = self.find_optimal_grid(print_area, rebate, self.framecount)

        # Resize rebate and film sizes by k
        self.k = k
        # self.rebate_size = [dim * k for dim in self.rebate_size]
        # self.film_size = [dim * k for dim in self.film_size]

        # Get absolute center coordinates for placement of each frame (x,y) with origin in top left
        grid = []
        w = rebate[0] * k
        h = rebate[1] * k
        y0 = (sheet[1] - print_area[1]) / 2 + self.margin_top
        x0 = (sheet[0] - print_area[0]) / 2

        for row in range(rows):
            for col in range(cols):
                x = x0 + w * (col + 0.5)
                y = y0 + h * (row + 0.5)
                if row > 0:
                    y += row * self.margin_rows
                grid.append((x,y))

        self.grid = grid

        self.build_text_coords()

    def find_optimal_grid(self, sheet, frame, n):
        buffer = self.margin_rows
        cols = 0
        rows = 0
        k_old = 0.0
        k_new = 0.0
        k = 0.0
        k_margin = 0.1
        tup = (cols, rows, k)  # (best_cols, best_rows, best_k)
        eps = 1e-12

        best_unscaled = None  # (cols, rows) that fit at k = 1.0

        # find the combination; first prefer any that fit unscaled (k = 1.0), then best k<=1 with margin preference for more cols
        for cols in range(1, n + 1):
            rows = math.ceil(n / cols)
            k_col = sheet[0] / (cols * frame[0])
            k_row = sheet[1] / (rows * (frame[1] + buffer))

            print(f"Trying {cols} cols x {rows} rows: k_col={k_col:.3f}, k_row={k_row:.3f}")

            # if it fits unscaled, record as a k=1.0 candidate
            if k_col >= 1.0 - eps and k_row >= 1.0 - eps:
                if best_unscaled is None:
                    best_unscaled = (cols, rows)
                else:
                    bu_cols, bu_rows = best_unscaled
                    # prefer more columns; if tied, fewer rows
                    if cols > bu_cols or (cols == bu_cols and rows < bu_rows):
                        best_unscaled = (cols, rows)
                # still continue loop to see if there is an even wider unscaled option
                continue

            # otherwise, evaluate scaled option (no upscaling)
            k_new = min(k_col, k_row)
            if k_new > 1:
                continue

            best_cols, best_rows, best_k = tup

            # strictly better k → take it
            if k_new > best_k + eps:
                k_old = k_new
                tup = (cols, rows, k_new)
                continue

            # within margin → prefer more columns
            if (best_k - k_new) <= k_margin + eps and cols > best_cols:
                k_old = k_new
                tup = (cols, rows, k_new)
                continue

            # equal k (within eps) and more columns → prefer more columns
            if abs(k_new - best_k) <= eps and cols > best_cols:
                k_old = k_new
                tup = (cols, rows, k_new)

        # If any unscaled layout exists, prefer it (k = 1.0), maximizing columns
        if best_unscaled is not None:
            uc, ur = best_unscaled
            print(f"Optimal grid (no scaling): {uc} cols x {ur} rows with k=1.000")
            return uc, ur, 1.0

        print(f"Optimal grid: {tup[0]} cols x {tup[1]} rows with k={tup[2]:.3f}")
        return tup[0], tup[1], tup[2]

    # Converts mm to pixels at self.dpi
    def to_px(self, mm):
        return round(mm * self.dpi / 25.4)

    # Calculate text box anchors for each image/metadata
    def build_text_coords(self):
        # margins in mm → px
        tm_mm = 1.5
        th_mm = 0
        tm = int(round(self.to_px(tm_mm)))
        th = int(round(self.to_px(th_mm)))

        # get frame (rebate) pixel size
        # if you already have it, use that; otherwise open once
        rebate = self.get_base_rebate_image()
        w_px, h_px = rebate.size
        try:
            rebate.close()
        except Exception:
            pass

        coords = []
        for _ in range(self.framecount):
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
                "BC": (cx,    bot, "mb"),
                "BR": (right, bot, "rb"),
            })

        self.text_coords = coords

    # Scrape relevant metadata from obj to render on rebates
    def process_metadata(self):
        # TL = cam/lns
        # TC = index
        # TR = stk
        # BL = date
        # BR = rating
        
        # Build metadata for each image
        metadata = []


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
        
        # print cam
        img = self.roll.images[0]

        print(img.cam, self.roll.cam)       
        self.rebate_metadata = metadata

        return

    def render_images(self):
        # 1) create base image from rebate
        base = self.get_base_rebate_image()

        # print base image size in mm using base.width and base.height in mm
        print(f"Base rebate image size: {base.width * 25.4 / self.dpi:.1f} x {base.height * 25.4 / self.dpi:.1f} mm")

        # 2) parallel process each frame
        n = min(self.framecount, len(self.grid), len(self.roll.images))
        print(f"Rendering {n} frames in parallel...")
        with ThreadPoolExecutor(max_workers=min(8, n)) as executor:
            futures = [executor.submit(self.task, base.copy(), i) for i in range(n)]
            results = [f.result() for f in futures]
        
        # 3) paste each result onto canvas at grid position
        for i in range(self.framecount):
            frame_img = results[i]
            cx, cy = self.to_px(self.grid[i][0]), self.to_px(self.grid[i][1])
            x0 = int(cx - frame_img.width / 2)
            y0 = int(cy - frame_img.height / 2)
            self.canvas.paste(frame_img, (x0, y0), frame_img)

    def get_base_rebate_image(self):
        key = self.roll.filmformat
        path = os.path.join(os.path.dirname(__file__), 'data', 'rebates', f'{key}.png')
        if not os.path.exists(path):
            print(f"Rebate image for format {key} not found at {path}. Skipping rebates.")
            return None
        rebate = Image.open(path).convert("RGBA")

        return rebate
    
    # define parallel subroutine
    def task(self, rebate_base, i):
        print(f"Processing frame {i+1}")

        # work on a fresh copy per frame
        frame = rebate_base.copy()

        bbox_h = int(self.film_size[1])         # mm
        bbox_w = int(self.film_size[0]) * 2     # mm

        # 1) load exposure
        path = self.roll.images[i].filePath
        img = Image.open(path).convert("RGBA")

        # 2) rotate if needed
        if getattr(self.roll.images[i], "isVertical", False):
            img = img.rotate(90, expand=True)

        # 3) fit to bounding box (no upscaling)
        img.thumbnail((self.to_px(bbox_w), self.to_px(bbox_h)), Image.LANCZOS)

        # 4) paste onto frame in centered position
        px = (frame.width - img.width) // 2
        py = (frame.height - img.height) // 2
        frame.paste(img, (px, py), img)

        # 5) overlay rebate ON TOP
        frame.paste(rebate_base, (0, 0), rebate_base)

        # 6) metadata (draw last)
        if i < len(self.rebate_metadata) and i < len(self.text_coords):
            md = self.rebate_metadata[i]
            coords = self.text_coords[i]
            draw_local = ImageDraw.Draw(frame)

            # Make a per-thread font to avoid FreeType thread quirks
            try:
                local_font = ImageFont.truetype(self.font_path, self.font_size)
            except Exception:
                # fall back to shared font or default
                local_font = getattr(self, "font", ImageFont.load_default())

            # ensure non-transparent color
            fc = self.fontColor
            if isinstance(fc, tuple) and len(fc) == 3:
                fc = (fc[0], fc[1], fc[2], 255)

            for pos, text in md.items():
                if not text or pos not in coords:
                    continue
                

                # TODO: fix text placement and positioning. shows up on 120, not at all on 135. 1
                # x, y, anchor = coords[pos]
                x = self.to_px(coords[pos][0])
                y = self.to_px(coords[pos][1])

                x = coords[pos][0]
                y = coords[pos][1]
                anchor = coords[pos][2]

                draw_local.text(
                    (int(round(x)), int(round(y))),
                    text,
                    fill=fc,
                    font=local_font,
                    anchor=anchor
                )

        # 7) scale by k
        scaled_w = max(1, int(round(frame.width * self.k)))
        scaled_h = max(1, int(round(frame.height * self.k)))
        frame = frame.resize((scaled_w, scaled_h), Image.LANCZOS)

        return frame

    def render_header(self):
        # Build header with the following information/placements:
        # Top row (bold, larger):
        #   Left: Title, Right: Roll Index
        # Second row (smaller):
        #   date range (start - end) | stock | camera

        # Config
        font_size_large = self.to_px(8)   # in points
        font_size_small = self.to_px(5)   # in points
        font_path = self.roll.fontPath
        font_color = (255, 255, 255, 255)  # white

        title = self.roll.title if self.roll.title else "78_23-09-23 R35S APX400 Seewlisee"
        index = f'#{int(self.roll.index):03d}' if self.roll.index is not None else "???"
        date_start = self.roll.startDate.strftime("%y.%m.%d") if self.roll.startDate else "??????"
        date_end = self.roll.endDate.strftime("%y.%m.%d") if self.roll.endDate else "??????"
        date_range = f"{date_start} - {date_end}"
        stock = self.roll.stk if self.roll.stk else "???"
        camera = self.roll.cameras if self.roll.cameras else "???"

        # Fonts
        font_large = ImageFont.truetype(font_path, font_size_large)
        font_small = ImageFont.truetype(font_path, font_size_small)

        # Draw context
        img = self.canvas
        draw = ImageDraw.Draw(img)

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
        w, h = img.size
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
        row_text = f"{date_range} // {stock} // {camera}"

        draw.text(
            (padding_x, second_row_y),
            row_text,
            font=font_small,
            fill=font_color,
            anchor="la"
        )

        self.canvas = img


    def render_infopage(self):
        """
        Build a clean metadata table for each exposure on a fresh canvas.
        Layout: two columns if needed, with headers and truncated cells to fit.
        Uses modern Pillow sizing via draw.textbbox.
        """
        # --- Config ---
        img_w, img_h = self.canvas.size
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
        from PIL import ImageDraw, ImageFont, Image
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
        self.canvas_2 = info_img

        # Show canvas
        self.canvas_2.show()


FORMATS = {
    # 35mm / 135 film
    "half": {            # 18×24 mm on 135
        "filmformat": "135",
        "film_w": 24.0 * 1.0857142857,          # frame pitch for half-frame not standardized in still; leaving blank
        "film_h": 35.0,          # nominal film width
        "frame_w": 24.0,
        "frame_h": 18.0,
    },
    "35mm": {            # 24×36 mm on 135
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
    "6x6": {
        "filmformat": "120",
        "film_w": None,
        "film_h": 61.0,
        "frame_w": 56.0,
        "frame_h": 56.0,
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
    "6x17": {
        "filmformat": "120",
        "film_w": None,
        "film_h": 61.0,
        "frame_w": 56.0,
        "frame_h": 168.0,
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
