import getopt
import sys
import numpy
import mrcfile
from pylab import *
import scipy.ndimage
from cloudvolume.lib import mkdir

def main(argv):
    print("Starting classmask deconstruction...")
    file = ''

    try:
        opts, args = getopt.getopt(argv, "hi:", ["input="])
    except getopt.GetoptError:
        print("error")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('extract_header.py -i <inputfile>')
            sys.exit()
        elif opt in ("-i", "--input"):
            file = arg
    
    basepath_arr = file.split("/")
    #print(basepath_arr)
    basepath = '/'.join(basepath_arr[0:len(basepath_arr)-1])
    #print(basepath)
    mrc = mrcfile.mmap(file, mode='r+', permissive=True)
    arr = mrc.data.astype(int)
    #print(type(arr))
    classes = numpy.unique(arr)
    print("Found main objects: ")
    #print(classes)
    classes = numpy.delete(classes,[0]) #delete 0 if present
    classes = classes.astype(int)
    print(classes)
    s =  [
        [
        [1,1,1],
        [1,1,1],
        [1,1,1]
        ],
        [
        [1,1,1],
        [1,1,1],
        [1,1,1]
        ],
        [
        [1,1,1],
        [1,1,1],
        [1,1,1]
        ]
    ]
    p=mkdir(basepath+"/splitClassmask/")
    for el in classes:
        newArr= numpy.where(arr == el, arr, 0) #make a new mrc, filled with 0 and only the objects with the given id.

        lw,num = scipy.ndimage.label(newArr,structure=s)
        #print(lw)
        #print(num) #classes found.
        #print(lw)
        finalArr = numpy.where(lw == 0, 0,lw+(el*1000)) #keep the zeros, but give each object a unique id starting with the id of the element.
     
        finalArr = finalArr.astype(float32)
       
        with mrcfile.new(p+"/"+str(el)+'.mrc', overwrite=True) as mrc:
            mrc.set_data(finalArr)
        
if __name__ == "__main__":
    main(sys.argv[1:])
