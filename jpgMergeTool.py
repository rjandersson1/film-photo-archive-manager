import time
import threading
import pyautogui
from pynput import keyboard
from pynput.keyboard import Controller, Key


class rawJpgSync:

    def __init__(self):
        self.delay_default = 0.05
        self.sync_pos = None
        self.accept_event = threading.Event()
        self.stop_flag = False
        self.shift_pressed = False

        self.waitForAccept = True
        self.acceptButton = "."
        self.pauseOnFinish = True

        self.kb = Controller()

        pyautogui.FAILSAFE = True

        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()

    def _on_press(self, key):
        try:
            if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
                self.shift_pressed = True

            if key == keyboard.Key.esc:
                self.stop_flag = True

            if hasattr(key, "char") and key.char == self.acceptButton:
                self.accept_event.set()

        except Exception:
            pass

    def _on_release(self, key):
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            self.shift_pressed = False

    def wait_accept(self, forceWait=False):

        if not self.waitForAccept and not forceWait:
            time.sleep(self.delay_default)
            return

        self.accept_event.clear()

        while not self.accept_event.is_set():
            if self.stop_flag:
                return
            time.sleep(0.01)

        self.accept_event.clear()

    def wait_accept_finish(self):

        if not self.pauseOnFinish:
            time.sleep(self.delay_default * 2)
            return

        self.accept_event.clear()

        while not self.accept_event.is_set():
            if self.stop_flag:
                return
            time.sleep(0.01)

        self.accept_event.clear()

    def press(self, key):
        if self.stop_flag:
            return

        key_map = {
            "left": Key.left,
            "right": Key.right,
            "up": Key.up,
            "down": Key.down,
            "enter": Key.enter,
            "return": Key.enter,
            "esc": Key.esc,
            "space": Key.space,
            "tab": Key.tab,
            "backspace": Key.backspace,
            "delete": Key.delete
        }

        k = key_map.get(key, key)

        self.kb.press(k)
        time.sleep(0.03)
        self.kb.release(k)
        time.sleep(self.delay_default)

    def hotkey(self, *keys):
        if self.stop_flag:
            return

        key_map = {
            "shift": Key.shift,
            "shift_l": Key.shift_l,
            "shift_r": Key.shift_r,
            "cmd": Key.cmd,
            "command": Key.cmd,
            "ctrl": Key.ctrl,
            "alt": Key.alt,
            "option": Key.alt,
            "left": Key.left,
            "right": Key.right,
            "up": Key.up,
            "down": Key.down,
            "enter": Key.enter
        }

        parsed = [key_map.get(k, k) for k in keys]

        for k in parsed[:-1]:
            self.kb.press(k)
            time.sleep(0.02)

        self.kb.press(parsed[-1])
        time.sleep(0.03)
        self.kb.release(parsed[-1])

        for k in reversed(parsed[:-1]):
            time.sleep(0.02)
            self.kb.release(k)

        time.sleep(self.delay_default)

    def calibrate(self):

        print("\nCALIBRATION")
        print("Move the mouse to the 'Sync Metadata..' button.")
        print(f"Press <{self.acceptButton}> to confirm position.\n")

        self.wait_accept(forceWait=True)

        self.sync_pos = pyautogui.position()

        print(f"Captured sync button position: {self.sync_pos}")

    def init_loop(self):

        self.press("/")
        self.press("left")

    def main_loop(self):

        self.press("right")
        self.hotkey("shift", "left")

        print(f"WAIT: verify pair selection, press <{self.acceptButton}>")
        self.wait_accept()

        pyautogui.moveTo(self.sync_pos)
        time.sleep(self.delay_default)

        pyautogui.click()
        time.sleep(self.delay_default)

        self.press("enter")

        print(f"WAIT: metadata applied, press <{self.acceptButton}>")
        self.wait_accept()

        print("Sending 8")
        self.press("8")

        print("Sending b")
        self.press("b")

        print(f"WAIT: proceed to next pair, press <{self.acceptButton}>")
        self.wait_accept_finish()

    def run(self):

        print("\nPress ESC at any time to stop.\n")

        self.calibrate()

        if self.stop_flag:
            return

        print("\nStarting iteration in 2 seconds...")
        time.sleep(2)

        self.init_loop()

        while not self.stop_flag:
            self.main_loop()

        print("Stopped.")


if __name__ == "__main__":
    macro = rawJpgSync()
    macro.waitForAccept = False
    macro.pauseOnFinish = False
    macro.run()