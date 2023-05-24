import json
from pymongo import MongoClient

# Class to manage interactions with the MongoDB
class MongoDB():
    def __init__(self, config):
        self.config = config
        self.client = MongoClient(self.config["uri"])
        self.database = self.client[self.config["database"]]
        self.collection = self.database[self.config["collection"]]

    # Insert a new dataset entry 
    def insert(self, name, foldername, text, user, proteomics=False, privacy="public"):
        # Construct object
        dataset = {
            "image": f'{self.config["file_host"]}/{foldername}/',
            "metadata": {
                "text": text
            },
            "name": name,
            "access": {
                "privacy": privacy,
                "user": user
            },
            "layers": [
                {
                    "metadata": '',
                    "path": f'{self.config["file_host"]}/{foldername}/coordinates/',
                    "type": 'all'
                }
            ],
            "processing": True
        }

        # Optionally add proteomics
        if proteomics:
            dataset["proteomics"] = {
                "path": f'{self.config["file_host"]}/{foldername}/proteomics/proteomics.json'
            }

        # Insert to database
        return self.collection.insert_one(dataset)

    # Update a dataset entry
    def update(self, doc_id, obj):
        return self.collection.update_one({"_id": doc_id}, obj)
    
    # Update a dataset that has finished processing
    def update_processed(self, doc_id):
        return self.update(doc_id, obj={"$set": {"processing": False}})

if __name__ == "__main__":
    # Load config
    with open("mongo_config.json") as file:
        config = json.load(file)

    # Test mongo
    mongo = MongoDB(config)
    record = mongo.insert("new_insert_dataset", "some text", "mhar0048")
    mongo.update_processed(record.inserted_id)