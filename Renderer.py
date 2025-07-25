# Todo
# build contact sheet headers
# work on metadata headers
# merge with film roll
# automatically detect film format and stock
# build other contact sheets (6x6, 6x7)


# Import libraries
import os
from tkinter import Tk
from tkinter.filedialog import askdirectory
from PIL import Image, ImageDraw, ImageFont
import math
from concurrent.futures import ThreadPoolExecutor
import random

def main():
    renderer = Renderer(film_roll=None)  # Placeholder for FilmRoll object
    renderer.canvas, renderer.draw = renderer.build_canvas()

    renderer.rows = 7
    renderer.cols = 5
    renderer.build_grid()
    renderer.render_rebates()
    renderer.render_images()  

    # Show canvas to user (open file)
    renderer.canvas.show()  # This will open the default image viewer with the canvas


class Renderer:
    def __init__(self, film_roll):
        self.film_roll = film_roll
        self.debug = False

        # Properties
        # Sheet properties
        self.canvas = None
        self.draw = None
        self.rows = None
        self.cols = None
        self.sheet_size = {
            'width': 2480,  # A4 at 300 DPI
            'height': 3508  # A4 at 300 DPI
        }
        self.sheet_margins = { # margin['top']
            'top': 150,     # ~0.33" (8.5 mm)
            'bottom': 100,  # a bit larger for captions or notes
            'left': 100,
            'right': 100
        }
        self.grid = []
        self.grid_centered = []

        # Frame properties
        self.film_formats = {135, 120, 110, 45, 810}
        self.film_format = None
        self.frame_formats = {
            'half',     # 18×24 mm (half-frame 35mm)
            'full',     # 24×36 mm (standard 35mm)
            'panoramic',# 24×58 mm or 24×65 mm (XPan style)
            '645',      # 56×42 mm (medium format 645)
            '6x4.5',    # alias for 645
            '6x6',      # 56×56 mm
            '6x7',      # 56×70 mm
            '6x8',      # 56×76 mm
            '6x9',      # 56×84 mm
            '6x12',     # 56×112 mm (panoramic MF)
            '6x17',     # 56×168 mm (ultra-pan MF)
            '6x24',     # 56×224 mm (rare panoramic)
            '4x5',      # 102×127 mm (large format)
            '5x7',      # 127×178 mm
            '8x10',     # 203×254 mm
            '11x14',    # 279×356 mm
            'custom'    # catch-all for unusual sizes
        }
        self.frame_format = None
        self.rebate_image_path = 'data/film_rebates/135-color.png'
        self.rebate_image = Image.open(self.rebate_image_path)
        self.rebate_width, self.rebate_height = self.rebate_image.size
        self.rebate_height = self.rebate_height + self.px(5)
        self.rebate_center = (round(self.rebate_width / 2), round(self.rebate_height / 2))
        self.rebate_header_coords = (425, 27, 12, 0) # w,h,x,y
        self.rebate_footer_coords = (425, 27, 12, 386) # w,h,x,y

        # Header
        self.header = []
        self.header_font_size = [60,40,30]
        self.header_font = ImageFont.truetype("fonts/Impact Label Reversed.ttf", size=2)
        # update font size with self.header_update(size)

        # Roll Metadata
        self.film_stock = None
        self.camera_model = None
        self.date_start = None
        self.date_end = None
        self.duration = None
        self.frame_count = 0 # individual frames
        self.photo_count = 0 # including edits, duplicates, etc.
        self.metadata_font_size = self.rebate_header_coords[1] - 2
        self.metadata_font = ImageFont.truetype("fonts/helvetica-neue-55/HelveticaNeueBold.ttf", size=self.metadata_font_size)
        self.metdata_font_color = {
            'default': (255, 255, 255, 255),  # white
            'P400_1': (252, 194, 120, 255),  # #FCC278
            'P400_2': (215, 107, 46, 255),  # #D76B2E
            'K400_1': (143, 143, 143, 255)  # #8F8F8F
        }

    # Methods
    def run(self):
        print('\n\n\nRunning renderer...\n')
        self.build_canvas()
        self.cols = 5
        # self.rows = 7
        self.build_metadata()
        self.build_header()
        self.build_grid()
        self.render_rebates()
        self.render_images()
        self.render_header()
        self.render_image_metadata()

        self.canvas.show()

    # Create canvas for contact sheet. Returns image object and ImageDraw object.
    def build_canvas(self):
        debug = True
        # Build a blank canvas with ImageDraw.draw
        canvas = Image.new("RGBA", (self.sheet_size['width'], self.sheet_size['height']), (0, 0, 0, 255))
        if self.debug:
            canvas = Image.new("RGBA", (self.sheet_size['width'], self.sheet_size['height']), (0, 0, 255, 255))
        draw = ImageDraw.Draw(canvas)

        if self.debug:
            # Draw guidelines for debugging
            def draw_guideline(x, y, w, orientation, sheet_size, draw):
                """
                Draws a white guideline with width `w` at (x, y), spanning the canvas.
                - orientation: 'horizontal' or 'vertical'
                - sheet_size: dict with 'width' and 'height' in pixels
                - draw: ImageDraw.Draw object
                """
                if orientation == 'horizontal':
                    draw.line([(0, y), (sheet_size['width'], y)], fill=(255, 255, 255, 255), width=w)
                elif orientation == 'vertical':
                    draw.line([(x, 0), (x, sheet_size['height'])], fill=(255, 255, 255, 255), width=w)

            draw_guideline(self.sheet_margins['left'], 0, 2, 'vertical', self.sheet_size, draw)
            draw_guideline(self.sheet_size['width'] - self.sheet_margins['right'], 0, 2, 'vertical', self.sheet_size, draw)
            draw_guideline(0, self.sheet_margins['top'], 2, 'horizontal', self.sheet_size, draw)
            draw_guideline(0, self.sheet_size['height'] - self.sheet_margins['bottom'], 2, 'horizontal', self.sheet_size, draw)

        self.canvas = canvas
        self.draw = draw
        return canvas, draw
    
    def build_grid(self):
        debug = True
        # Create a grid for the center points of each image.
        # Defined by rows x cols. (grab from self.rows self.cols)
        # Col spacing (from left of canvas): self.sheet_margins['left'] + round(self.rebate_width / 2)
        # Subsequent col spacing: ++self.rebate_width
        # Row spacing: (from top of canvas): self.mnargin['top'] + round(self.rebate_height / 2)
        # Subsequent row spacing: ++self.rebate_height
        # draw a 8px diameter cross at the center coordinate for each.
        # build grid as an array of x,y coordinates corresponding to the self.frame_count. (eg. grid[4] = (x ,y) corresponds to 5th frame coordinate.)

        # Build grid of center points and draw crosses
        self.grid = []
        self.grid_centered = []
        self.rows = math.ceil(self.film_roll.countJpg / self.cols)

        for row in range(self.rows):
            for col in range(self.cols):
                x = self.sheet_margins['left'] + round(self.rebate_width / 2) + col * self.rebate_width
                y = self.sheet_margins['top'] + round(self.rebate_height / 2) + row * self.rebate_height

                self.grid_centered.append((x, y))
        # Draw crosses at each grid point
                if self.debug:
                    # Draw 8px cross centered at (x, y)
                    cross_len = 16  # half of 8px
                    self.draw.line([(x - cross_len, y), (x + cross_len, y)], fill=(255, 255, 255, 255), width=2)
                    self.draw.line([(x, y - cross_len), (x, y + cross_len)], fill=(255, 255, 255, 255), width=2)

        # Convert grid center coordinates to top-left coordinates
        self.grid = self.convert_grid(self.grid_centered)

        # Draw top left corner of each frame as a 16px BLUE cross, width 2.
        if self.debug:
            for x, y in self.grid:
                cross_len = 16
                self.draw.line([(x - cross_len, y), (x + cross_len, y)], fill=(125, 125, 255, 255), width=2)
                self.draw.line([(x, y - cross_len), (x, y + cross_len)], fill=(125, 125, 255, 255), width=2)

        # Draw rebate image border as width 1 rectangle GREEN centered on each self.grid point
        if self.debug:
            for x, y in self.grid:
                # Draw a rectangle around the rebate image
                self.draw.rectangle(
                    [x, y, x + self.rebate_width, y + self.rebate_height],
                    outline=(0, 255, 0, 255),  # Green outline
                    width=1
                )  

        return self.grid, self.grid_centered
    
    # convert mm to px
    def px(self, value):
        dpi = 300
        return round(value * dpi / 25.4)  # Convert mm to inches, then to pixels
    
    def convert_grid(self, grid, width=None, height=None):
        if width is None:
            width = self.rebate_width
        if height is None:
            height = self.rebate_height
        """
        Convert grid of center coordinates to top-left coordinates for each frame.
        :param grid: List of tuples (x, y) representing center coordinates.
        :return: List of tuples (x, y) representing top-left coordinates.
        """
        converted = []
        for x, y in grid:
            top_left_x = x - round(width / 2)
            top_left_y = y - round(height / 2)
            converted.append((top_left_x, top_left_y))
        return converted
    
    def convert_grid_cell(self, cell, width, height):
        x0 = cell[0]
        y0 = cell[1]
        x1 = x0 - round(width / 2)
        y1 = y0 - round(height / 2) - self.px(2.5) # idk why but need to offset vertically
        cell = (x1, y1)
        return cell

    

    # Paste rebate .png onto canvas and return canvas, draw objects.
    # grab image file from self.rebate_image_path
    # place rebate images at each self.grid point.
    def render_rebates(self):
        # Load rebate image
        if not self.rebate_image:
            self.rebate_image = Image.open(self.rebate_image_path).convert("RGBA")

        # Paste rebate image at each grid point
        for x, y in self.grid:
            # Calculate position to paste the rebate image
            position = (x, y)
            self.canvas.paste(self.rebate_image, position, self.rebate_image)

        return self.canvas, self.draw
    
    # paste each image to the canvas at each grid point. Will need to convert from center to frame top/left coordinates.
    # run through each coordinate in self.grid_centered, convert to topleft with self.convert_grid() and frame size is 300x200 px.
    # if debug, draw a red rectangle for each image frame (as a placeholder unntil I get images
    def render_images(self):
        frame_width = self.px(36)
        frame_height = self.px(24)
        vertical_offset = self.px(2.5)

        # Convert grid
        grid = self.convert_grid(self.grid_centered, width=frame_width, height=frame_height)

        if self.debug:
            print("DEBUG ON")
            for i, (x, y) in enumerate(self.grid):
                top_left_x, top_left_y = grid[i]
                self.draw.rectangle(
                    [top_left_x, top_left_y - vertical_offset,
                    top_left_x + frame_width, top_left_y + frame_height - vertical_offset],
                    outline=(255, 0, 0, 255),
                    fill=(255, 0, 0, 64),
                    width=2
                )
            return

        # Helper function to process a single image
        def load_and_prepare_image(i):
            if i > self.film_roll.countJpg - 1 or i > len(grid) - 1:
                return None  # Skip invalid index

            path = self.film_roll.image_data[i]['path']
            exposure = self.film_roll.image_data[i]['exposure']
            try:
                with Image.open(path) as img:
                    print(f"[THREAD] Processing image {exposure}...")

                    # Rotate if portrait
                    if img.height > img.width:
                        img = img.rotate(90, expand=True)

                    # Resize
                    img.thumbnail((frame_width, frame_height), Image.LANCZOS)

                    # Convert for pasting
                    img = img.convert("RGBA")

                    # Convert center coordinate to top-left paste location
                    converted_cell = self.convert_grid_cell(self.grid_centered[exposure], img.width, img.height)
                    paste_x, paste_y = int(converted_cell[0]), int(converted_cell[1])

                    return (img.copy(), paste_x, paste_y)  # copy to detach from context manager
            except Exception as e:
                print(f"[THREAD] Error loading image {exposure} ({path}): {e}")
                return None

        # Run all in parallel
        print("Rendering images in parallel...")
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(load_and_prepare_image, range(len(self.grid))))

        # Paste all images back onto canvas
        for result in results:
            if result:
                img, x, y = result
                self.canvas.paste(img, (x, y), img)  # use img as mask for transparency







    def build_metadata(self):
        roll = self.film_roll
        self.film_stock = roll.stock
        self.film_stk = roll.stk
        self.camera_model = roll.camera
        self.date_start = roll.startDate
        self.date_end = roll.endDate
        self.duration = roll.duration
        self.frame_count = 0 # individual frames
        self.photo_count = roll.countJpg
        self.roll_path = roll.directory
        self.roll_index = roll.index
        self.roll_title = roll.title
        self.roll_format = roll.format

    def build_header(self):
        # Line 1: Large, contains index, title
        idx = self.roll_index
        tit = self.roll_title

        # Line 2: Medium, date start, date end, stock, camera, frame count,
        stk = self.film_stock
        cam = self.camera_model
        cnt = self.photo_count

        # Line 3: file path
        path = self.roll_path
        t0 = self.date_start.date()
        t1 = self.date_end
        dt = self.duration

        header_line_1 = f'#{idx}   {tit}'
        header_line_2 = f'{stk}   {cam}   #{cnt}'
        header_line_3 = f'{t0}'

        self.header.append(header_line_1)
        self.header.append(header_line_2)
        self.header.append(header_line_3)



    def render_header(self):
        # run through line by line and draw each string in header at the top of the page
        for i, string in enumerate(self.header):
            size = self.header_font_size[i]
            self.update_header(size)
            color = (255, 255, 255, 255)  # #FCC278
            font = self.header_font
            pos_y = self.sheet_margins['top'] / 3 + i * size * 1.1
            pos_x = self.sheet_margins['left'] + 10
            self.draw.text((pos_x, pos_y), string, font=font, fill=color, anchor="lm")
        
        return self.canvas, self.draw

    def update_header(self, size):
        self.header_font = ImageFont.truetype("fonts/Impact Label Reversed.ttf", size=size)
        
    def render_image_metadata(self):
        grid = self.grid
        roll = self.film_roll
        for i in range(roll.countJpg):
            cell = grid[i]
            xl = cell[0] + 12
            xm = cell[0] + round(self.rebate_header_coords[0] / 2)
            xr = cell[0] + self.rebate_header_coords[0]
            yt = cell[1]
            yb = cell[1] + self.rebate_footer_coords[3]



            metadata = roll.image_data[i]
            idx = str(i)
            date = str(metadata['date']).split('20')[-1]
            lens = str(round(metadata['focalLength']))
            cam = str(metadata['cameraModel']) + f"/{lens}"
            stk = str(metadata['stock'])
            rate = str(metadata['rating']) + "s"


            # print text onto image
            font = ImageFont.truetype("fonts/Impact Label Reversed.ttf", size=40)
            text_color = (252, 194, 120, 255)  # #FCC278
            # anchor="mm"
            self.draw.text((xm,yt), idx, font=font, fill=text_color, anchor="mt")
            self.draw.text((xl, yt), cam, font=font, fill=text_color, anchor="lt")
            self.draw.text((xr, yt), stk, font=font, fill=text_color, anchor="rt")
            self.draw.text((xr, yb), rate, font=font, fill=text_color, anchor='rt')
            self.draw.text((xl, yb), date, font=font, fill=text_color, anchor='lt')
            # font = ImageFont.truetype("fonts/Impact Label Reversed.ttf", size=30)
            # self.draw.text((x, y + 50), lens, font=font, fill=text_color, anchor="mm")


        

if __name__ == "__main__":
    main()