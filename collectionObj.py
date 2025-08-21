import os
import numpy as np
import pandas as pd
import sys
import matplotlib.pyplot as plt
from matplotlib.widgets import SpanSelector, Button
from datetime import datetime

from PIL import Image
from PIL.ExifTags import TAGS
import re
import glob

# sys.path.append(os.path.abspath(r'C:\A_Documents\Documents\Coding\Lightroom_FileFinder'))
from rollObj import rollObj

class collectionObj:
    def __init__(self, directory):
        print("[I]\tImporting collection...")
        # Initialize FilmCollection with a base directory
        self.directory = directory
        self.subdirectories = self._find_subdirectories() # eg ['/Users/rja/Documents/Coding/film-photo-archive-manager/data/filmCollectionTest/2023']

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
        self._import_rolls() # Import all rolls
        
        
        
        # self.stock_list = self._build_stock_list()
        self._process_rolls()
        print("Collection imported!")
        # self.get_size()
        self.plot = self.Plot(self)
    
    # Adds rolls to collection from a given directory
    def add_rolls_from_directory(self, folderDir):
        # List all subdirectories in folderDir
        subfolders = os.listdir(folderDir)
        
        # Sort subfolders by numeric prefix (before '_') if it exists
        sorted_subfolders = sorted(
            subfolders,
            key=lambda x: int(x.split('_')[0]) if x.split('_')[0].isdigit() else float('inf')
        )
        
        # Loop through each sorted subfolder and add to rolls
        for subFolder in sorted_subfolders:
            # skip ds_store files
            if subFolder == '.DS_Store': continue
            subdirectory = os.path.join(folderDir, subFolder)
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
            print(f"[I]\tImporting from {directory}...")
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
        # stock = {
        #     'manufacturer': '',
        #     'stock': '',
        #     'boxspeed': '',
        #     'stk': '',
        #     'process': 'C41',
        #     'isColor': False,
        #     'isBlackAndWhite': False,
        #     'isInfrared': False,
        #     'isNegative': False,
        #     'isSlide': False
        # }

        EK100 = {
            'manufacturer': 'Kodak',
            'stock': 'Ektar 100',
            'boxspeed': '100',
            'stk': 'EK100',
            'process': 'C41',
            'isColor': True,
            'isBlackAndWhite': False,
            'isInfrared': False,
            'isNegative': True,
            'isSlide': False
        }

        G200 = {
            'manufacturer': 'Kodak',
            'stock': 'Gold 200',
            'boxspeed': '200',
            'stk': 'G200',
            'process': 'C41',
            'isColor': True,
            'isBlackAndWhite': False,
            'isInfrared': False,
            'isNegative': True,
            'isSlide': False
        }

        P400 = {
            'manufacturer': 'Kodak',
            'stock': 'Portra 400',
            'boxspeed': '400',
            'stk': 'P400',
            'process': 'C41',
            'isColor': True,
            'isBlackAndWhite': False,
            'isInfrared': False,
            'isNegative': True,
            'isSlide': False
        }

        K400 = {
            'manufacturer': 'Harman',
            'stock': 'Kentmere 400',
            'boxspeed': '400',
            'stk': 'K400',
            'process': 'BNW',
            'isColor': False,
            'isBlackAndWhite': True,
            'isInfrared': False,
            'isNegative': True,
            'isSlide': False
        }

        FP4 = {
            'manufacturer': 'Ilford',
            'stock': 'FP4 125',
            'boxspeed': '125',
            'stk': 'FP4',
            'process': 'BNW',
            'isColor': False,
            'isBlackAndWhite': True,
            'isInfrared': False,
            'isNegative': True,
            'isSlide': False
        }

        self.stocklist = {
            'EK100': EK100,
            'G200': G200,
            'P400': P400,
            'K400': K400,
            'FP4': FP4
        }

    def build_cameralist(self): # TODO: make this better and more robust. make a script to scrape excel file to build list more easily
        # CAMERA = {
        #     'brand': '',
        #     'model': '',
        #     'id': '',
        #     'serial': '',
        #     'filmtype': '',
        #     'filmformat': ''
        # }

        F3 = {
            'brand': 'Nikon',
            'model': 'F3',
            'id': 'F3',
            'serial': '',
            'filmtype': '135',
            'filmformat': '35mm'
        }

        R35S = {
            'brand': 'Rollei',
            'model': '35S',
            'id': 'R35S',
            'serial': '',
            'filmtype': '135',
            'filmformat': '35mm'
        }

        P6X7 = {
            'brand': 'Pentax',
            'model': '6x7',
            'id': 'P6X7',
            'serial': '',
            'filmtype': '120',
            'filmformat': '6X7'
        }

        self.cameralist = {
            'F3': F3,
            'R35S': R35S,
            'P6X7': P6X7,
            'Pentax 6x7': P6X7,
            'Pentax 6X7': P6X7
        }