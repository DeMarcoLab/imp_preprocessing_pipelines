# Integrated Microscopy and Proteomics (IMP) Backend

This repository hosts the back end code for the Integrated Microscopy and Proteomics (IMP) Platform. Other repositories include the [Landing Page](https://github.com/DeMarcoLab/cryoglancerLandingPage) and the [Cryoglancer Application](https://github.com/DeMarcoLab/IMP/tree/main), which is a modified neuroglancer viewer.

The repository contains:
- files marked `deprecated_`
    - Deprecated code from previous iterations of the pipeline - this is kept for reference for reference for when this functionality is reimplemented and added to the existing system (files marked `deprecated_`)
- An `environment.yml` for the python environment that the pipeline uses
- A `Dockerfile` and `docker-compose.yml` that builds a container that processes incoming datasets
- expressjs
    - The backend for communicating with the Mongo database that stores the dataset metadata
    - This is a modified example project and so while this section does serve the service adequately at its current scale it is in need of restructure
- [multiresolution-mesh-creator](https://github.com/mitchellshargreaves-monash/multiresolution-mesh-creator/tree/4979288b4ca67ccd8b50a9b8865e747f9121f19e)
    - A submodule which the pipeline depends on
- nginx
    - An example NginX config and Docker for hosting datasets for the Cryoglancer viewer to access
- passthrough_api
    - An experiment which uses fast_api to pass through any commands to the docker container
    - Intended for use with a Relion Docker environment in the future to allow for users to upload just the tilt series rather than a full volume
- pipeline
    - The code used to process IMP datasets into something that can be viewed by the platform

## Archetecture
![Data flow](/images/data_flow.drawio.png)

- Prior to upload the user will prepare the volume, objects and any proteomics that they wish to share for visualisation
- Currently the full volume must be uploaded and any object coordinates need to be processed as a .csv **in the same coordinate system**
- The platform also supports attaching additional files to the dataset, such as tilt series or .star files along with the dataset
- Datasets are uploaded to the IMP platform using the [MyData Client](https://github.com/mytardis/mydata)
- The pipeline watches for new datasets to arrive using [Watchdog](https://pypi.org/project/watchdog/)
- Datasets are processed into neuroglancer's precomuted format
- Users are alerted by email when the processing is complete or if it has failed
- If the dataset processed successfully it will be available for viewing using the [Cryoglancer Portal](https://cryoglancer.imp-db.cloud.edu.au/)

## Dataset Input
The pipeline expects an input folder with the following format:
- `metadata.json`
    - `name`: The name of the dataset - `string`
    - `description`: The description of the dataset - `string`
    - `parent_volume`: The filename of the parent volume - `.mrc`
    - `object_volumes`: A list of the filenmaes of the objects - `[.mrc]`
    - `object_coordinates`: The filename of the coordinates table - `.csv`
    - `object_names`: A list of human readable object names - should match the length of the filenames in `object_volumes` - `[string]`
    - `subclasses`: The names of any additional columns in the `object_coordinates` table for visualisation - `[string]`
    - `proteomics`: A table that encodes the Majority Protein IDs and iBAQ of the dataset - `.csv`
    - `other_files`: A list of any additional files for sharing along with the dataset `[string]`
    - `orcid`: Your ORCiD in "0123-4567-8901-2345" format `[string]`
    - `doi_attributes`: The attributes of the doi for minting `[json]`
        ```
        "doi_attributes": {
            "creators": [{
                "name": "Your research group"
            }],
            "titles": [{
                "title": "Test Dataset"
            }],
            "publisher": "IMP Platform",
            "publication_year": 2023
        }
        ```
- `parent_volume.mrc`
    - The volume for the objects to be placed in
    - Take care that the coordinate system matches the object coordinates
- `object_volumes.mrc`
    - One or more objects to be placed in the volume
- `object_coordinates.csv`
    - A table of coordinates and euler angles for the objects to be placed in the parent volume
    - Columns:
        - Position Coordinates - `x`, `y`, `z`
        - Euler Angles - `eux`, `euy`, `euz`
        - Object volume filename - `mrcfile`
        - Human readable name of the corresponding object - `name`
        - `index` - The index of the particle as it corresponds to the object list
        - Any additional subclasses you wish to visualise, as referenced by the list of subclasses
- `proteomics.csv`
    - A table of the proteomics information
    - Columns:
        - Majority Protein IDs
        - iBAQ
        - Any additional information for sharing
            - Note that while only Majority Protein IDs and iBAQ will be shown by the IMP platform, any extra columns will still be present for browsing if the file is downloaded
- Any other files listed

An example input dataset has been provided at `/example/object_input`

## NginX
An NginX config file to host on localhost is provided. The server has to be able to serve compressed files and overcome a few caveats with the filenames, therefore `simplehttpserver` wasn't sufficient. 

You can install nginx on linux with:  
```
apt-get install nginx
```
or on MAC:
```
brew install nginx
```

Add the config file at `/etc/nginx/sites-available/` with a symlink to `/etc/nginx/sites-enabled/`. Edit the config file to point to the folder you want to serve. Useful commands for management include:
```  
service nginx start
service nginx restart
service nginx stop
```
