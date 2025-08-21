
DICT = {}
dict1 = {}
dict2 = {}

dict1['a'] = 'A'
dict1['b'] = 'B'
dict2['c'] = 'C'

DICT['dict1'] = dict1
DICT['dict2'] = dict2

val = DICT['dict1']

for dict in DICT.items():
    print(dict)