# IMP_Preprocessing

These pipeline has been developed to convert EM datasets (.mrc format, or image slices) to the precomputed neuroglancer format. There are two pathways:

1) MRC file for the image available with a list of molecules and their position/rotations. Other values like cc can be in this table. If a .obj or .mrc file is available for the individual molecules, it will be used to create duplicated objects at the correct position/rotation. 
  
2) MRC file for the image, as well as a class mask as MRC. This will result in a segmentation layer for each type of class found in the file, with its individual object meshes calculated from the segmentation file. At the current stage, this does not support additional values like cc.

Both ways result in a folder of ...path.../bucket/dataset/
The contents of this folder will be hosted either locally on your computer for access with local neuroglancer, ot on the web app for which the database has to be updated - It will be possible to do this step some time in the future.
  

<h4>OS Requirement</h4>
Linux, MAC.
WSL on Windows works, however you need to keep to the WSL file system when serving the files (and copying them to the server). Else the : in some file names will pose a problem on Windows.

<h4>Software Requirements</h4>

- The functions **mrc2tif** and **newstack** from ***[imod](https://bio3d.colorado.edu/imod/download.html)*** are used.
- Python 3 and Anaconda
- The required packages are bundled in the conda environment found in **environment.yml**

<h5>For object mesh creation</h5>

- cmake
- [pyMesh](https://github.com/PyMesh/PyMesh) for the object to mesh pipeline. This is a bit of pain to install - looking to find alternatives.
- [multiresoultion-mesh-creator](https://github.com/davidackerman/multiresolution-mesh-creator)

<h5>Folder structure</h5>
Please look at the two examples to understand the required folder structure. The two images below also illustrate the structure.


<h5>To run</h5>

    bash ./pipeline.sh -p path/to/folder/containing/mrcFile
