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
#                       /scans/
#                       /exports/
#                       /previews/
#                       /edits/
#                       /other/
#               /2021/
#                   ...
#           /archive/
#       /temp/
#       /other/
#