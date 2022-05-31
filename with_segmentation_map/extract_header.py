import mrcfile
import sys
import getopt
import json
import os
import numpy as np
import pandas as pd

# this script extracts relevant information from the header to be used in the online app.
def main(argv):
    print("Starting header extraction...")
    inputfile = ''
    basepath = ''
    name = ''
    output = {}

    try:
        opts, args = getopt.getopt(argv, "hi:s:", ["ifile=segment="])
    except getopt.GetoptError:
        print("error")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('extract_header.py -i <inputfile>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt in ("-s", "--segment"):
            segm = arg
    #print(inputfile)
    
    tmp = inputfile.split("/")[len(inputfile.split("/"))-1] #[len(inputfile.split('.'))-1]
    #print(tmp) filename
    l = inputfile.split("/")[0:len(inputfile.split("/"))-1]
    #print(l)
    basepath = "/".join(l)
    labels = pd.read_csv(basepath+"/meta/labels.csv", index_col="id").to_dict()["name"]
    print(labels)
    #print(basepath)
    name = tmp.split(".")[0]  # file name
    outputfile = basepath+"/bucket/dataset/"+name+".json"
    #print(outputfile)
    mrc = mrcfile.mmap(inputfile, mode='r+')

    voxelsize = [mrc.voxel_size.x/10, mrc.voxel_size.y /
                 10, mrc.voxel_size.z/10]  # convert from angstrom
    # print(voxelsize)
    sx = mrc.header.nx.item(0)
    sy = mrc.header.ny.item(0)
    sz = mrc.header.nz.item(0)
    output["x"] = mrc.header.nx.item(0)
    output["y"] = mrc.header.ny.item(0)
    output["z"] = mrc.header.nz.item(0)
    output["pixel_spacing"] = voxelsize
    output["min"] = mrc.header.dmin.item(0)
    output["max"] = mrc.header.dmax.item(0)
    output["mean"] = mrc.header.dmean.item(0)
    mrc.close()

    # saves some information to be used in the app later
    with open(outputfile, 'w+') as f:
        print(outputfile)
        json.dump(output, f)

    print("Done extracting header.")

    print("----")
    #call image conversion for the image. This is stupid, but the ProcessPoolExecutor in the conversion file doesn't like main functions, so this is the quick and dirty
    #solution

    #convert the image itself
    os.system("python create_cloudvolume_volume.py " +basepath +"/image_slices " + str(voxelsize[0]) + " " +   str(voxelsize[1]) + " " +   str(voxelsize[2]) + " file://" +basepath+  "/bucket/dataset/image --layer_type image --dtype float32")
    #os.system('python ../image_conversion.py ' + basepath+"/bucket/dataset/image " + basepath+"/image_slices " + str(sx) + " " + str(sy) + " " + str(sz) + " False")
    print("Done converting image data.")

    #convert the segmentations.

    directory = basepath+"/segmentation/splitClassmask/"
    os.system('mkdir ' + basepath+"/bucket/dataset/segmentation/")
    for filename in os.listdir(directory):
        #print(filename)
        if "int" in filename:
            continue
        f = os.path.join(directory,filename)
        #print(f)
        print("Processing " + filename)
        id_ = filename.split(".")[0]

        readable_name = str(id_)
        try:
            readable_name = labels[int(id_)]
        except:
            print("No readable name available in file for id: " + id_ + ". Will use id instead as key.")   

        #generates split tif images for each class .
        os.system('rm -r '+basepath+"/bucket/dataset/segmentation/"+ readable_name )
        os.system('mkdir '+basepath+"/bucket/dataset/segmentation/"+ readable_name )

        #convert to int
        os.system('newstack -in ' + f +' -ou ' + directory +"/"+id_+ '_int.mrc -mode 6 > /dev/null') 

        #make dir for slices
        os.system("rm -r  " + directory + "/" +id_+"_int_slices")
        os.system("mkdir " + directory + "/" +id_+"_int_slices")
        os.system("mrc2tif " + directory +"/"+id_+ '_int.mrc ' + directory + "/" +id_+"_int_slices/img > /dev/null")
        
        #create precomputed format
        os.system("python create_cloudvolume_volume.py " +directory + "/" +id_+"_int_slices/ "   +str(voxelsize[0])+" "+str(voxelsize[1])+" "+str(voxelsize[2])+" file://" +basepath+  "/bucket/dataset/segmentation/"+readable_name +" --layer_type segmentation --dtype uint16")
   
        #create mesh files
        os.system('python meshing.py file://'+ basepath+"/bucket/dataset/segmentation/" +  readable_name  +  " " + str(sx) + " " + str(sy) + " " + str(sz))
        
        # Make a correct properties file for each created layer of particles.
        #get the resulting classes
        mrc = mrcfile.mmap(directory +"/"+id_+ '_int.mrc', mode='r+', permissive=True)
        arr = mrc.data.astype(int)
        #print(type(arr))
        classes = np.unique(arr)
        classes = np.delete(classes,[0]) #remove 0 element
        classesstr = [str(x) for x in classes]
        #os.system('python makeSegmentation_properties.py ' + basepath+"/particlelabels/templates.csv " + basepath+"/bucket/dataset/segmentation/")

        res = {}
        res["@type"] = "neuroglancer_segment_properties"
        res["inline"] = {
            "ids":classesstr,
            #"ids": df['id'].to_list(),
            "properties":[

                {"id":"label",
                "type":"label",
                "values": classesstr},
                
            ]
        }
        #print(res)
        os.system('mkdir '+basepath+"/bucket/dataset/segmentation/"+ readable_name +"/segmentation_properties")
        with open(basepath+"/bucket/dataset/segmentation/"+readable_name+"/segmentation_properties/info",'w') as f:
            json.dump(res,f)

        #add segment_properties entry to info file of segmentation
        jsonfile = open(basepath+"/bucket/dataset/segmentation/"+readable_name+"/info","r")
        obj = json.load(jsonfile)
        jsonfile.close()
        obj["segment_properties"] = "segmentation_properties"
        jsonfile = open(basepath+"/bucket/dataset/segmentation/"+readable_name+"/info","w")
        json.dump(obj, jsonfile)
        jsonfile.close()
if __name__ == "__main__":
    main(sys.argv[1:])
