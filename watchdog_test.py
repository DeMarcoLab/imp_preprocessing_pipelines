import sys
import logging
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Log when created and run a shell command
class EventHandler(FileSystemEventHandler):
    def __init__(self, logger=None):
        super().__init__()
        self.logger = logger or logging.root

    def on_created(self, event):
        super().on_created(event)

        what = "directory" if event.is_directory else "file"
        self.logger.info("Created %s: %s", what, event.src_path)
        command = f"bash echo.sh {event.src_path}"
        self.process = subprocess.Popen(command, shell=True)


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# Use provided directory, else default to current directory
path = sys.argv[1] if len(sys.argv) > 1 else '.'

# Create and start handler and observer
event_handler = EventHandler()
observer = Observer()
observer.schedule(event_handler, path, recursive=True)
observer.start()

# Continue until exited
try:
    while observer.is_alive():
        observer.join(1)
finally:
    observer.stop()
    observer.join()