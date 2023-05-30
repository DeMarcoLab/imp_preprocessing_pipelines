import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

import math
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation as R
from matplotlib.colors import Normalize, to_hex
from matplotlib.cm import get_cmap
from pandarallel import pandarallel
# pandarallel.initialize(progress_bar=True)

import tifffile
import mrcfile
import starfile
import json
import tinybrain
import trimesh
import skimage.measure as skim
from cloudvolume import CloudVolume
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

import joblib
from joblib import Parallel, delayed
from psutil import virtual_memory
from tqdm import tqdm
import contextlib

def csv2json(csv_path, json_path):
    # Read and select the columns to display
    df = pd.read_csv(csv_path)
    df = df[["Majority protein IDs", "iBAQ"]]

    # Convert each row into a dict
    proteomics = []
    for _, row in df.iterrows():
        proteomics.append(row.to_dict())

    with open(json_path, "w", encoding="utf-8") as jsonf:
        jsonf.write(json.dumps(proteomics, indent=4))

def parse_mrc(mrc_path, json_path=None, tiff_path=None):
    """
    Extract the header of the mrc file as a dictionary
    Optionally export the data of the mrc file as a tiff
    """
    mrc = mrcfile.mmap(mrc_path, mode="r+")

    # Extract header
    header = {
        "x": mrc.header.nx.item(0),
        "y": mrc.header.ny.item(0),
        "z": mrc.header.nz.item(0),
        # different naming convention to match Neuroglancer's metadata format
        "pixel_spacing": [mrc.voxel_size.x/10, mrc.voxel_size.y/10, mrc.voxel_size.z/10],
        "min": mrc.header.dmin.item(0),
        "max": mrc.header.dmax.item(0),
        "mean": mrc.header.dmean.item(0)
    }

    # Optionally save data as tiff
    # mrc.data is in the shape: [z, y, x]
    if tiff_path:
        digits = len(str(mrc.data.shape[0]))
        for i in range(mrc.data.shape[0]):
            tifffile.imwrite(tiff_path/f"img.{i:0{digits}d}.tif", mrc.data[i])
    
    # Export header as json for neuroglancer
    if json_path:
        with open(json_path, "w", encoding="utf-8") as jsonf:
            jsonf.write(json.dumps(header, indent=4))
    
    mrc.close()
    return header


@contextlib.contextmanager
def tqdm_joblib(tqdm_object):
    """Context manager to patch joblib to report into tqdm progress bar given as argument"""

    class TqdmBatchCompletionCallback:
        def __init__(self, time, index, parallel):
            self.index = index
            self.parallel = parallel

        def __call__(self, index):
            tqdm_object.update()
            if self.parallel._original_iterator is not None:
                self.parallel.dispatch_next()

    old_batch_callback = joblib.parallel.BatchCompletionCallBack
    joblib.parallel.BatchCompletionCallBack = TqdmBatchCompletionCallback
    try:
        yield tqdm_object
    finally:
        joblib.parallel.BatchCompletionCallBack = old_batch_callback
        tqdm_object.close()


# This looks like it assumes x,y,z orientation
# Need to confirm this is what we want since its different to mrcfile
def process_image_slice(z, file_path, layer_path, num_mips):
    """
    Precompute an image slice into an image pyramid
    Result will be saved at layer_path
    """

    # Create a cloud volume object for each mip
    vols = [
        CloudVolume(layer_path, mip=i, parallel=False, fill_missing=False)
        for i in range(num_mips)
    ]

    # Import data and calculate pyramid
    array = np.squeeze(np.array(Image.open(file_path))).T[..., None]
    img_pyramid = tinybrain.accelerated.average_pooling_2x2(array, num_mips)

    # Fill in list of volumes
    vols[0][:, :, z] = array
    for i in range(num_mips - 1):
        vols[i + 1][:, :, z] = img_pyramid[i]


def create_precomputed_volume(
    image_slices_path, precomputed_path, header, layer_type="image",dtype="float32", parallel=False
):
    """Create precomputed volume from 2D TIF series"""
    image_slices = os.listdir(image_slices_path)
    image_slices.sort()

    # compute num_mips from data size
    # we add one because 0 is included in the number of downsampling levels
    chunk_size = (256, 256, 1)
    num_mips = max(1, math.ceil(math.log(max(header["x"], header["y"]) / chunk_size[0], 2)) + 1)

    # convert voxel size from um to nm
    vol = CloudVolume(
        "file://" + str(precomputed_path), 
        parallel=parallel, 
        info=CloudVolume.create_new_info(
            num_channels=1,
            layer_type=layer_type,
            data_type=dtype,  # Channel images might be "uint8"
            encoding="raw",  # raw, jpeg, compressed_segmentation, fpzip, kempressed
            resolution=header["pixel_spacing"],  # Voxel scaling, units are in nanometers
            voxel_offset=[0, 0, 0],  # x,y,z offset in voxels from the origin
            # Pick a convenient size for your underlying chunk representation
            # Powers of two are recommended, doesn"t need to cover image exactly
            chunk_size=chunk_size,  # units are voxels
            volume_size=(header["x"], header["y"], header["z"])  # e.g. a cubic millimeter dataset
        )
    )

    # Compute scales for the image pyramid and add to cloud volume object
    for i in range(num_mips):
        vol.add_scale((2 ** i, 2 ** i, 1), chunk_size=chunk_size)
    vol.commit_info()

    # Calculate num procs to use based on available memory and number of cpus
    num_procs = min(
        math.floor(virtual_memory().total / (header["x"] * header["y"] * 8)),
        joblib.cpu_count(),
    )

    # Precompute volumes
    try:
        with tqdm_joblib(tqdm(desc="Creating precomputed volume", total=len(image_slices))) as progress_bar:
            Parallel(num_procs, timeout=3600, verbose=10)(
                delayed(process_image_slice)(int(fn.split(".")[1]), image_slices_path/fn, vol.layer_cloudpath, num_mips)
                for fn in image_slices
            )
    # Why is it ok to move on?
    except Exception as e:
        print(e)
        print("timed out on a slice. moving on to the next step of pipeline")


# Temporarily unused until we determine why the object stars do not match the volumes
def extract_objects(config, header, csv_path, input_path):
    """
    Extract particle objects from the provided stars
    Returns as a pandas data frame and saves at the csv_path
    """
    particles = pd.DataFrame({})

    for i, (star, volume, name) in enumerate(zip(config["object_stars"], config["object_volumes"], config["object_names"])):
        star = starfile.read(input_path/star)

        # Mandatory fields
        object_table = pd.DataFrame({
            # Might need to subtract origin, check with Alex/Charles
            # "x": star["particles"]["rlnCoordinateX"] + star["particles"]["rlnOriginXAngst"] / star["optics"]["rlnImagePixelSize"][0],
            # "y": star["particles"]["rlnCoordinateY"] + star["particles"]["rlnOriginYAngst"] / star["optics"]["rlnImagePixelSize"][0],
            # "z": star["particles"]["rlnCoordinateZ"] + star["particles"]["rlnOriginZAngst"] / star["optics"]["rlnImagePixelSize"][0],
            "x": (star["particles"]["rlnCoordinateX"] + star["particles"]["rlnOriginXAngst"]) / 10 * header["pixel_spacing"][0],
            "y": (star["particles"]["rlnCoordinateY"] + star["particles"]["rlnOriginYAngst"]) / 10 * header["pixel_spacing"][1],
            "z": (star["particles"]["rlnCoordinateZ"] + star["particles"]["rlnOriginZAngst"]) / 10 * header["pixel_spacing"][2],
            "eux": star["particles"]["rlnAngleRot"],
            "euy": star["particles"]["rlnAngleTilt"],
            "euz": star["particles"]["rlnAnglePsi"],
            "mrcfile": volume,
            "name": name,
            "index": i / len(config["object_stars"])
        })

        # 0 or more extra fields
        for sub in config["subclasses"]:
            object_table[sub] = star["particles"][sub]

        # Add to cumulative table of particles
        particles = particles.append(object_table, ignore_index=True)
        particles.to_csv(csv_path)
    
    return particles


def name2id(name):
    """
    A function to create a unique id composed of integers out of a given name
    Truncated to 0:4 to fit in uint64
    """
    return "".join([str(ord(c)) for c in name[0:4]]) 

# Could take particles df in as an input rather than reading from file once object star / volume is resolved
def annotate_objects(particles, config, coordinates_path):
    """Create neuroglancer format object annotations from the particle information"""
    # Create norm functions
    norms = {sub: Normalize(vmin=particles[sub].min(), vmax=particles[sub].max()) for sub in config["subclasses"]}

    # Define empty lists for each particle name and add a property to list the names
    annotations = {name: [] for name in config["object_names"]}
    annotations["columns"] = config["object_names"]

    # Create a point for each subclass
    for i, row in particles.iterrows():
        # Create description as list of subclass values
        if config["subclasses"]:
            desc = ", ".join([f"{sub}: {row[sub]}" for sub in config["subclasses"]])
        # If no subclasses, label with no further data
        else:
            desc = "no further data"

        # Construct annotations object
        annotations[row["name"]].append({
            "type": "point", 
            "description":  desc,
            "id": name2id(row["name"]) + str(i),
            "point": [row["x"], row["y"], row["z"]],
            "props": [to_hex(get_cmap("tab20")(row["index"]))] + \
                [to_hex(get_cmap("plasma")(row[sub])) for sub in config["subclasses"]],
            "fields": {sub: norms[sub](row[sub]) for sub in config["subclasses"]}
        })

    # Save all annotations as a json
    for key in annotations.keys():
        with open(coordinates_path/(key.strip() + ".json"), "w", encoding="utf-8") as jsonf:
            jsonf.write(json.dumps(annotations[key], indent=4))


def particle2mesh(row, object_id, original_mesh, objects_path):
    """Create triangle mesh objects out of the particles"""
    # rotate
    rot = R.from_euler("ZXZ", [row["eux"], row["euy"], row["euz"]], degrees=True)
    newVertices = np.dot(rot.as_matrix(), original_mesh.vertices.T).T
    rotMesh = trimesh.Trimesh(newVertices, original_mesh.faces, process=False)

    # translate back
    rotMesh.apply_translation(np.array([row['x'], row['y'], row['z']]))

    # remove material info from file
    rotMesh.visual = trimesh.visual.ColorVisuals()

    # export to object file
    rotMesh.export(objects_path/row["name"]/"meshes/mesh_lods/s0"/f"{object_id}{row.name}.obj", file_type="obj")


def write_object(vertices, faces, object_name):
    """Record an object as an obj file"""

    object_file = open(object_name, 'w')
    object_file.write("o {name2id(object_name)}\n")
    
    for vertex in vertices:
        object_file.write(f"v {vertex[0]} {vertex[1]} {vertex[2]}\n")
    
    object_file.write("s off\n")

    for face in faces:
        object_file.write(f"f {face[0]+1} {face[1]} {face[2]}\n")
    
    object_file.close()

def create_object_meshes(volume_path, name, particles, objects_path):
    """Convert object mrc volumes to triangular mesh"""
    pandarallel.initialize(progress_bar=True)

    object_id = name2id(name)

    # read in MRC volume
    mrc = mrcfile.open(volume_path, "r+", permissive=True)

    # Get object data
    vertices, faces, _, _ = skim.marching_cubes(mrc.data.transpose(2, 1, 0))

    # Store object and convert to triangular mesh
    object_name = objects_path/f"{object_id}.obj"
    write_object(vertices, faces, object_name)
    original_mesh = trimesh.load_mesh(object_name, force="mesh")

    # translate to zero
    original_mesh.apply_translation(np.array([mrc.data.shape[2], mrc.data.shape[1], mrc.data.shape[0]]) / 2)

    # Copy configs
    shutil.copy("./dask-config.yaml", objects_path/name/"dask-config.yaml")
    shutil.copy("./run-config.yaml", objects_path/name/"run-config.yaml")

    # Export objects
    particles[particles["name"] == name].parallel_apply(particle2mesh, axis=1, args=(object_id, original_mesh, objects_path))

def pipeline(input_path, staging_path, test=False):
    """
    Main Workflow
    Convert an input dataset into cryoglancer format
    """
    # Parse metadata.json
    print("Loading config...")
    with open(input_path/"metadata.json", "r") as f:
        config = json.loads(f.read())

    # Construct file paths 
    parent_volume_path = input_path/config["parent_volume"]
    proteomics_path = staging_path/"proteomics"
    image_slices_path = staging_path/"image_slices"
    precomputed_path = staging_path/"image"
    coordinates_path = staging_path/"coordinates"
    objects_path = staging_path/"objects"
    s0 = "meshes/mesh_lods/s0"

    # Create folders
    print("Creating folders...")
    paths = [proteomics_path, image_slices_path, precomputed_path, coordinates_path, objects_path] + \
        [objects_path/name/s0 for name in config["object_names"]]

    for path in paths:
        if not path.exists():
            os.makedirs(path)

    # Run pipeline
    if config.get("proteomics", False):
        print("Convert proteomics...")
        csv2json(input_path/config["proteomics"], proteomics_path/"proteomics.json")
        shutil.copy(input_path/config["proteomics"], proteomics_path/"proteomics.csv")

    print("Parsing parent volume...")
    header = parse_mrc(parent_volume_path, json_path=staging_path/(config["name"] + ".json"), tiff_path=image_slices_path)

    print("Converting parent volume...")
    create_precomputed_volume(image_slices_path, precomputed_path, header)

    # print("Parsing object properties...")
    # particles = extract_objects(config, header, staging_path/"particles.csv", input_path)

    # Load particles
    particles = pd.read_csv(input_path/config["object_coordinates"])

    print("Annotating objects...")
    annotate_objects(particles, config, coordinates_path)

    if test:
        print("Reduce particle number for testing")
        particles = particles.head(100)

    for volume, name in zip(config["object_volumes"], config["object_names"]):
        print(f"Creating object triangular mesh: {name} ({volume})")
        create_object_meshes(input_path/volume, name, particles, objects_path)

        print("\nCreating multiresolution mesh...")
        subprocess.Popen(f"create-multiresolution-meshes {objects_path/name} -n {joblib.cpu_count()}", shell=True).wait()

        print("Transferring mesh...")
        multi_mesh = [file for file in os.listdir(objects_path) if file.startswith(str(name + "-"))] 
        multi_mesh.sort()
        shutil.copytree(objects_path/multi_mesh[-1], coordinates_path/(name + ".mesh"))

        print(f"{name} ({volume}) completed")

    print("Cleanup intermediate artifacts...")
    shutil.rmtree(image_slices_path)
    shutil.rmtree(objects_path)

if __name__ == "__main__":
    # Parse inputs
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path")
    parser.add_argument("staging_path")
    parser.add_argument("-t", "--test", action="store_true",
                        help="Test the pipeline using only the 'head' of the particle table without cleaning up any generated files.")
    args = parser.parse_args()

    # Set base paths
    input_path = Path(args.input_path)
    staging_path = Path(args.staging_path)

    # Run pipeline
    pipeline(input_path, staging_path, test=args.test)