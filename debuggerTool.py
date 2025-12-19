import numpy as np

class debuggerTool:

    def __init__(self, on_debug=1, on_warning=1, on_error=1):
        self.on_debug = on_debug
        self.on_warning = on_warning
        self.on_error = on_error

        self.col_err = "[35m"
        self.col_war = "[31m"
        self.col_debug = "[33m"

        # self.col_err = "[37;45m"  # white text on purple background
        # self.col_war = "[30;43m"  # black text on red background
        # self.col_debug = "[30;44m"  # black text on blue background

        self.col_data = "[90m"
        self.col_data2 = "[37m"
        self.col_data3 = "[90m"

        print(self.colorize_str("Debugger tool initialized.", self.col_debug))

        return
    
    def colorize_str(self, test, col):
        return f"\033{col}{test}\033[0m"
    
    def d(self, pre, post, data=None):
        if self.on_debug:
            self.debug('debug', pre, post, data)
    
    def e(self, pre, post, data=None):
        if self.on_error:
            self.debug('error', pre, post, data)

    def w(self, pre, post, data=None):
        if self.on_warning:
            self.debug('warning', pre, post, data)

    def debug(self, mode, pre, post, data=None):
        max_pre_length = 9  # [999][999]
        spaces_after = max(max_pre_length + 2 - len(pre), 0)
        pre_padded = pre + ' ' * spaces_after
        data_padding = ' ' * (len(pre_padded) + 2)

        string_debugger = ""
        if mode == 'debug':
            string_debugger = (f"{self.colorize_str(pre_padded, self.col_debug)}{post}")
        elif mode == 'error':
            string_debugger = (f"{self.colorize_str(pre_padded, self.col_err)}{post}")
        elif mode == 'warning':
            string_debugger = (f"{self.colorize_str(pre_padded, self.col_war)}{post}")
        else:
            string_debugger = (f"{pre_padded}\033[32mINFO:\033[0m  {post}")
    
        if data is not None:
            # handle scalars
            if np.isscalar(data):
                # check length and ensure < n chars
                if len(str(data)) < 100:
                    string_debugger = string_debugger + f'\t{self.colorize_str(data, self.col_data)}'
                else:
                    string_debugger = string_debugger + f'\n{data_padding}{self.colorize_str(data, self.col_data)}'
            else:
                for item in data:
                    string_debugger = string_debugger + f"\n{data_padding}{self.colorize_str(item, self.col_data)}"
            
        print(string_debugger)

                  

# example usage
DEBUG = 0
WARNING = 0
ERROR = 1
if __name__ == "__main__":
    db = debuggerTool(DEBUG, WARNING, ERROR)

    db.d('[1][2]', 'This is a debug message.')
    db.d('[1][2]', 'This is a data message.', data='DSC01663')     
    db.d('[1][2]', 'This is a data message.', data=[1,'2',3.0])     

    db.e('[1][2]', 'This is an error message.')
    db.e('[1][2]', 'This is a data message.', data='DSC01663')
    db.e('[1][2]', 'This is a data message.', data=[1,'2',3.0])

    db.w('[1][2]', 'This is a warning message.')
    db.w('[1][2]', 'This is a data message.', data='DSC01663')
    db.w('[1][2]', 'This is a data message.', data=[1,'2',3.0])
