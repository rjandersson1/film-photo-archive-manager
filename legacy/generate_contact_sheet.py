# Import libraries
import os
from tkinter import Tk
from tkinter.filedialog import askdirectory
from PIL import Image, ImageDraw, ImageFont
import math
from concurrent.futures import ThreadPoolExecutor
import random


# Open file dialogue to select photos
# askopenfiles


# Gather metadata: camera, date range, film stock

def main():
    # Hide the root window
    Tk().withdraw()

    # Ask user to select a directory containing film rolls (default to '/Users/rja/Photography/Film Scanning/Temp')
    directory = askdirectory(title="Select Directory Containing Film Rolls", initialdir='data/roll/jpeg temp/')
    if not directory:
        print("No directory selected. Exiting.")
        return

    # Create a FilmRoll object and load photos
    film_roll = FilmRoll(directory)
    film_roll.load_photos()

    # Print summary of the film roll
    print(f"Loaded {film_roll.photoCount} photos from {film_roll.directory}")
    print(f"Total size: {film_roll.size} bytes")

    film_roll.build_contact_sheet()

class FilmRoll:
    def __init__(self, directory):
        self.directory = directory
        self.photoCount = 0
        self.size = 0
        self.stock = None
        self.cameraModel = None
        self.dateStart = None
        self.dateEnd = None

    def load_photos(self):
        # Load photos from the directory
        self.photos = []
        for file in os.listdir(self.directory):
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                file_path = os.path.join(self.directory, file)
                self.photos.append(file_path)
                self.photoCount += 1
                self.size += os.path.getsize(file_path)

    def px(self, value, dpi=300):
        # Convert mm to pixels at given DPI
        return round(value * dpi / 25.4)


    def build_contact_sheet(self):
        if not self.photos:
            print("No photos to create contact sheet.")
            return

        print("Starting contact sheet build...")

        # Contact sheet size: A4 at 300 DPI
        a4_width = 2480
        a4_height = 3508

        # Frame and layout config (in mm)
        frame_width = 36
        frame_height = 24
        frame_gutter_x = 2
        frame_gutter_y = (35 - frame_height) + 1
        frames_per_row = 5
        rows_per_sheet = math.ceil(len(self.photos) / frames_per_row)

        # Create the contact sheet canvas
        contact_sheet = Image.new('RGB', (a4_width, a4_height), (0, 0, 0))
        draw = ImageDraw.Draw(contact_sheet)

        # Header layout
        header_height = self.px(10)  # 10 mm header height
        header_font_size = self.px(4)  # 4 mm font size
        header_font = ImageFont.truetype("fonts/Impact Label Reversed.ttf", size=header_font_size)

        # Header text
        header_text = f"Contact Sheet - {self.photoCount} Photos"

        # Left-aligned, vertically centered in the header region
        header_x = self.px(10)  # 10 mm left margin
        header_y = header_height // 2  # middle of the header region

        # Draw the header text
        draw.text((header_x, header_y), header_text, font=header_font, fill=(255, 255, 255), anchor="lm")
        # Calculate total grid width in mm (horizontal remains fixed)
        total_width_mm = frames_per_row * frame_width + (frames_per_row - 1) * frame_gutter_x
        total_width_px = self.px(total_width_mm)

        # Calculate horizontal buffer (center grid horizontally)
        x_buffer = (a4_width - total_width_px) // 2
        x_coords = [x_buffer + i * (self.px(frame_width) + self.px(frame_gutter_x)) for i in range(frames_per_row)]

        # Vertical layout: dynamically space rows within remaining vertical space
        # frame_h_px = self.px(frame_height)
        # available_height_px = a4_height - header_height
        # vertical_space_px = (available_height_px - rows_per_sheet * frame_h_px) // (rows_per_sheet + 1)
        # y_coords = [header_height + vertical_space_px * (i + 1) + frame_h_px * i for i in range(rows_per_sheet)]

        # Vertical layout: fixed spacing based on frame_gutter_y
        frame_h_px = self.px(frame_height)
        row_spacing_px = self.px(frame_gutter_y)

        y_coords = [header_height + (frame_h_px + row_spacing_px) * i for i in range(rows_per_sheet)]

        # Target thumbnail size
        thumb_size = (self.px(frame_width), self.px(frame_height))
        
        def prepare_thumbnail(photo_path):
            try:
                with Image.open(photo_path) as img:
                    print(f"[THREAD] Loading {os.path.basename(photo_path)}")

                    # Rotate if needed
                    if img.height > img.width:
                        img = img.rotate(90, expand=True)

                    # Resize thumbnail
                    img.thumbnail(thumb_size, Image.LANCZOS)

                    # Convert to RGBA for compositing
                    img = img.convert("RGBA")
                    thumb_w, thumb_h = img.size

                    # Load font
                    text_size = self.px(2.5)
                    # font = ImageFont.truetype("fonts/Impact Label Reversed.ttf", size=text_size)
                    font = ImageFont.truetype("fonts/helvetica-neue-55/HelveticaNeueBold.ttf", size=text_size)
                    line_height = font.getbbox("Ag")[3] + 4  # estimate one line height with padding

                    # Add space above and below the image for metadata
                    top_pad = line_height
                    bottom_pad = line_height
                    total_h = top_pad + thumb_h + bottom_pad

                    # Create base canvas
                    base = Image.new("RGBA", (thumb_w, total_h), (0, 0, 0, 255))
                    base.paste(img, (0, top_pad))  # Paste image with vertical offset

                    # Create transparent text layer
                    txt_layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
                    draw = ImageDraw.Draw(txt_layer)

                    # Sample metadata (can be passed later)
                    t_date    = "23/12/25"
                    t_framenr = "#36"
                    t_stock   = "G200"
                    t_camera  = "F3"
                    t_lens    = "50/1.4"
                    t_rating  = "3s"
                    # text_color = (215, 107, 46, 255)  # #D76B2E
                    text_color = (252, 194, 120, 255)  # #FCC278

                    # Top text (above thumbnail)
                    draw.text((0, top_pad // 2), t_date, font=font, fill=text_color, anchor="lm")
                    draw.text((thumb_w // 2, top_pad // 2), t_framenr, font=font, fill=text_color, anchor="mm")
                    draw.text((thumb_w, top_pad // 2), t_stock, font=font, fill=text_color, anchor="rm")

                    # Bottom text (below thumbnail)
                    draw.text((0, total_h - bottom_pad // 2), t_camera, font=font, fill=text_color, anchor="lm")
                    draw.text((thumb_w // 2, total_h - bottom_pad // 2), t_lens, font=font, fill=text_color, anchor="mm")
                    draw.text((thumb_w, total_h - bottom_pad // 2), t_rating, font=font, fill=text_color, anchor="rm")

                    # Composite base and text layer
                    out = Image.alpha_composite(base, txt_layer)

                    return out.convert("RGB")
            except Exception as e:
                print(f"[THREAD] Error processing {photo_path}: {e}")
                return None

        # Load and process images in parallel
        print("Preprocessing images in parallel...")
        with ThreadPoolExecutor() as executor:
            thumbnails = list(executor.map(prepare_thumbnail, self.photos))
        
        random_shift = self.px(0)
        row_shifts = [random.randint(-random_shift, random_shift) for _ in range(rows_per_sheet)]
        # Paste thumbnails into contact sheet
        print("Compositing contact sheet...")
        for i, thumb in enumerate(thumbnails):
            if thumb is not None:
                row = i // frames_per_row
                col = i % frames_per_row

                # Apply per-row horizontal shift
                x = x_coords[col] + row_shifts[row]
                y = y_coords[row]

                print(f"Pasting frame {i} at ({x}, {y})")
                contact_sheet.paste(thumb, (x, y))
            else:
                print(f"Skipping frame {i} due to earlier error.")

        # Save the contact sheet
        contact_sheet_path = os.path.join(self.directory, 'contact.pdf')
        contact_sheet.save(contact_sheet_path, 'PDF', resolution=300.0)
        print(f"Contact sheet saved to {contact_sheet_path}")



if __name__ == "__main__":
    main()