import json
import requests
import os
import smtplib
from email.mime.text import MIMEText

class QatAPI():
    def __init__(self, config):
        # API
        self.username = config["username"]
        self.api_key = config["api_key"]
        self.server = config["server"]
        self.headers = {
            "Authorization": f"ApiKey {self.username}:{self.api_key}",
            "Content-Type": "application/json"
        }

        # Email
        self.sender = config["sender"]
        self.password = config["password"]

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

    def send_email(self, subject, body, recipients):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = ', '.join(recipients)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(self.sender, self.password)
            smtp_server.sendmail(self.sender, recipients, msg.as_string())
    
    def email_received(self, dataset):
        name, ds_id = dataset.split("-")
        subject = "IMP dataset received"
        body = f"Dear IMP User,\n\nYour dataset '{name}' has been received and has entered the queue. We will email you again when your dataset is ready for viewing."
        self.send_email(subject, body, [self.get_email(ds_id)])
    
    def email_completed(self, dataset):
        name, ds_id = dataset.split("-")
        subject = "IMP dataset completed"
        body = f"Dear IMP User,\n\nYour dataset '{name}' has completed processing and is now ready for viewing. You can now log in to the Cryoglancer Portal to view your dataset.\nhttps://cryoglancer.imp-db.cloud.edu.au/"
        self.send_email(subject, body, [self.get_email(ds_id)])

    def email_corrupted(self, dataset, error):
        name, ds_id = dataset.split("-")
        subject = "IMP dataset corrupted"
        body = f"Dear IMP User,\n\nYour dataset '{name}' failed during processing. Please double check the format and validity of your data and resubmit. If you are still having trouble, feel free to reach out to us at this email address. The exception is as follows:\n\n{error}"
        self.send_email(subject, body, [self.get_email(ds_id)])

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