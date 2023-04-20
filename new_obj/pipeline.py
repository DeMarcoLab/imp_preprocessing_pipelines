import argparse
import json
import os
from pathlib import Path

import math
import numpy as np
import tifffile
import mrcfile
import tinybrain
from cloudvolume import CloudVolume
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

import joblib
from joblib import Parallel, delayed
from psutil import virtual_memory
from tqdm import tqdm
import contextlib




# Extract the header of the mrc file as a dictionary
# Extract the data of the mrc as a npy
def parse_mrc(mrc_path, tiff_path=None):
    mrc = mrcfile.mmap(mrc_path, mode='r+')

    # Extract header
    header = {
        "x": mrc.header.nx.item(0),
        "y": mrc.header.ny.item(0),
        "z": mrc.header.nz.item(0),
        # why this not called voxel size?
        "pixel_spacing": [mrc.voxel_size.x/10,mrc.voxel_size.y/10,mrc.voxel_size.z/10],
        "min": mrc.header.dmin.item(0),
        "max": mrc.header.dmax.item(0),
        "mean": mrc.header.dmean.item(0)
    }

    # Optionally save data as tiff
    # mrc.data is in the shape: [z, y, x]
    if tiff_path:
        # Make sure dir exists
        if not tiff_path.exists():
            os.makedirs(tiff_path)

        # Save data as tiffs
        digits = len(str(mrc.data.shape[0]))
        for i in range(mrc.data.shape[0]):
            tifffile.imwrite(tiff_path/f"img.{i:0{digits}d}.tif", mrc.data[i])
    
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
def process(z, file_path, layer_path, num_mips):
    """Upload single slice to S3 as precomputed
    Args:
        z (int): Z slice number to upload
        file_path (str): Path to z-th slice
        layer_path (str): S3 path to store data at
        num_mips (int): Number of 2x2 downsampling levels in X,Y
    """
    vols = [
        CloudVolume(layer_path, mip=i, parallel=False, fill_missing=False)
        for i in range(num_mips)
    ]

    array = np.squeeze(np.array(Image.open(file_path))).T[..., None]
    img_pyramid = tinybrain.accelerated.average_pooling_2x2(array, num_mips)
    vols[0][:, :, z] = array

    for i in range(num_mips - 1):
        vols[i + 1][:, :, z] = img_pyramid[i]


def create_precomputed_volume(
    image_slices_path, precomputed_path, header, layer_type="image",dtype="float32", parallel=False
):
    """Create precomputed volume on S3 from 2D TIF series
    Args:
        input_path (str): Local path to 2D TIF series
        voxel_size (np.ndarray): Voxel size of image in X,Y,Z in microns
        precomputed_path (str): S3 path where precomputed volume will be stored
        extension (str, optional): Extension for image files. Defaults to "tif".
    """
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
            data_type=dtype,  # Channel images might be 'uint8'
            encoding="raw",  # raw, jpeg, compressed_segmentation, fpzip, kempressed
            resolution=header["pixel_spacing"],  # Voxel scaling, units are in nanometers
            voxel_offset=[0, 0, 0],  # x,y,z offset in voxels from the origin
            # Pick a convenient size for your underlying chunk representation
            # Powers of two are recommended, doesn't need to cover image exactly
            chunk_size=chunk_size,  # units are voxels
            volume_size=(header["x"], header["y"], header["z"])  # e.g. a cubic millimeter dataset
        )
    )
    [vol.add_scale((2 ** i, 2 ** i, 1), chunk_size=chunk_size) for i in range(num_mips)]
    vol.commit_info()

    # num procs to use based on available memory
    num_procs = min(
        math.floor(virtual_memory().total / (header["x"] * header["y"] * 8)),
        joblib.cpu_count(),
    )

    # Precompute volumes
    try:
        with tqdm_joblib(tqdm(desc="Creating precomputed volume", total=len(image_slices))) as progress_bar:
            Parallel(num_procs, timeout=3600, verbose=10)(
                delayed(process)(int(fn.split(".")[1]), image_slices_path/fn, vol.layer_cloudpath, num_mips)
                for fn in image_slices
            )
    # Why is it ok to move on?
    except Exception as e:
        print(e)
        print("timed out on a slice. moving on to the next step of pipeline")


# Parse inputs
parser = argparse.ArgumentParser()
parser.add_argument('input_path')
parser.add_argument('staging_path')
parser.add_argument('output_path')
args = parser.parse_args()

# Set base paths
input_path = Path(args.input_path)
staging_path = Path(args.staging_path)
output_path = Path(args.output_path)

# Parse metadata.json
with open(input_path/"metadata.json", 'r') as f:
    config = json.loads(f.read())

# Construct file paths 
parent_volume = input_path/config["tilt_volume"]
image_slices = output_path/config["name"]/"image_slices"
precomputed = output_path/config["name"]/"image"

# Pipeline
header = parse_mrc(parent_volume, image_slices)
create_precomputed_volume(image_slices, precomputed, header)
