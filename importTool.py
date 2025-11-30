import numpy as np
import pandas as pd
import sys
import os
from tkinter import Tk
from tkinter.filedialog import askdirectory


class importTool:
    def __init__(self):
        return
    
    # Opens a roll from a path and checks to confirm validity
    def get_photo_name(self, img):
        # Define new file naming convention
        #[YYMMDD]_[index]_[stk]_[location]_[cam]_[lns]_[rating]
        date = img.dateExposed
        index = img.index
        stk = img.stk
        cam = img.cam
        lns = img.lns
        location = img.state
        rating = img.rating

        date_str = date.strftime('%y%m%d') if date is not None else '??????'
        index_str = f"{int(index):02d}" if index is not None else '??'

        # handle VC
        if img.isCopy:
            if img.isStitched or img.isPano:
                new_name = f"{date_str}_{index_str}_{stk}_{location}_{cam}_{lns}_{rating}s_pano"
            elif img.isGrayscale:
                new_name = f"{date_str}_{index_str}_{stk}_{location}_{cam}_{lns}_{rating}s_BW"
            else:
                new_name = f"{date_str}_{index_str}_{stk}_{location}_{cam}_{lns}_{rating}s_edit"
        else:
            new_name = f"{date_str}_{index_str}_{stk}_{location}_{cam}_{lns}_{rating}s"

        return new_name











# Library to handle file loading/offloading from local drive to external drive.
# In short:
# 1. Load RAW, JPG, or PNG files from external drive to external drive.
# 2. Offload RAW, JPG, or PNG files from local drive to external drive. (re-sync)
# 3. Delete files from local drive after offloading.
# 4. Identify file changes and update accordingly.
# 5. Log operations for tracking.



# File structure

#   /photography/
#       /digital/
#           /projects/
#           /photos/
#               /astro/
#               /landscape/...
#           /videos/
#       /film/
#           /projects/
#           /library/
#               /2020/
#                   /1_22-06-06 EK100 F3 Stockholm & Flims/
#                   ...
#                   /XX_YY-MM-DD [STK] [CAM] [LOCATION(S)]/
#                       /scans/         (raw files)
#                       /exports/       (jpg/png files)
#                       /previews/      (low-res files)
#                       /edits/         (edites / virtual copies)
#                       /other/
#               /2021/
#                   ...
#           /archive/
#       /temp/
#       /other/


