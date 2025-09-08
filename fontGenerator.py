# fontGenerator.py

# Input: stocklist.xlsx
# Output: stocklist.xlsx

# Takes in filmstocks and emulsion info (c41, bw, slide) and randomizes font color within a predetermined range.

# Sampled Color Values:
HEX_C41 = [
    '#FFB95C',
    '#FFBE61',
    '#FAA040',
    '#EFA940',
    '#EC9036',
    '#FFF6E5',
    '#E5B395',
    '#F7CC87',
    '#BB8149',
    '#B68948',
    '#D5C298',
    '#D4705F',
    '#D67560',
    '#C78E01',
    '#D0860A',
    '#FFFF18',
    '#D6AB70',
    '#C49B6A',
    '#EFB170', #P400
    '#F5AC79', #P400
    '#E3A051', #P400
    '#D7AA61'  #P400
]

HEX_E6 = [
    '#B08428', #fujifilm
    '#CCB463', #fujifilm
    '#DBB54A',	#fujifilm
    '#F5CB00',	#fujifilm
    '#F7DD01',	#fujifilm
    '#E5D5C5', #E100
    '#F2D6B9', #E100
    '#E3DEC9', #E100
    '#E0C9B0' #E100
]

HEX_BW = [
    '#C7C5C5',
    '#EFEFEF',
    '#A1A1A1',
    '#FCFCFC'
]

# Config
C41_RANGE = [(200, 255), (100, 255), (100, 255)]  # R, G, B ranges for C41 films 
BW_RANGE = [(200, 255), (200, 255), (200, 255)]    # R, G, B ranges for B&W films
SLIDE_RANGE = [(100, 255), (100, 255), (200, 255)] # R G, B ranges for Slide films
STOCKLIST_PATH = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/stocklist.xlsx'


import pandas as pd
import numpy as np
import random
from openpyxl import load_workbook

def main():
    df = import_stocklist()
    # df['fontColor'] = df.apply(generate_font_color, axis=1) # generate using random range defined by **_RANGE
    df['fontColor'] = df.apply(randomize_font_color, axis=1)
    df.to_excel(STOCKLIST_PATH, index=False)
    

# Import excel
def import_stocklist():
    df = pd.read_excel(STOCKLIST_PATH)
    return df

# Filter through each stock
def generate_font_color(row):
    isColor = row['isColor']
    isBlackAndWhite = row['isBlackAndWhite']
    isSlide = row['isSlide']
    
    if isColor and not isBlackAndWhite and not isSlide:
        r = random.randint(*C41_RANGE[0])
        g = random.randint(*C41_RANGE[1])
        b = random.randint(*C41_RANGE[2])
    elif isBlackAndWhite and not isColor and not isSlide:
        r = random.randint(*BW_RANGE[0])
        g = random.randint(*BW_RANGE[1])
        b = random.randint(*BW_RANGE[2])
    elif isSlide and not isColor and not isBlackAndWhite:
        r = random.randint(*SLIDE_RANGE[0])
        g = random.randint(*SLIDE_RANGE[1])
        b = random.randint(*SLIDE_RANGE[2])
    else:
        # Default to white if multiple or no emulsion types are specified
        r, g, b = 255, 255, 255
    
    return f'{r}, {g}, {b}, 255'


def randomize_font_color(row):
    isColor = row['isColor']
    isBlackAndWhite = row['isBlackAndWhite']
    isSlide = row['isSlide']
    
    if isColor and not isBlackAndWhite and not isSlide:
        hex_color = random.choice(HEX_C41)
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        
    elif isBlackAndWhite and not isColor and not isSlide:
        hex_color = random.choice(HEX_BW)
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        
    elif isSlide and not isColor and not isBlackAndWhite:
        hex_color = random.choice(HEX_E6)
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        
    else:
        # Default to red if multiple or no emulsion types are specified
        r, g, b = 255, 0, 0
    
    return f'{r}, {g}, {b}, 255'


if __name__ == "__main__":
    main()