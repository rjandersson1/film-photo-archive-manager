
DICT = {}
dict1 = {}
dict2 = {}

dict1['a'] = 'A'
dict1['b'] = 'B'
dict2['c'] = 'C'

DICT['dict1'] = dict1
DICT['dict2'] = dict2

val = DICT['dict1']

# for dict in DICT.items():
#     print(dict)


ektar = {'stock': 'Ektar', 'manufacturer': 'Kodak', 'stk': 'EK100'}
gold = {'stock': 'Gold', 'manufacturer': 'Kodak', 'stk': 'G200'}

stock = {
    'manufacturer': '',
    'stock': '',
    'boxspeed': '',
    'stk': '',
    'isNegative': True,
    'isPositive': False,
    'process': 'C41'
}

stocklist = {'EK100': ektar, 'G200': gold}

for stock in stocklist.values():
    print(stock['stk'])


# # Try to find stock (fall back to empty dict if missing)
# stock = self._collection.stocklist.get(key, {})
print('\n')
print('\n')
print('\n')

for key in ['EK100', 'G200', 'XYZ']:
    print(stocklist.get(key, {}))