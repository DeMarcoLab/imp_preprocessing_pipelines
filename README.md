# IMP_Webtool
Building on neuroglancer, enables viewing and interacting with EM data.

This web tool has been developed to enable scientists and researchers to view and interact with their EM data. Building on https://github.com/google/neuroglancer , large scale datasets can be viewed quickly in the browser.

A pipeline has been developed to convert EM datasets (.mrc format, or image slices) to the precomputed neuroglancer format. There are two pathways:

1) MRC file for the image available with a list of molecules and their position/rotations. Other values like cc can be in this table. If a .obj or .mrc file is available for the individual molecules, it will be used to create duplicated objects at the correct position/rotation. Resulting data structures is <TODO>.
  
2) MRC file for the image, as well as a class mask as MRC. This will result in a segmentation layer for each type of class found in the file, with its individual object meshes calculated from the segmentation file. At the current stage, this does not support additional values like cc.
  
  
App specific enhancements not found in vanilla neuroglancer:
  
  1) change colourmap online
  2) change value by which to colour online, this will apply for segments and annotations
  3) select a region (currently box shaped) in which to display meshes.
  4) change colour of an individual mesh easily
  5) Create a group of meshes by selecting them - they will be added to a new layer
  
  
Local installation to view generated files:
  <TODO>
         
Setup and use Preprocessing Pipelines:
  <TODO>

