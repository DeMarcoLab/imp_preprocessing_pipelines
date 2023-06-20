import json
import requests

class DoiAPI():
    def __init__(self, config):
        # API
        self.api_key = config["api_key"]
        self.server = config["server"]
        self.prefix = config["prefix"]
        self.headers = {
            "authorization": f"Basic {self.api_key}",
            "content-type": "application/vnd.api+json"
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
    
    def post(self, query, body):
        return self.handle_response(requests.post(query, body, headers=self.headers))
    
    def mint(self, doi_object):
        return self.post(f"{self.server}/dois", json.dumps({
            "data": {
                "id": f"{self.prefix}/{doi_object['id']}",
                "type": "dois",
                "attributes": {
                    "event": "publish",
                    "doi": f"{self.prefix}/{doi_object['id']}",
                    "creators": doi_object['attributes']['creators'],
                    "titles": doi_object['attributes']['titles'],
                    "publisher": doi_object['attributes']['publisher'],
                    "publicationYear": doi_object['attributes']['publication_year'],
                    "types": {
                        "resourceTypeGeneral": 'Dataset'
                    },
                    "url": doi_object['url'], # Map this to hosted
                    "schemaVersion": 'http://datacite.org/schema/kernel-4'
                }
            }
        }))

if __name__ == "__main__":
    # Load config
    with open("doi_config.json") as file:
        config = json.load(file)

    # Test qat
    doi = DoiAPI(config)
    doi_object = {
        "id": 'test_identifier212',
        "url": 'https://webdev.imp-db.cloud.edu.au:3002/folderhost',
        "attributes": {
            "creators": [{
                "name": 'Your research group'
            }],
            "titles": [{
                "title": 'Test Dataset'
            }],
            "publisher": 'IMP Platform',
            "publication_year": 2023,
        }
    }

    # Mint a test DOI
    print(doi.mint(doi_object))