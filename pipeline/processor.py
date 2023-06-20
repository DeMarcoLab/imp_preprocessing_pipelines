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
from datetime import datetime
from pathlib import Path

# from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver as Observer # Needed for CIFS
from watchdog.events import FileSystemEventHandler

from pipeline import pipeline
from mongo import MongoDB
from qat_api import QatAPI
from doi_api import DoiAPI

# Set logging config
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# Confirm if folder if completely uploaded
def validate_folder(folder):
    # Load config
    try:
        with open(folder/"metadata.json", "r") as f:
            config = json.loads(f.read())
    except:
        print("metadata.json not found")
        return False
    
    # Confirm metadata is correctly structured
    # Note that proteomics is optional and not required
    try:
        keys = [
            "name",
            "description",
            "parent_volume",
            "object_volumes",
            "object_coordinates",
            "object_names",
            "subclasses",
            "other_files"
        ]
        assert set(keys).issubset(config.keys())
    except:
        print("Config is not structured correctly")
        return False
    
    # Confirm that referenced files exist
    try:
        files = [config["parent_volume"]] + config["object_volumes"] + [config["object_coordinates"]]
        if config.get("proteomics", False):
            files += [config["proteomics"]]
        
        for file in files:
            assert os.path.isfile(folder/file)
    except:
        print(f"A referenced file did not exist ({file})")
        return False
    
    # Confirm that the number of names match the number volumes
    try:
        assert len(config["object_names"]) == len(config["object_volumes"])
    except:
        print("There is a mismatch between the number of object volumes given and the number of object names")
        return False
    
    # The dataset folder is ready for processing
    # Note that this does not check if the dataset's files are well formed
    # Checking this would involve loading these assets into memory, 
    # which may be memory intensive and may as well happen during processing
    return True


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
        # Note that we need to add a check for malformed datasets and alert the user
        if validate_folder(self.path/dataset):
            self.qat.email_received(dataset)
            print(f"Valid dataset detected! Adding {dataset} to queue...")
            self.lock.acquire()
            self.queue.put(dataset)
            self.lock.release()


# Class to handle processing of IMP workloads
class ImpProcesser():
    def __init__(self, input_path, staging_path, hosting_path, mongo_config, qat_config, doi_config, test=False):
        # Set paths
        self.input_path = Path(input_path)
        self.staging_path = Path(staging_path)
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
        
        # QAT
        with open(qat_config) as file:
            self.qat = QatAPI(json.load(file))

        # DOI
        with open(doi_config) as file:
            self.doi = DoiAPI(json.load(file))

        # Populate list of inputs
        self.populate()
    
    def populate(self):
        existing = os.listdir(self.input_path)
        print(f"Adding {len(existing)} existing dataset(s) to the queue...")
        for dataset in os.listdir(self.input_path):
            if validate_folder(self.input_path/dataset):
                self.queue.put(dataset)
                self.qat.email_received(dataset)
    
    def queueHandler(self):
        while self.cont:
            if not self.queue.empty():
                try:
                    self.lock.acquire()
                    dataset = self.queue.get()
                    self.lock.release()

                    print(f"Processing {dataset}")
                    with open(self.input_path/dataset/"metadata.json", "r") as f:
                        config = json.loads(f.read())

                    print("Creating database entry...")
                    # This should extract the orcid user from the market-storage somehow in the future
                    foldername = f"{config['name']}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    record = self.mongodb.insert(config["name"], foldername, config["description"], config["orcid"], proteomics=config.get("proteomics", False))

                    print("Running pipeline...")
                    pipeline(self.input_path/dataset, self.staging_path/foldername, test=self.test)

                    print(f"Making dataset available over web...")
                    shutil.copytree(self.staging_path/foldername, self.hosting_path/foldername)
                    input_files = [config["parent_volume"]] + config["object_volumes"] + config["other_files"]
                    for file in input_files:
                        shutil.copy(self.input_path/dataset/file, self.hosting_path/foldername/file)
                    self.mongodb.update_processed(record.inserted_id)
                    
                    print(f"Cleaning up...")
                    shutil.rmtree(self.staging_path/foldername)
                    if not self.test:
                        shutil.rmtree(self.input_path/dataset)
                    
                    print(f"Minting doi...")
                    res = self.doi.mint({
                        "id": record.inserted_id,
                        "url": f'{self.mongodb.config["file_host"]}/{foldername}/',
                        "attributes": config["doi_attributes"]
                    })
                    if "errors" in res:
                        raise Exception(f"DOI was not minted successfully. Error response from server: {res['errors']}")
                    
                    self.qat.email_completed(dataset)
                    print(f"Processing of {dataset} complete!")

                except Exception as e:
                    print("Dataset corrupted!")
                    print(e)
                    self.qat.email_corrupted(dataset, e)
                    print("Skipping dataset and cleaning up artefacts...")

                    # Remove generated files
                    try:
                        shutil.rmtree(self.staging_path/foldername)
                    except:
                        pass
                    
                    # Remove dataset from database
                    try:
                        record = self.mongodb.delete(record.inserted_id)
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
    parser.add_argument("hosting_path")
    parser.add_argument("mongo_config")
    parser.add_argument("qat_config")
    parser.add_argument("doi_config")
    parser.add_argument("-t", "--test", action="store_true",
                        help="Test the pipeline using only the 'head' of the particle table without cleaning up any generated files.")
    args = parser.parse_args()

    # Init and Run processor
    imp = ImpProcesser(args.input_path, args.staging_path, args.hosting_path, args.mongo_config, args.qat_config, args.doi_config, test=args.test)
    imp.run()