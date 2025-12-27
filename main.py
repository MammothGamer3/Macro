import time
import threading
import keyboard
from collections import deque
import sys
import os

# First row
# Left Side
a = "e"
b = "2"
c = "1"
d = "tab"

# Right Side
e = "p"
f = "="
g = "backspace"
h = "\\"

# Second row
# Left side
i = "space"
j = "c"
k = "shift"
l = "delete"

# Right Side
m = ","
n = "."
o = "h"
p = "enter"

# Extra
q = "s"
r = "d"
s = "f"
t = "g"
u = "j"
v = "k"
w = "l"
s = ";"

Keys = [

]

Timing = [

]

HoldTimes = [

]

note_index = 0
macro_running = False
macro_thread = None
stop_event = threading.Event()
macro_lock = threading.Lock()
SpeedTrial = 1.0
OriginalSpeed = 1.0

release_threads = deque(maxlen=10)
timing_adjustments = []

def set_high_priority():
    try:
        if sys.platform == 'win32':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetCurrentProcess()
            success = kernel32.SetPriorityClass(handle, 0x00000100)
            if not success:
                kernel32.SetPriorityClass(handle, 0x00000080)
            print("Process priority elevated to maximum")
    except Exception as e:
        print(f"Could not set high priority: {e}")

def validate_lengths():
    lengths = {
        "Keys": len(Keys),
        "Timing": len(Timing),
        "HoldTimes": len(HoldTimes)
    }
    max_len = max(lengths.values())
    issues = {name: max_len - length for name, length in lengths.items() if length < max_len}
    if issues:
        print("Mismatched alert")
        for name, missing in issues.items():
            current_len = lengths[name]
            print(f"    - {name} has {current_len} items, missing {missing} to match {max_len}")
        return False
    return True

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def release_key_precise(key: str, release_time: float):
    def release():
        remaining = release_time - time.perf_counter()
        if remaining > 0.003:
            time.sleep(remaining - 0.002)
        while time.perf_counter() < release_time:
            pass
        keyboard.release(key)
    
    thread = threading.Thread(target=release, daemon=True)
    thread.start()
    release_threads.append(thread)

def macro_loop():
    global note_index, macro_running, timing_adjustments

    if not validate_lengths():
        macro_running = False
        return

    print("\nMacro started")
    macro_running = True
    stop_event.clear()

    start_time = time.perf_counter()
    cumulative = 0.0

    while note_index < len(Keys):
        # Check stop frequently
        if stop_event.is_set():
            break

        base_timing = (Timing[note_index] * OriginalSpeed) / SpeedTrial
        adjusted_hold = (HoldTimes[note_index] * OriginalSpeed) / SpeedTrial
        current_adjustment = timing_adjustments[note_index]
        adjusted_timing = base_timing + current_adjustment
        
        target = start_time + (cumulative / 1000.0)
        release_time = target + (adjusted_hold / 1000.0)
        
        # Phase 1: Coarse sleep for long waits
        now = time.perf_counter()
        remaining = target - now
        
        if remaining > 0.005:
            time.sleep(remaining - 0.004)
        
        # Phase 2: Fine sleep with live adjustments and frequent stop checks
        while True:
            if stop_event.is_set():
                break
                
            now = time.perf_counter()
            current_adjustment = timing_adjustments[note_index]
            target = start_time + ((cumulative + current_adjustment) / 1000.0)
            remaining = target - now
            
            if remaining <= 0.0005:
                break
            
            if remaining > 0.001:
                time.sleep(0.0001)
            else:
                break
        
        if stop_event.is_set():
            break
        
        # Phase 3: Final adjustment and busy-wait for precision
        current_adjustment = timing_adjustments[note_index]
        adjusted_timing = base_timing + current_adjustment
        target = start_time + ((cumulative + current_adjustment) / 1000.0)
        release_time = target + (adjusted_hold / 1000.0)
        
        while time.perf_counter() < target:
            if stop_event.is_set():
                break
        
        if stop_event.is_set():
            break
        
        # Execute key press
        key = Keys[note_index]
        keyboard.press(key)
        release_key_precise(key, release_time)

        cumulative += adjusted_timing
        note_index += 1

    # Cleanup
    for thread in list(release_threads):
        if thread.is_alive():
            thread.join(timeout=0.2)

    if stop_event.is_set():
        print("Macro stopped")
    else:
        print("Macro finished")

    macro_running = False

def start_macro():
    global macro_thread, note_index, timing_adjustments, Keys
    with macro_lock:
        if macro_running:
            print("Macro is already running")
            return

        note_index = 0
        stop_event.clear()
        
        if len(timing_adjustments) == 0 and len(Keys) > 0:
            timing_adjustments = [0] * len(Keys)
        
        macro_thread = threading.Thread(target=macro_loop, daemon=True)
        macro_thread.start()

def stop_macro():
    global macro_running, note_index
    with macro_lock:
        if not macro_running:
            print("Macro is not running yet")
            return

        stop_event.set()
        
        if macro_thread and macro_thread.is_alive():
            macro_thread.join(timeout=0.5)
        
        for key in set(Keys):
            try:
                keyboard.release(key)
            except Exception:
                pass
        
        note_index = 0
        macro_running = False

def adjust_next_timing_faster():
    global timing_adjustments, note_index, Keys
    
    if len(Keys) == 0:
        return
    
    if len(timing_adjustments) == 0:
        timing_adjustments = [0] * len(Keys)
    elif len(timing_adjustments) != len(Keys):
        old_adjustments = timing_adjustments[:]
        timing_adjustments = [0] * len(Keys)
        for i in range(min(len(old_adjustments), len(Keys))):
            timing_adjustments[i] = old_adjustments[i]
    
    target_index = note_index if note_index < len(Keys) else 0
    timing_adjustments[target_index] -= 1

def adjust_next_timing_slower():
    global timing_adjustments, note_index, Keys
    
    if len(Keys) == 0:
        return
    
    if len(timing_adjustments) == 0:
        timing_adjustments = [0] * len(Keys)
    elif len(timing_adjustments) != len(Keys):
        old_adjustments = timing_adjustments[:]
        timing_adjustments = [0] * len(Keys)
        for i in range(min(len(old_adjustments), len(Keys))):
            timing_adjustments[i] = old_adjustments[i]
    
    target_index = note_index if note_index < len(Keys) else 0
    timing_adjustments[target_index] += 1

def reset_timing_adjustments():
    global timing_adjustments
    if len(Keys) > 0:
        timing_adjustments = [0] * len(Keys)
        print("All timing adjustments reset to 0ms")
    else:
        print("No keys in macro to reset")

def main():
    global SpeedTrial
    set_high_priority()
    
    try:
        SpeedTrial = float(input("Speed: "))
        if SpeedTrial <= 0:
            print("Speed must be positive")
            return
    except ValueError:
        print("Invalid speed input")
        return
    
    clear_console()

    print(f"Macro is ready to run at {SpeedTrial}x speed.")
    print("\n=== Controls ===")
    print("F8: Start macro")
    print("F9: Stop and reset macro")
    print("Up Arrow: Make next input 1ms faster (PERMANENT)")
    print("Down Arrow: Make next input 1ms slower (PERMANENT)")
    print("F10: Reset all timing adjustments")
    print("\nNote: Adjustments persist across runs until F10 pressed")
    
    keyboard.add_hotkey("f8", start_macro)
    keyboard.add_hotkey("f9", stop_macro)
    keyboard.add_hotkey("up", adjust_next_timing_faster)
    keyboard.add_hotkey("down", adjust_next_timing_slower)
    keyboard.add_hotkey("f10", reset_timing_adjustments)
    keyboard.wait()

if __name__ == "__main__":
    main()
