from distutils import extension
import logging
import os
import shutil
# import sys
# import subprocess
import argparse
import json

import threading
from queue import Queue
from time import sleep

from pathlib import Path

# from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver as Observer # Needed for CIFS
from watchdog.events import FileSystemEventHandler

from pipeline import pipeline
from mongo import MongoDB

# Set logging config
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# Confirm if folder if completely uploaded
def validate_folder(folder):
    # Get all files in folder
    file_list = os.listdir(folder)

    # Count each extension
    extensions = {}
    for file in file_list:
        extension = file.split(".")[-1]
        extensions[extension] = extensions.get(extension, 0) + 1

    # If all has arrived return True, else False
    if extensions.get("json", 0) >= 1 and extensions.get("mrc", 0) >= 3 and extensions.get("star", 0) >= 2:
        return True
    return False

# Log when created and run a shell command
class EventHandler(FileSystemEventHandler):
    def __init__(self, path, lock, queue, logger=None):
        super().__init__()
        self.path = path
        self.lock = lock
        self.queue = queue
        self.logger = logger or logging.root

    def on_created(self, event):
        super().on_created(event)
        print(f"Received {event.src_path}")
        new_file = Path(event.src_path)

        # The name of the dataset will be the part of the path that is immediately after the monitored path
        dataset = new_file.parts[len(self.path.parts)]

        # If the whole dataset has arrived, add to queue
        if validate_folder(self.path/dataset):
            print(f"Whole dataset detected! Adding {dataset} to queue...")
            self.lock.acquire()
            self.queue.put(dataset)
            self.lock.release()


# Class to handle processing of IMP workloads
class ImpProcesser():
    def __init__(self, input_path, staging_path, output_path, hosting_path, mongo_config, test=False):
        # Set paths
        self.input_path = Path(input_path)
        self.staging_path = Path(staging_path)
        self.output_path = Path(output_path)
        self.hosting_path = Path(hosting_path)

        # Initialise
        self.queue = Queue()
        self.lock = threading.Lock()
        self.event_handler = EventHandler(self.input_path, self.lock, self.queue)
        self.thread = None
        self.observer = None
        self.test = test
        self.cont = True

        # DB
        with open(mongo_config) as file:
            self.mongodb = MongoDB(json.load(file))

        # Populate list of inputs
        self.populate()
    
    def populate(self):
        existing = os.listdir(self.input_path)
        print(f"Adding {len(existing)} existing dataset(s) to the queue...")
        for dataset in os.listdir(self.input_path):
            if validate_folder(self.input_path/dataset):
                self.queue.put(dataset)
    
    def queueHandler(self):
        while self.cont:
            if not self.queue.empty():
                try:
                    self.lock.acquire()
                    dataset = self.queue.get()
                    self.lock.release()

                    print(f"Processing {dataset}")
                    print("Creating database entry...")
                    with open(self.input_path/dataset/"metadata.json", "r") as f:
                        config = json.loads(f.read())

                    # This should extract the orcid user from the market-storage somehow in the future
                    record = self.mongodb.insert(config["name"], config["description"], "USER")

                    print("Running pipeline...")
                    # TODO: We probably need a check that the output is empty...
                    pipeline(self.input_path/dataset, self.staging_path/dataset, self.output_path/dataset, test=self.test)

                    print(f"Cleaning up...")
                    shutil.rmtree(self.staging_path/dataset)
                    if not self.test:
                        shutil.rmtree(self.input_path/dataset)
                    
                    print(f"Making dataset available over web...")
                    self.mongodb.update_processed(record.inserted_id)
                    shutil.copytree(self.output_path/dataset, self.hosting_path/config["name"])

                    print(f"Processing of {dataset} complete!")

                except Exception as e:
                    print("Dataset corrupted!")
                    print(e)
                    print("Skipping dataset and cleaning up artefacts...")

                    try:
                        shutil.rmtree(self.staging_path/dataset)
                    except:
                        pass

                    try:
                        shutil.rmtree(self.output_path/dataset)
                    except:
                        pass
            else:
                sleep(5)
    
    def run(self):
        # Start thread
        self.cont = True
        self.thread = threading.Thread(target=self.queueHandler)
        self.thread.start()
        print("Starting processing thread...")

        # Create and start handler and observer
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.input_path, recursive=True)
        self.observer.start()
        print(f"Observing {self.input_path} for new inputs...")

        try:
            while self.observer.is_alive():
                self.observer.join(1)
        finally:
            self.observer.stop()
            self.stop()
            self.observer.join()
            self.thread.join()
    
    def stop(self):
        print("Stopping after this process...")
        self.cont = False

if __name__ == "__main__":
    # Parse inputs
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path")
    parser.add_argument("staging_path")
    parser.add_argument("output_path")
    parser.add_argument("hosting_path")
    parser.add_argument("mongo_config")
    parser.add_argument("-t", "--test", action="store_true",
                        help="Test the pipeline using only the 'head' of the particle table without cleaning up any generated files.")
    args = parser.parse_args()

    # Init and Run processor
    imp = ImpProcesser(args.input_path, args.staging_path, args.output_path, args.hosting_path, args.mongo_config, test=args.test)
    imp.run()