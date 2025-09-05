import os
import shutil

# target_path = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/filmCollectionTest/2022/11_22-10-03 Ektar 100 Zurich Flims Andeer/Negatives'
# new_path = r'/Users/rja/Documents/Coding/film-photo-archive-manager/data/filmCollectionTest/2022/11_22-10-03 Ektar 100 Zurich Flims Andeer/Negatives_2'
# for file in os.listdir(target_path):
#     splitname = file.split('-')[0]
#     newname = splitname + ".ARW"
#     if len(newname) != 12:
#         print(file, splitname, newname)
#         continue

#     src = os.path.join(target_path, file)
#     dst = os.path.join(new_path, newname)
#     print(f'copying {file}...')
#     shutil.copyfile(src, dst)


    #

src_dir = r'/Users/rja/Desktop/10_22-10-02 Ektar 100 OM Accura ZH+Andeer+Flims/raw'
dst_dir = r'/Users/rja/Desktop/10_22-10-02 Ektar 100 OM Accura ZH+Andeer+Flims/raw2'
keys = [
    'DSC01374',
    'DSC01377',
    'DSC01380',
    'DSC01383',
    'DSC01386',
    'DSC01389',
    'DSC01392',
    'DSC01397',
    'DSC01400',
    'DSC01403',
    'DSC01406',
    'DSC01409',
    'DSC01412',
    'DSC01415',
    'DSC01445',
    'DSC01421',
    'DSC01424',
    'DSC01427',
    'DSC01430',
    'DSC01434',
    'DSC01439',
    'DSC01442',
    'DSC01449',
    'DSC01468',
    'DSC01482',
    'DSC01485',
    'DSC01488'
]


match_count = 0
matched = False
no_matches = []
for file in os.listdir(src_dir):
    matched = False
    for key in keys:
        name = file.split(".")[0].split("-")[0]
        
        # Handle file match
        if name == key:
            print(file, key)
            match_count += 1
            matched = True
            keys.remove(key)

            src_path = os.path.join(src_dir, file)
            dst_path = os.path.join(dst_dir, name + ".dng")
            print("Moving", name,"...")
            shutil.move(src_path, dst_path)

    if not matched:
        no_matches.append(file.split(".")[0].split("-")[0])



temp = []
for match in no_matches:
    temp.append(int(match.split("DSC0")[-1]))

no_matches = temp
no_matches.sort()

temp = []
for key in keys:
    temp.append(int(key.split("DSC0")[-1]))

no_keys = temp
no_keys.sort()

print("\n\n\n")
print(no_keys, len(no_keys), " Missing keys")
print(no_matches, len(no_matches), "Missing negatives")
print("\n\n\n")




# Keys
# 1         DSC01374.ARW
# 2         DSC01377.ARW
# 3         DSC01380.ARW
# 4         DSC01383.ARW
# 5         DSC01386.ARW
# 6         DSC01389.ARW
# 7         DSC01392.ARW
# 8         DSC01397.ARW
# 9         DSC01400.ARW
# 10        DSC01403.ARW
# 11        DSC01406.ARW
# 12        DSC01409.ARW
# 13        DSC01412.ARW
# 14        DSC01415.ARW
# 15        DSC01445.ARW
# 16        DSC01421.ARW
# 17        DSC01424.ARW
# 18        DSC01427.ARW
# 19        DSC01430.ARW
# 20        DSC01434.ARW
# 21        DSC01439.ARW
# 22        DSC01442.ARW
# 23        DSC01449.ARW
# 24        DSC01468.ARW
# 25        DSC01482.ARW
# 26        DSC01485.ARW
# 27        DSC01488.ARW