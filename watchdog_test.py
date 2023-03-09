import sys
import logging
import os
import subprocess

import threading
from queue import Queue
from time import sleep

from pathlib import Path

# from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver as Observer # Needed for CIFS
from watchdog.events import FileSystemEventHandler

# Log when created and run a shell command
class EventHandler(FileSystemEventHandler):
    def __init__(self, logger=None):
        super().__init__()
        self.logger = logger or logging.root

    def on_created(self, event):
        super().on_created(event)

        print(f"received {event.src_path}")

        lock.acquire()
        queue.put(event.src_path.split("/")[-1]) # split to isolate filename
        lock.release()

        # what = "directory" if event.is_directory else "file"
        # self.logger.info("Created %s: %s", what, event.src_path)
        # command = f"bash echo.sh {event.src_path}"
        # self.process = subprocess.Popen(command, shell=True)

def queueHandler(path):
    while True:
        # Move file to output
        if not queue.empty():
            lock.acquire()
            file = queue.get()
            lock.release()

            print(f"processing {file}")
            command = f"cp '{path}/input/{file}' '{path}/output/{file}'"
            subprocess.Popen(command, shell=True).wait()
            os.remove(f"{path}/input/{file}")
        else:
            sleep(5)


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# Initialise queue
queue = Queue()
lock = threading.Lock()

# Use provided directory, else default to current directory
path = Path(sys.argv[1] if len(sys.argv) > 1 else ".")

# Prepopulate queue with unprocessed
existing = os.listdir(path/"input")
print(f"Adding {len(existing)} existing files to the queue...")
for file in os.listdir(path/"input"):
    queue.put(file)

# Create thread
thread = threading.Thread(target=queueHandler, args=(path,))
thread.start()
print("Processing inputs...")

# Create and start handler and observer
event_handler = EventHandler()
observer = Observer()
observer.schedule(event_handler, path/"input", recursive=True)
observer.start()
print(f"Observing {path/'input'} for new inputs...")

# Continue until exited
try:
    while observer.is_alive():
        observer.join(1)
finally:
    observer.stop()
    observer.join()
    thread.join()