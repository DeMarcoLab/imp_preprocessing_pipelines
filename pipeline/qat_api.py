import json
import requests
import os

class QatAPI():
    def __init__(self, config):
        self.username = config["username"]
        self.api_key = config["api_key"]
        self.server = config["server"]
        self.headers = {
            "Authorization": f"ApiKey {self.username}:{self.api_key}",
            "Content-Type": "application/json"
        }

    def handle_response(self, rsp):
        """
        Handle API call response
        """
        try:
            data = json.loads(rsp.content)
        except:
            raise Exception("Unexpected data received from the server.")
        
        return data
    
    def get(self, query):
        return self.handle_response(requests.get(query, headers=self.headers))

    def get_email(self, ds_id):
        # Get dataset data to determine experiment id
        data =  self.get(f"{self.server}/api/v1/dataset/{ds_id}/")
        experiments = data['experiments'][0]
        exp_id = experiments.split("/")[-2]

        # Get experiment data to determine user id
        exp_object = self.get(f"{self.server}/api/v1/experiment/{exp_id}/?id=")
        user_id = exp_object['owner_ids'][0]

        # Get user data and return email
        user_object = self.get(f"{self.server}/api/v1/user/{user_id}/")
        return user_object["email"]    

if __name__ == "__main__":
    # Load config
    with open("qat_config.json") as file:
        config = json.load(file)

    # Test qat
    qat = QatAPI(config)
    datasets = os.listdir("/market-file/input/")

    # Get email for each dataset
    for ds in datasets:
        ds_id = ds.split("-")[-1]
        print(f"Dataset: {ds}, id: {ds_id}, email: {qat.get_email(ds_id)}")