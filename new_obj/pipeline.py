import argparse
import json
import os

import tifffile
import mrcfile

from pathlib import Path

import math
# from cloudvolume import CloudVolume
# import numpy as np
# import joblib
# from joblib import Parallel, delayed
# from glob import glob
# import argparse
# import PIL
# from PIL import Image
# from psutil import virtual_memory
# from tqdm import tqdm
# import tinybrain

# PIL.Image.MAX_IMAGE_PIXELS = None

# import contextlib
# import joblib

# import math
# import numpy as np
# from tqdm import tqdm

# Extract the header of the mrc file as a dictionary
# Extract the data of the mrc as a npy
def parse_mrc(mrc_path, tiff_path=None):
    mrc = mrcfile.mmap(mrc_path, mode='r+')
    data = mrc.data

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
    if tiff_path:
        # Make sure dir exists
        if not tiff_path.exists():
            os.makedirs(tiff_path)

        # Save data as tiffs
        digits = len(str(data.shape[0]))
        for i in range(0, data.shape[0]):
            tifffile.imwrite(tiff_path/f"img.{i:0{digits}d}.tif", data[i])
    
    mrc.close()
    return header


### create precomputed volume
# def calc_hierarchy_levels(img_size, lowest_res=256):
#     """Compute max number of mips for given chunk size
#     Args:
#         img_size (list): Size of image in x,y,z
#         lowest_res (int, optional): minimum chunk size in XY. Defaults to 256.
#     Returns:
#         int: Number of mips
#     """
#     max_xy = max(img_size[0:1])
#     # we add one because 0 is included in the number of downsampling levels
#     num_levels = max(1, math.ceil(math.log(max_xy / lowest_res, 2)) + 1)
#     return num_levels



# ### misc
# @contextlib.contextmanager
# def tqdm_joblib(tqdm_object):
#     """Context manager to patch joblib to report into tqdm progress bar given as argument"""

#     class TqdmBatchCompletionCallback:
#         def __init__(self, time, index, parallel):
#             self.index = index
#             self.parallel = parallel

#         def __call__(self, index):
#             tqdm_object.update()
#             if self.parallel._original_iterator is not None:
#                 self.parallel.dispatch_next()

#     old_batch_callback = joblib.parallel.BatchCompletionCallBack
#     joblib.parallel.BatchCompletionCallBack = TqdmBatchCompletionCallback
#     try:
#         yield tqdm_object
#     finally:
#         joblib.parallel.BatchCompletionCallBack = old_batch_callback
#         tqdm_object.close()



# def chunks(l, n):
#     """Convert a list into n-size chunks (last chunk may have less than n elements)
#     Args:
#         l (list): List to chunk
#         n (int): Elements per chunk
#     Yields:
#         list: n-size chunk from l (last chunk may have fewer than n elements)
#     """
#     for i in range(0, len(l), n):
#         yield l[i : i + n]



# def create_cloud_volume(
#     precomputed_path,
#     img_size,
#     voxel_size,
#     num_mips,
#     chunk_size,
#     parallel=False,
#     layer_type="image",
#     dtype="uint16",
# ):
#     """Create Neuroglancer precomputed volume S3
#     Args:
#         precomputed_path (str): S3 Path to location where precomputed layer will be stored
#         img_size (list of int): Size of the image (in 3D) to be uploaded
#         voxel_size ([type]): Voxel size in nanometers
#         num_mips (int, optional): Number of downsampling levels in X and Y. Defaults to 6.
#         chunk_size (list, optional): Size of each chunk stored on S3. Defaults to [1024, 1024, 1].
#         parallel (bool, optional): Whether or not the returned CloudVlue object will use parallel threads. Defaults to False.
#         layer_type (str, optional): Neuroglancer type of layer. Can be image or segmentation. Defaults to "image".
#         dtype (str, optional): Datatype of precomputed volume. Defaults to "uint16".
#     Returns:
#         cloudvolume.CloudVolume: CloudVolume object associated with this precomputed volume
#     """
#     info = CloudVolume.create_new_info(
#         num_channels=1,
#         layer_type=layer_type,
#         data_type=dtype,  # Channel images might be 'uint8'
#         encoding="raw",  # raw, jpeg, compressed_segmentation, fpzip, kempressed
#         resolution=voxel_size,  # Voxel scaling, units are in nanometers
#         voxel_offset=[0, 0, 0],  # x,y,z offset in voxels from the origin
#         # Pick a convenient size for your underlying chunk representation
#         # Powers of two are recommended, doesn't need to cover image exactly
#         chunk_size=chunk_size,  # units are voxels
#         volume_size=img_size,  # e.g. a cubic millimeter dataset
#     )
#     vol = CloudVolume(precomputed_path, info=info, parallel=parallel)
#     [vol.add_scale((2 ** i, 2 ** i, 1), chunk_size=chunk_size) for i in range(num_mips)]

#     vol.commit_info()
#     return vol



# def get_image_dims(files):
#     """Get X,Y,Z dimensions of images based on list of files
#     Args:
#         files (list of str): Path to 2D tif series 
#     Returns:
#         list of int: X,Y,Z size of image in files
#     """
#     # get X,Y size of image by loading first slice
#     img = np.squeeze(np.array(Image.open(files[0]))).T
#     # get Z size by number of files in directory
#     z_size = len(files)
#     x_size, y_size = img.shape
#     return [x_size, y_size, z_size]



# def process(z, file_path, layer_path, num_mips):
#     """Upload single slice to S3 as precomputed
#     Args:
#         z (int): Z slice number to upload
#         file_path (str): Path to z-th slice
#         layer_path (str): S3 path to store data at
#         num_mips (int): Number of 2x2 downsampling levels in X,Y
#     """
#     vols = [
#         CloudVolume(layer_path, mip=i, parallel=False, fill_missing=False)
#         for i in range(num_mips)
#     ]
#     # array = load_image(file_path)[..., None]
#     # array = tf.imread(file_path).T[..., None]
#     array = np.squeeze(np.array(Image.open(file_path))).T[..., None]
#     img_pyramid = tinybrain.accelerated.average_pooling_2x2(array, num_mips)
#     vols[0][:, :, z] = array
#     for i in range(num_mips - 1):
#         vols[i + 1][:, :, z] = img_pyramid[i]
#     return



# def create_precomputed_volume(
#     input_path, voxel_size, precomputed_path,num_procs=None, extension="tif", layer_type="image",dtype="float32"
# ):
#     """Create precomputed volume on S3 from 2D TIF series
#     Args:
#         input_path (str): Local path to 2D TIF series
#         voxel_size (np.ndarray): Voxel size of image in X,Y,Z in microns
#         precomputed_path (str): S3 path where precomputed volume will be stored
#         extension (str, optional): Extension for image files. Defaults to "tif".
#     """
#     files_slices = list(
#         enumerate(np.sort(glob(f"{input_path}/*.{extension}")).tolist())
#     )
#     zs = [i[0] for i in files_slices]
#     files = np.array([i[1] for i in files_slices])

#     img_size = get_image_dims(files)
#     print(img_size)
#     # compute num_mips from data size
#     chunk_size = [256, 256, 1]
#     num_mips = calc_hierarchy_levels(img_size, lowest_res=chunk_size[0])
#     print(num_mips)
#     # convert voxel size from um to nm
#     vol = create_cloud_volume(
#         precomputed_path,
#         img_size,
#         voxel_size,
#         num_mips,
#         chunk_size,
#         parallel=False,
#         layer_type=layer_type,
#         dtype=dtype,

#     )

#     if num_procs == None:
#         # num procs to use based on available memory
#         num_procs = min(
#             math.floor(virtual_memory().total / (img_size[0] * img_size[1] * 8)),
#             joblib.cpu_count(),
#         )

#     try:
#         with tqdm_joblib(
#             tqdm(desc="Creating precomputed volume", total=len(files))
#         ) as progress_bar:
#             Parallel(num_procs, timeout=3600, verbose=10)(
#                 delayed(process)(z, f, vol.layer_cloudpath, num_mips,)
#                 for z, f in zip(zs, files)
#             )
#     except Exception as e:
#         print(e)
#         print("timed out on a slice. moving on to the next step of pipeline")



# Parse inputs
parser = argparse.ArgumentParser()
parser.add_argument('input_path')
parser.add_argument('staging_path')
parser.add_argument('output_path')

# Optional inputs
# parser.add_argument("-c", "--config", default="~/.authservers.json",
#                     help="JSON format config file containing the list of places we can log into")
args = parser.parse_args()

# Set paths
input_path = Path(args.input_path)
staging_path = Path(args.staging_path)
output_path = Path(args.output_path)

# Parse metadata.json
with open(input_path/"metadata.json", 'r') as f:
    config = json.loads(f.read())

header = parse_mrc(input_path/config["tilt_volume"], output_path/config["name"]/"image_slices")

# create_precomputed_volume(tif_path, header["pixel_spacing"], out_path, num_procs, "tif", "Image", "float32")
