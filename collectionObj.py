import os
import numpy as np
import pandas as pd
import sys
import matplotlib.pyplot as plt
from matplotlib.widgets import SpanSelector, Button
from datetime import datetime
import shutil
import subprocess
import json
from time import time

from PIL import Image
from PIL.ExifTags import TAGS
import re
import glob

# sys.path.append(os.path.abspath(r'C:\A_Documents\Documents\Coding\Lightroom_FileFinder'))
from rollObj import rollObj
from debuggerTool import debuggerTool

DEBUG = 1
WARNING = 1
ERROR = 1

db = debuggerTool(DEBUG, WARNING, ERROR)

class collectionObj:
    def __init__(self, directory):
        self.dbIdx = '[I]'
        db.i(self.dbIdx, 'Importing collection...')
        # Initialize FilmCollection with a base directory
        self.directory = directory
        self.paths_rolls = [] # List of tuples (index, folder_path) for each roll
        # self.subdirectories = self._find_subdirectories() # eg ['/Users/rja/Documents/Coding/film-photo-archive-manager/data/filmCollectionTest/2023']

        # Initialize filesizes
        self.sizeJpg = 0
        self.sizeRaw = 0
        self.countJpg = 0
        self.countRaw = 0

        # Initialize dicts
        self.stocklist = {}
        self.cameralist = {}
        self.build_stocklist()
        self.build_cameralist()
        self.rolls = []  # List to store RollMetadata instances for each roll

    def init(self):
        self._import_rolls() # Import all rolls
        self._process_rolls()
    
    # Adds rolls to collection from a given directory TODO: make it possible to import specific folders
    def add_rolls_from_directory(self, folderDir):
        # List all subdirectories in folderDir
        
        condition = (folderDir.split("/")[-1].split(" ")[0] == "2022" or folderDir.split("/")[-1].split(" ")[0] == "2023")
        print(folderDir.split("/")[-1].split(" ")[0])
        subfolders = []
        if condition:
            subfolders = os.listdir(folderDir)
        else:
            subfolders.append(os.path.basename(folderDir))
        
        # Sort subfolders by numeric prefix (before '_') if it exists
        sorted_subfolders = sorted(
            subfolders,
            key=lambda x: int(x.split('_')[0]) if x.split('_')[0].isdigit() else float('inf')
        )
        
        # Loop through each sorted subfolder and add to rolls
        for subFolder in sorted_subfolders:
            # skip ds_store files
            if subFolder.startswith('.'): continue
            if condition:
                subdirectory = os.path.join(folderDir, subFolder)
            else:
                subdirectory = folderDir
                
            # Create a RollMetadata instance for each subfolder and add it to rolls
            new_roll = rollObj(directory=subdirectory, collection=self)
            new_roll.process_roll()
            self.rolls.append(new_roll)

    # Returns address of roll index
    def getRoll(self, target_index):
        # Retrieve the roll with the specified index, if it exists
        for roll in self.rolls:
            # Compare each roll's index with target_index (match types if index is a string)
            if roll.index == target_index:
                return roll  # Return the roll if a match is found
        return None  # Return None if no roll with the specified index is found

    # Gives overview of attributes
    def help(self):
        """Prints descriptions of all attributes in FilmCollection and RollMetadata."""

        # FilmCollection attributes
        print("FilmCollection Attributes:")
        print(f"  directory: (str) - The main directory where film rolls are stored. Current value: {self.directory}")
        print(f"  rolls: (list) - A list storing RollMetadata instances, each representing a film roll.")
        
        # RollMetadata attributes description
        if self.rolls:
            print("\nRollMetadata Attributes (for each roll in rolls):")
            # Assuming that all rolls have similar attributes; display from the first roll
            example_roll = self.rolls[0]
            roll_attributes = {
                "directory": "(str) - Directory path of the roll folder.",
                "stock": "(str) - Film stock used in this roll.",
                "startDate": "(str) - Date when the roll was started.",
                "index": "(str) - Unique index extracted from the folder name.",
                "title": "(str) - Title of the roll, derived from the folder name.",
                "camera": "(str) - Camera model used for this roll.",
                "iso": "(str) - ISO setting of the roll.",
            }

            for attr, desc in roll_attributes.items():
                value = getattr(example_roll, attr, "Unknown")
                print(f"  {attr}: {desc} Current value: {value}")
        else:
            print("\nNo rolls have been added to the collection yet.")

    # Searches through subdirectories for importing
    def _find_subdirectories(self):
        subdirectories = []
        subfolders = os.listdir(self.directory)
        for folder in subfolders:
            subdirectory = os.path.join(self.directory,folder)
            if os.path.basename(subdirectory)[0] == '2': # ensure folder contains '2' at the start, eg. in '2023'
                print(f"Search for photos in ...\{folder}? [y/n]")
                # choice = input()
                choice = 'y' # TODO TEMP
                if choice == 'y': subdirectories.append(subdirectory)
        return subdirectories

    # Imports rolls
    def _import_rolls(self):
        for directory in self.subdirectories:
            db.i(self.dbIdx, f'Importing from...', [directory])
            self.add_rolls_from_directory(directory)

    # Indexes and sorts a list of filepaths
    def _create_indexed_path_dict(self, input_list):
        index_dict = {}
        for file_path in input_list:
            index = self._get_index_from_path(file_path)
            index_dict[index] = file_path

        return dict(sorted(index_dict.items(), key=lambda item: int(item[0])))

    # Returns index from filepath  
    def _get_index_from_path(self, file_path):
        directory_name = os.path.split(os.path.dirname(file_path))[1]
        is_subfolder = len(directory_name.split('_')) > 1

        if is_subfolder:
            folder_name = directory_name
        else:
            folder_name = os.path.split(file_path)[1]
        
        index = folder_name.split('_')[0]
        return index
    
    def _process_rolls(self):
        for roll in self.rolls[:]:  # Iterate over a copy of self.rolls
            if roll.jpgDirs is None:
                self.rolls.remove(roll)  # Remove from the original list
                continue

            # Accumulate sizes and counts TODO: reimplement as of 16 aug 2025
            # self.sizeJpg += roll.sizeJpg
            # self.sizeRaw += roll.sizeRaw
            # self.countJpg += roll.countJpg
            # self.countRaw += roll.countRaw

        # Set total size and count
        self.size = self.sizeJpg + self.sizeRaw
        self.count = self.countJpg + self.countRaw
    
    
    def get_size(self, extension=None):
        def format_size(size_mb):
            # Convert to GB if size is greater than 1 GB (1024 MB)
            if size_mb >= 1024:
                return f"{size_mb / 1024:.2f} GB"
            else:
                return f"{size_mb} MB"

        if extension is None:
            # Print size and count for both JPG and RAW, and the total
            print(f"JPG: {format_size(self.sizeJpg)} and {self.countJpg} files")
            print(f"RAW: {format_size(self.sizeRaw)} and {self.countRaw} files")
            print(f"Total: {format_size(self.size)} and {self.count} files")
        elif extension.lower() == "jpg":
            # Print size and count only for JPG
            print(f"JPG: {format_size(self.sizeJpg)} and {self.countJpg} files")
        elif extension.lower() == "raw":
            # Print size and count only for RAW
            print(f"RAW: {format_size(self.sizeRaw)} and {self.countRaw} files")

    def get_vec_from_rolls(self, x, y, startDate=None, endDate=None):
        # Convert startDate and endDate to datetime objects, or set them to None if not provided
        start_date = datetime.strptime(startDate, '%Y.%m.%d') if startDate else None
        end_date = datetime.strptime(endDate, '%Y.%m.%d') if endDate else None
        
        x_vals = []
        y_vals = []
        
        # Iterate through each roll
        for roll in self.rolls:
            data = roll.image_data
            for photo in data.keys():
                # Convert the photo date to a datetime object
                photo_date = datetime.strptime(data[photo][x], '%Y.%m.%d')
                
                # Check if the photo date is within the start and end date range
                if (start_date is None or photo_date >= start_date) and (end_date is None or photo_date <= end_date):
                    x_vals.append(data[photo][x])
                    y_vals.append(data[photo][y])

        return x_vals, y_vals
    
    class Plot:
        def __init__(self, collection):
            self.collection = collection

        def date_camera(self, x_input, y_input, startDate=None, endDate=None):
            # Get date and camera data
            x, y = self.collection.get_vec_from_rolls(x_input, y_input, startDate, endDate)

            # Convert dates to datetime objects
            dates = [datetime.strptime(date_str, '%Y.%m.%d') for date_str in x]

            # Create a DataFrame with the data and count occurrences
            data = pd.DataFrame({'Date': dates, 'Camera': y})
            data['Count'] = 1

            # Group by Date and Camera, then aggregate counts
            aggregated_data = data.groupby(['Date', 'Camera']).sum().reset_index()

            # Pivot the data to have cameras as columns and fill NaNs with 0s
            pivot_data = aggregated_data.pivot(index='Date', columns='Camera', values='Count').fillna(0)

            # Calculate cumulative sum for each camera
            cumulative_data = pivot_data.cumsum()

            # Plot cumulative photos taken on each camera over time
            plt.figure(figsize=(12, 6))
            for camera in cumulative_data.columns:
                plt.plot(cumulative_data.index, cumulative_data[camera], label=camera)

            # Formatting the plot
            plt.xlabel('Date')
            plt.ylabel('Cumulative Photos Taken')
            plt.title('Cumulative Photos Taken on Each Camera Over Time')
            plt.xticks(rotation=45)
            plt.legend(title="Camera Models")
            plt.tight_layout()
            plt.show()

        def date_file_size(self, x_input='date', y_input='fileSize', startDate=None, endDate=None):
            # Get date and file size data
            x, y = self.collection.get_vec_from_rolls(x_input, y_input, startDate, endDate)

            # Convert dates to datetime objects
            dates = [datetime.strptime(date_str, '%Y.%m.%d') for date_str in x]

            # Create a DataFrame with the data
            data = pd.DataFrame({'Date': dates, 'FileSize': y})

            # Convert file sizes to numeric (if they're strings) and handle missing values
            data['FileSize'] = pd.to_numeric(data['FileSize'], errors='coerce').fillna(0)

            # Convert file sizes from MB to GB
            data['FileSize'] = data['FileSize'] / 1024

            # Group by Date and sum file sizes per day
            daily_size = data.groupby('Date').sum().sort_index()

            # Calculate cumulative file size over time
            cumulative_size = daily_size.cumsum()

            # Plot cumulative file size over time
            plt.figure(figsize=(12, 6))
            plt.plot(cumulative_size.index, cumulative_size['FileSize'], label='Cumulative File Size', color='b')

            # Formatting the plot
            plt.xlabel('Date')
            plt.ylabel('Cumulative File Size (GB)')
            plt.title('Cumulative File Size Over Time')
            plt.xticks(rotation=45)
            plt.legend()
            plt.grid(True)  # Add grid lines
            plt.tight_layout()
            plt.show()

        def size_over_image_count(self, x_input='date', y_input='fileSize', startDate=None, endDate=None):
            # Get date and file size data
            x, y = self.collection.get_vec_from_rolls(x_input, y_input, startDate, endDate)

            # Convert y (file sizes) to a pandas Series and handle missing values
            file_sizes = pd.Series(y).apply(pd.to_numeric, errors='coerce').fillna(0)

            # Convert file sizes from MB to GB
            file_sizes = file_sizes / 1024

            # Calculate cumulative file size over image count
            cumulative_size = file_sizes.cumsum()

            # Plot cumulative file size over image count
            plt.figure(figsize=(12, 6))
            plt.plot(range(1, len(cumulative_size) + 1), cumulative_size, label='Cumulative File Size', color='b')

            # Formatting the plot
            plt.xlabel('Image Number')
            plt.ylabel('Cumulative File Size (GB)')
            plt.title('Cumulative File Size Over Image Number')
            plt.legend()
            plt.grid(True)  # Add grid lines
            plt.tight_layout()
            plt.show()

        def cumulative_photos_over_time2(self, x_input, y_input, startDate=None, endDate=None):
            # Get date and y data
            x, y = self.collection.get_vec_from_rolls(x_input, y_input, startDate, endDate)

            # Convert dates to datetime objects
            dates = [datetime.strptime(date_str, '%Y.%m.%d') for date_str in x]

            # Create a DataFrame with the data and count occurrences
            data = pd.DataFrame({'Date': dates, f'{y_input}': y})
            data['Count'] = 1

            # Group by Date and Camera, then aggregate counts
            aggregated_data = data.groupby(['Date', f'{y_input}']).sum().reset_index()

            # Pivot the data to have cameras as columns and fill NaNs with 0s
            pivot_data = aggregated_data.pivot(index='Date', columns=f'{y_input}', values='Count').fillna(0)

            # Calculate cumulative sum for each camera
            cumulative_data = pivot_data.cumsum()

            # Plot cumulative photos taken on each camera over time
            plt.figure(figsize=(12, 6))
            for serie in cumulative_data.columns:
                plt.plot(cumulative_data.index, cumulative_data[serie], label=serie)

            # Formatting the plot
            plt.xlabel('Date')
            plt.ylabel('Photos')
            plt.title('Cumulative Photos Taken Over Time')
            plt.xticks(rotation=45)
            plt.legend(title=f"{y_input}")
            plt.tight_layout()
            plt.show()

        def vs_image(self, x_input='date', y_input='fileSize', startDate=None, endDate=None):
            # Get date and file size data
            x, y = self.collection.get_vec_from_rolls(x_input, y_input, startDate, endDate)

            # Convert y (file sizes) to a pandas Series and handle missing values
            file_sizes = pd.Series(y).apply(pd.to_numeric, errors='coerce').fillna(0)

            # Convert file sizes from MB to GB
            file_sizes = file_sizes / 1024

            # Calculate cumulative file size over image count
            cumulative_size = file_sizes.cumsum()

            # Plot cumulative file size over image count
            plt.figure(figsize=(12, 6))
            plt.plot(range(1, len(cumulative_size) + 1), cumulative_size, label='Cumulative File Size', color='b')

            # Formatting the plot
            plt.xlabel('Image Number')
            plt.ylabel('Cumulative File Size (GB)')
            plt.title('Cumulative File Size Over Image Number')
            plt.legend()
            plt.grid(True)  # Add grid lines
            plt.tight_layout()
            plt.show()



        def cumulative_photos_over_time_with_span_and_labels(self, x_input, y_input, startDate=None, endDate=None):
            # Get date and y data
            x, y = self.collection.get_vec_from_rolls(x_input, y_input, startDate, endDate)

            # Convert dates to datetime objects
            dates = [datetime.strptime(date_str, '%Y.%m.%d') for date_str in x]

            # Convert dates to ordinal floats for SpanSelector compatibility
            date_floats = [date.toordinal() for date in dates]

            # Create a DataFrame with the data and count occurrences
            data = pd.DataFrame({'Date': dates, f'{y_input}': y})
            data['Count'] = 1

            # Group by Date and Camera, then aggregate counts
            aggregated_data = data.groupby(['Date', f'{y_input}']).sum().reset_index()

            # Pivot the data to have cameras as columns and fill NaNs with 0s
            pivot_data = aggregated_data.pivot(index='Date', columns=f'{y_input}', values='Count').fillna(0)

            # Calculate cumulative sum for each camera
            cumulative_data = pivot_data.cumsum()
            cumulative_data['DateFloat'] = cumulative_data.index.to_series().map(datetime.toordinal)

            # Create figure and axes for SpanSelector
            fig, (ax1, ax2) = plt.subplots(2, figsize=(12, 8))
            lines = {}

            # Plot cumulative photos taken on each camera over time on the main plot (ax1)
            for serie in cumulative_data.columns[:-1]:  # Exclude DateFloat
                line, = ax1.plot(cumulative_data['DateFloat'], cumulative_data[serie], label=serie)
                lines[serie] = line  # Store line references for toggling

            # Formatting for ax1
            ax1.set_xlabel('Date')
            ax1.set_ylabel('Photos')
            ax1.set_title('Cumulative Photos Taken Over Time')
            ax1.tick_params(axis='x', rotation=45)
            ax1.set_xlim(date_floats[0], date_floats[-1])  # Set x-axis limits based on ordinal range of dates
            
            # Format ax1 x-axis labels as dates
            ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: datetime.fromordinal(int(x)).strftime('%Y-%m-%d')))

            # Place the legend outside the plot
            legend = ax1.legend(title=f"{y_input}", loc="center left", bbox_to_anchor=(1, 0.5))

            # Toggle functionality for legend labels
            def on_legend_click(event):
                label = event.artist.get_text()
                line = lines[label]
                visible = not line.get_visible()
                line.set_visible(visible)
                event.artist.set_alpha(1.0 if visible else 0.3)
                fig.canvas.draw()

            # Connect the legend click event
            for legend_text in legend.get_texts():
                legend_text.set_picker(True)
            fig.canvas.mpl_connect('pick_event', on_legend_click)

            # Prepare the secondary plot (ax2) for selected region
            ax2.set_xlabel('Date')
            ax2.set_ylabel('Photos')
            ax2.set_title('Selected Region of Cumulative Photos')

            def onselect(xmin, xmax):
                # Filter cumulative data within the selected range
                selected_data = cumulative_data[
                    (cumulative_data['DateFloat'] >= xmin) & (cumulative_data['DateFloat'] <= xmax)
                ]
                
                # Clear ax2 before updating to avoid overplotting
                ax2.clear()
                
                # Variables to track y-axis limits based on visible lines only
                visible_y_min, visible_y_max = float('inf'), float('-inf')
                
                # Plot the selected data range on ax2
                for serie in cumulative_data.columns[:-1]:  # Exclude DateFloat
                    if lines[serie].get_visible():  # Only consider visible lines
                        ax2.plot(selected_data.index, selected_data[serie], label=serie)
                        # Update y-axis limits based on visible data
                        visible_y_min = min(visible_y_min, selected_data[serie].min())
                        visible_y_max = max(visible_y_max, selected_data[serie].max())
                
                # Set limits for ax2 to fit the selected visible data
                if not selected_data.empty:
                    ax2.set_xlim(selected_data.index[0], selected_data.index[-1])
                    ax2.set_ylim(0, visible_y_max*1.1)
                    ax2.legend(title=f"{y_input}")
                    ax2.set_xlabel('Date')
                    ax2.set_ylabel('Photos')
                    ax2.set_title('Selected Region of Cumulative Photos')
                    fig.canvas.draw_idle()

            # Initialize SpanSelector with horizontal selection
            span = SpanSelector(
                ax1,
                onselect,
                "horizontal",
                useblit=True,
                props=dict(alpha=0.5, facecolor="tab:blue"),
                interactive=True,
                drag_from_anywhere=True
            )

            plt.tight_layout()
            plt.show()

    def build_stocklist(self):
        xlsx_path = os.path.join(os.getcwd(), "data", "stocklist.xlsx")
        df = pd.read_excel(xlsx_path, dtype=str, engine="openpyxl").fillna("")

        stocklist = {}

        for _, row in df.iterrows():
            stk_id = row["KEY_ID"].strip()
            if not stk_id:
                continue

            entry = {
                "KEY_ID": row["KEY_ID"].strip(),
                "stk": row["stk"].strip(),
                "stock": row["stock"].strip(),
                "manufacturer": row["manufacturer"].strip(),
                "boxspeed": row["boxspeed"].strip(),
                "process": row["process"].strip(),
                "isColor": bool(int(row["isColor"])),
                "isBlackAndWhite": bool(int(row["isBlackAndWhite"])),
                "isInfrared": bool(int(row["isInfrared"])),
                "isNegative": bool(int(row["isNegative"])),
                "isSlide": bool(int(row["isSlide"])),
                "font": row["font"].strip() if pd.notna(row["font"]) else None,
                "color": row["color"].strip() if pd.notna(row["color"]) else None,
            }

            stocklist[stk_id] = entry

        self.stocklist = stocklist

    def build_cameralist(self):
        xlsx_path = os.path.join(os.getcwd(), "data", "cameralist.xlsx")
        df = pd.read_excel(xlsx_path, dtype=str, engine="openpyxl").fillna("")

        cameralist = {}

        for _, row in df.iterrows():
            cam_id = row["id"].strip()
            if not cam_id:
                continue

            entry = {
                "id": row["id"].strip(),
                "model": row["model"].strip(),
                "brand": row["brand"].strip(),
                "serial": row["serial"].strip(),
                "filmtype": row["filmtype"].strip(),
                "filmformat": row["filmformat"].strip(),
            }

            # store under id
            cameralist[cam_id] = entry
            # also allow lookup by "Brand Model" and by model
            full = f'{entry["brand"]} {entry["model"]}'.strip()
            if full:
                cameralist[full] = entry
            if entry["model"]:
                cameralist[entry["model"]] = entry

        self.cameralist = cameralist

    # Copies over all files from a roll into a designated (cleaner) collection directory with consistent filename extensions.
    def re_export_roll(self, roll):
        # Confirm if filepath exists in working folder
        filepath = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/photography/film/library'
        #TODO...


    # From directory list, imports specific roll (via index XXX)
    def import_roll(self, index):
        db.i(self.dbIdx, f'Importing roll:', index)

        # Find the path for the specified index in self.paths_rolls
        path_roll = None
        for idx, path in self.paths_rolls:
            if int(idx) == index:
                path_roll = path
                break
        if path_roll is None:
            db.w(self.dbIdx, f'Roll not found in the collection:', index)
            return

        new_roll = rollObj(directory=path_roll, collection=self)
        new_roll.preprocess_roll()
        new_roll.process_roll()
        self.rolls.append(new_roll)
        return
    
    # Identifies collection directory and builds a directory tree
    def build_directory_tree(self):
        path_library = self.directory # typically /.../photography/film/library/

        # Identify years in library
        paths_years = []
        for path in os.listdir(path_library):
            if os.path.isdir(os.path.join(path_library, path)) and re.match(r'20\d{2}', path):
                paths_years.append(os.path.join(path_library, path))

        # Index folders from each year
        paths_rolls = []
        for path_year in paths_years:
            folders = os.listdir(path_year)
            for folder in folders:
                folder_path = os.path.join(path_year, folder)
                if os.path.isdir(folder_path):
                    # Get index from folder name eg 11_22-10-03 Ektar 100 Zurich Flims Andeer --> 11 or 011_22-10-03 Ektar 100 Zurich Flims Andeer --> 11
                    index = folder.split('_')[0]
                    # build list and sort by index
                    paths_rolls.append((index, folder_path))
                    paths_rolls = sorted(paths_rolls, key=lambda x: int(x[0]))
                    pass
            
        self.paths_rolls = paths_rolls

        if len(self.paths_rolls) == 0:
            db.w(self.dbIdx, 'No rolls found in the library directory:', path_library)
        else:
            db.i(self.dbIdx, f'Library with {len(self.paths_rolls)} rolls identified', [self.paths_rolls[0], '...', self.paths_rolls[-1]])


        return
    

    # Imports multiple rolls given certain inputs:
    #   'all' - imports all rolls in self.paths_rolls
    #   [index1, index2, ...] - imports rolls with specified indices
    #   (12,13,15) - imports rolls within the specified range (inclusive)
    #   ('13-18') - imports rolls within the specified range (inclusive)
    def import_rolls(self, rolls):
        target_indices = self.get_import_indices(rolls)
        if target_indices == -1 or target_indices is None:
            return

        for index in target_indices:

            self.import_roll(index)

    def get_import_indices(self, rolls):
        # Determine target indices based on input type
        if isinstance(rolls, str) and rolls.lower() == 'all': # e.g., 'all'
            target_indices = [int(idx) for idx, _ in self.paths_rolls]
        elif isinstance(rolls, list): # e.g., [12, 15, 18]  
            target_indices = [int(idx) for idx in rolls if isinstance(idx, int) or (isinstance(idx, str) and idx.isdigit())]
        elif isinstance(rolls, tuple) and len(rolls) == 2 and all(isinstance(i, int) for i in rolls): # e.g., (12, 18)
            target_indices = list(range(rolls[0], rolls[1] + 1))
        elif isinstance(rolls, str) and '-' in rolls: # e.g., '13-18'
            try:
                start, end = map(int, rolls.split('-'))
                target_indices = list(range(start, end + 1))
            except ValueError:
                print(f"[E]\tInvalid range format: {rolls}. Use 'start-end' format.")
                return -1
        else:
            print(f"[E]\tInvalid input for importing rolls: {rolls}")
            return -1
        return target_indices
