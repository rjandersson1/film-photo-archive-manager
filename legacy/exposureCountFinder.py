from pathlib import Path



def first_jpg_in(dirpath: Path):
    for f in dirpath.iterdir():
        if f.is_file() and f.suffix.lower() == '.jpg':
            return f.name
    return None

def main():
    # folder_path = Path('/Volumes/NVME_B/backup_NVME_A_08.05.2025/A_Documents/Photography/Film Scanning/2023 - 135')
    folder_path = Path('/Volumes/NVME_B/backup_NVME_A_08.05.2025/A_Documents/Photography/Film Scanning/Backup/2023 - 120')
    count = 0
    case = 99
    for sub in sorted((p for p in folder_path.iterdir() if p.is_dir()), key=lambda x: int(x.name.split('_')[0])):
        index = sub.name.split('_')[0]  # Extract index from folder name
        # 1) first .jpg directly in the subfolder
        first = first_jpg_in(sub)
        # if first:
        #     count += 1
        #     exposure = first.split('.jpg')[0].split(' ')[-1]  # Extract exposure from filename
        #     print(exposure)
        #     # print(f"[{count}] {sub.name}\n.........................................................{first} = [{exposure}]")   

        # 2) look into any sub-subfolders
        for subsub in sorted((p for p in sub.iterdir() if p.is_dir()), key=lambda x: int(x.name.split('_')[0]) if x.name.split('_')[0].isdigit() else x.name):
            first2 = first_jpg_in(subsub)
            if first2:
                name = first2.split('.jpg')[0]
                count += 1
                exposure = name.split(' ')[-1] # Case 1: 22-10-02 Ektar 100 Seebach 1.jpg
                case = 1
                if not exposure.isdigit():
                    if ' - ' in first2:
                        if 's' in name.split(' - ')[-1]:
                            exposure = name.split(' - ')[1] # Case 2: 22-07-28 - 1 - Flims - Superia 400 -  - 5s.jpg
                            case = 2
                        if '#' in exposure:
                            exposure = name.split(' - ')[-1].split('#')[-1] # Case 3: 23-01-01 - Zurich - Ektar 100 - F3 - 3s - #2.jpg
                            case = 3
                if not exposure.isdigit():
                    if exposure.startswith('2022'): continue # Illegitimate file: camera exposure info from iPhone, skipping
                    exposure = '❌❌❌'
                if exposure.isdigit():
                    exposure = f'✅{case}✅ #{exposure}'
                
                # if case == 3:
                #     print(f"[{index}] {sub.name}\n[{exposure}].......................................................{first2}\n\n")

                print(f"[{index}] {sub.name}\n[{exposure}].......................................................{first2}\n\n")




if __name__ == "__main__":
    print("\n\n\n\n\n\n\n\n\n\n\n\n")
    main()