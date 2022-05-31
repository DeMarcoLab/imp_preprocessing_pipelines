import sys
import numpy  as np
import pandas as pd
import pymesh as pym
#from vol2mesh import Mesh, concatenate_meshes
from scipy.spatial.transform import Rotation as R
import mrcfile as mrc
import skimage.measure as skim
import os 
from os.path import isfile, join
import shutil
def writeToObjFile(self, pathToObjFile, name):
    objFile = open(pathToObjFile, 'w')
    objFile.write("o " + name + "\n")
    for vert in self["verts"]:
        objFile.write("v ")
        objFile.write(str(vert[0]))
        objFile.write(" ")
        objFile.write(str(vert[1]))
        objFile.write(" ")
        objFile.write(str(vert[2]))
        objFile.write("\n")
    objFile.write("s off\n")
    for face in self["faces"]:
        objFile.write("f ")
        objFile.write(str(face[0]+1))
        objFile.write(" ")
        objFile.write(str(face[1]+1))
        objFile.write(" ")
        objFile.write(str(face[2]+1))
        objFile.write("\n")
    objFile.close() 


def makeYamlFiles(path):
    f = open(path+"/run-config.yaml","w")
    f.write("required_settings:\n")
    f.write("  input_path: ./input/         # Path to lod 0 meshes or multiscale meshes\n")
    f.write("  output_path: ../meshes/   # Path to write out multires meshes\n")
    f.write("  num_lods: 2                          # Number of levels of detail\n")
    f.write("  box_size: 8                          # lod 0 box size\n")


    f.write("optional_decimation_settings:\n")
    f.write("  skip_decimation: False         # Skip mesh decimation if meshes exist; default is false\n")
    f.write("  decimation_factor: 2           # Factor by which to decimate faces at each lod, ie factor**lod; default is 2\n")
    f.write("  aggressiveness: 10             # Aggressiveness to be used for decimation; default is 7\n")
    f.write("  delete_decimated_meshes: True  # Delete decimated meshes, only applied if skip_decimation=False\n")

    g = open(path+"/dask-config.yaml","w")
    g.write("jobqueue:\n")
    g.write("  local:\n")
    # Cluster slots are reserved in chunks.
    # This specifies the chunk size.
    g.write("    ncpus: 1\n")

    # How many dask worker processed to run per chunk.
    # (Leave one thread empty for garbage collection.)
    g.write("    processes: 1\n")

    # How many threads to use in each chunk.
    # (Use just one thread per process -- no internal thread pools.)
    g.write("    cores: 1\n")

    g.write("    log-directory: job-logs\n")
    g.write("    name: dask-worker\n")

    g.write("distributed:\n")
    g.write("  scheduler:\n")
    g.write("    work-stealing: true\n")

    g.write("  worker:\n")
    g.write("    memory:\n")
    g.write("      target: 0.0\n")
    g.write("      spill: 0.0\n")
    g.write("      pause: 0.0\n")
    g.write("      terminate: 0.0\n")

    g.write("  admin:\n")
    g.write("    log-format: '[%(asctime)s] %(levelname)s %(message)s'\n")
    g.write("    tick:\n")
    g.write("      interval: 20ms  # time between event loop health checks\n")
    g.write("      limit: 3h       # time allowed before triggering a warning\n")

# args parsing
basepath    = sys.argv[1]
positionlist = sys.argv[2]

mrc_files = [f for f in os.listdir(basepath+"/templates/") if isfile(join(basepath+"/templates/",f)) ]
#print(mrc_files)
#delete previous output folder if it exists
print(" Starting multiplication of objects using coordinates/rotations ... ")
if(os.path.exists(basepath+"/objects/")):
    shutil.rmtree(basepath+"/objects/")
os.makedirs(basepath+"/objects/")
for f in mrc_files:
 
    if(".mrc" not in f):
        continue 
    print("Processing: " + f)
    g = f.split(".")[0]
    h =  [str(ord(c)) for c in g]
    #print(h)
    id = ''.join(h)[0:4]
   
    # read in MRC volume 
    S = mrc.open(join(basepath+"/templates/",f), 'r+', permissive=True)
    nz, ny, nx = S.data.shape
    #print(S.data.shape)
    T = np.array([nx,ny,nz],dtype=float)/2.0 # translation for rotation

    # swapping x & z coordinates
    data = np.ndarray((nx,ny,nz))
    for x in range(nx):
        for z in range(nz):
            data[x,:,z] = S.data[z,:,x]
    verts, faces, normals, values = skim.marching_cubes(data)
    newobj = {"verts" : verts, "faces" : faces}
    obj_name = basepath +"/" + id + ".obj"
    #print(obj_name)
    writeToObjFile(newobj, obj_name, id) # probably does not need to be written
    ori_mesh = pym.meshio.load_mesh(obj_name)  # and re-read but well, convenient for testing
    os.remove(obj_name) #delete cause it won't be used later for the neuroglancer format transformation

    # to ouput the zero-centred object:
    mesh = pym.form_mesh(ori_mesh.vertices - T, ori_mesh.faces)

    firstPass = True
    df = pd.read_csv(positionlist, header=0)
    #go through csv file. column ID should match file name
    #column name will be used for readable folder names.
    #print(g)
    #os.makedirs(basepath+"/objects/")
    for index, row in df.iterrows():
        if(g not in row["id"] ):  #find the matching rows for the given mrc file
            continue
        if(firstPass):
            #print(row["name"])
            if(os.path.exists(basepath+"/objects/"+row["name"]+"/input/")):
                shutil.rmtree(basepath+"/objects/"+row["name"]+"/input/")
            #create a new empty folder for the output
            os.makedirs(basepath+"/objects/"+row["name"]+"/input/")
            makeYamlFiles(basepath+"/objects/"+row["name"]) #yaml files needed for the conversion to neuroglancer readable format in the next step.
            firstPass = False


        h =  [str(ord(c)) for c in row["id"]]
        #print(h)
        id = ''.join(h)+str(index)
        # Rotation matrix
        eulers = [float(row["eux"]),float(row["euy"]),float(row["euz"])]
        rot = R.from_euler("ZXZ", eulers, degrees=True)

        # translate to zero
        mesh = pym.form_mesh(ori_mesh.vertices - T, ori_mesh.faces)

        # rotate
        newVertices = np.dot(rot.as_matrix(), mesh.vertices.T).T
        rotMesh = pym.form_mesh(newVertices, ori_mesh.faces)

        # translate back
        # here I guess 'T' should be the position in the tomogram from the csv
        T_final = np.array([float(row['x']),float(row['y']),float(row['z'])],dtype=float)
        newMesh = pym.form_mesh( rotMesh.vertices + T_final, rotMesh.faces)
        #print(index)
        #save: The object names are a concatenation of the type and the place in the CSV file. This creates a unique ID which is used later on. Must be numerical.
        pym.save_mesh(basepath+"/objects/"+row["name"]+"/input/" +id + ".obj",newMesh)

print("Done : Created object files inside the objects folder.")

