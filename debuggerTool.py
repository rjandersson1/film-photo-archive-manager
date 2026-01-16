import numpy as np
import time
import sys

# TODO: handle cases when none is passed, methods will crash on NoneType at the moment

class debuggerTool:

    def __init__(self, on_debug=1, on_warning=1, on_error=1):
        self.on_debug = on_debug
        self.on_warning = on_warning
        self.on_error = on_error

        self.col_err = "[35m"
        self.col_war = "[31m"
        self.col_debug = "[33m"
        self.col_info = "[36m"
        self.col_success = "[92m"
        self.col_data = "[90m"
        # self.col_err = "[37;45m"  # white text on purple background
        # self.col_war = "[30;43m"  # black text on red background
        # self.col_debug = "[30;44m"  # black text on blue background

        # progress bar state
        self._progress_active = False
        self._progress_last_len = 0
        self._progress_last_time = 0.0
        self._progress_start_time = None
        return
    
    def colorize(self, str, col):
        return f"\033{col}{str}\033[0m"
    
    def i(self, pre, post, data=None):
        self.debug('info', pre, post, data)
    
    def s(self, pre, post, data=None):
        self.debug('success', pre, post, data)
    
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
        # Handle NoneType
        if pre is None:
            pre = ''
        if post is None:
            post = ''
        
        max_pre_length = 9  # [999][999]
        spaces_after = max(max_pre_length + 2 - len(pre), 0)
        pre_padded = pre + ' ' * spaces_after
        data_padding = ' ' * (len(pre_padded) + 2)

        string_debugger = ""
        if mode == 'debug':
            string_debugger = (f"{self.colorize(pre_padded, self.col_debug)}{post}")
        elif mode == 'error':
            string_debugger = (f"{self.colorize(pre_padded, self.col_err)}{post}")
        elif mode == 'warning':
            string_debugger = (f"{self.colorize(pre_padded, self.col_war)}{post}")
        elif mode == 'success':
            string_debugger = (f"{self.colorize(pre_padded, self.col_success)}{post}")
        elif mode == 'info':
            string_debugger = (f"{self.colorize(pre_padded, self.col_info)}{post}")
        else:
            string_debugger = (f"{pre_padded}\033[32mINFO:\033[0m  {post}")
    
        if data is not None:
            # handle scalars
            if np.isscalar(data):
                # check length and ensure < n chars
                if len(str(data)) < 100:
                    string_debugger = string_debugger + f'\t{self.colorize(data, self.col_data)}'
                else:
                    string_debugger = string_debugger + f'\n{data_padding}{self.colorize(data, self.col_data)}'
            else:
                for item in data:
                    string_debugger = string_debugger + f"\n{data_padding}{self.colorize(item, self.col_data)}"
            
        print(string_debugger)


    def progress(
        self,
        pre: str,
        current: int,
        total: int,
        post: str = "",
        *,
        width: int = 28,
        mode: str = "info",
        every: float = 0.03,
        show_eta: bool = True
    ):
        if total <= 0:
            total = 1
        if current < 0:
            current = 0
        if current > total:
            current = total

        now = time.time()
        if (now - self._progress_last_time) < every and current != total:
            return

        if not self._progress_active and current != total:
            self._progress_active = True
            self._progress_start_time = now

        frac = current / total
        filled = int(frac * width)
        bar_raw = "█" * filled + " " * (width - filled)
        pct = int(frac * 100)

        # ETA
        eta_str = ""
        if show_eta and current > 0 and current < total and self._progress_start_time is not None:
            elapsed = now - self._progress_start_time
            rate = elapsed / current
            eta = rate * (total - current)
            eta_str = f"  ETA {eta:5.1f}s"
        elif show_eta and current == total and self._progress_start_time is not None:
            elapsed = now - self._progress_start_time
            eta_str = f"  {elapsed:5.1f}s"

        # prefix padding
        max_pre_length = 9
        spaces_after = max(max_pre_length + 2 - len(pre), 0)
        pre_padded = pre + " " * spaces_after

        # prefix color
        col = self.col_info
        if mode == "success":
            col = self.col_success
        elif mode == "debug":
            col = self.col_debug
        elif mode == "warning":
            col = self.col_war
        elif mode == "error":
            col = self.col_err

        prefix = self.colorize(pre_padded, col)

        if current == total:
            bar = self.colorize(bar_raw, self.col_success)
        else:
            bar = bar_raw

        if current != total:
            line = f"{prefix}[{bar}] {pct:3d}% ({current}/{total}) {post}{eta_str}"
        if current == total:
            line = f"{prefix}[{bar}] {pct:3d}% ({current}/{total}) {post}{eta_str}"

        pad = max(self._progress_last_len - len(line), 0)
        out = "\r" + line + (" " * pad)
        if current == total and mode == 'success':
            out = out + '\n'

        sys.stdout.write(out)
        sys.stdout.flush()

        self._progress_last_len = len(line)
        self._progress_last_time = now

        if current == total:
            self._progress_last_time = 0.0
            self._progress_active = False

                  

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

    db.i('[1][2]', 'This is an info message.')
    db.i('[1][2]', 'This is a data message.', data='DSC01663')
    db.i('[1][2]', 'This is a data message.', data=[1,'2',3.0]) 

    db.s('[1][2]', 'This is a success message.')
    db.s('[1][2]', 'This is a data message.', data='DSC01663')
    db.s('[1][2]', 'This is a data message.', data=[1,'2',3.0])



    print("\n--- Progress demo ---\n")

    # Simulate a roll with images + steps
    roll_index = 72
    images = 34
    steps_per_image = 3  # RAW, JPG, preview
    total_steps = images * steps_per_image

    done = 0

    for img_idx in range(images):
        for step in ("RAW", "JPG", "preview"):
            # simulate work
            time.sleep(0.01)

            done += 1
            db.progress(
                pre=f"[{roll_index}]",
                current=done,
                total=total_steps,
                post=f"[{roll_index}][{img_idx}] Copied {step}",
                mode="info"
            )

    # Finish the bar cleanly
    db.progress(
        pre=f"[{roll_index}]",
        current=total_steps,
        total=total_steps,
        post="Cleaned roll",
        mode="success"
    )

