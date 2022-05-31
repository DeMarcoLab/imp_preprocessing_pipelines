#older pipeline used to create meshes from volume files provided with list of coordinates/rotation
SECONDS=0;
while [[ $# -gt 0 ]]; do
  key="$1";

  case $key in
    -p|--path)
      mypath="$2"
      shift # past argument
      shift # past value
      ;;
    --default)
      DEFAULT=YES
      shift # past argument
      ;;
    *)    # unknown option
      POSITIONAL+=("$1") # save it in an array for later
      shift # past argument
      ;;
  esac
done

#echo ${mypath}

# #enable processing of hidden files starting with .
shopt -s dotglob
#generate the info file from header....'''
for i in  "${mypath}/*.mrc" 
do

    echo $i
    #unstack the mrc to tif files, index starting at 1
    rm -r "${mypath}/image_slices"
    rm "${mypath}/flipped.mrc"
    mkdir -p "${mypath}/image_slices"

    clip flipz $i "${mypath}/flipped.mrc"
    mrc2tif "${mypath}/flipped.mrc" "${mypath}/image_slices/img"

    # mkdir -p "${mypath}/bucket/dataset/image"

    
    #extract header information and convert slices to precomputed using that information   
    #python extract_header.py -i $i -s "False"
    
    #convert annotation layer
    # mkdir -p "${mypath}/bucket/dataset/coordinates/"
    # python annotation_layer_conversion.py -i "${mypath}/annotations/particles.csv" -o  "${mypath}/bucket/dataset/coordinates/"

    # #take mrc volume template and multiply it while translating/rotation. 
    # #Writes many obj files in named folder inside new folder objects
    # python multiplyObjects2.py "${mypath}/" "${mypath}/annotations/particles.csv"
    # #convert the many obj files to neuroglancer readable format
    # sh ./create_neuroglancer_meshes.sh "${mypath}"
done

echo "All done in " $SECONDS " seconds."
echo "Copy the contents of the dataset/ folder to the server."
echo "Make sure the database has a dataset pointing to the new data."
echo "If you are admin and have scp to the server set up called IMP do: "
echo "scp -r bucket/dataset/*  IMP:/home/ubuntu/workspace/IMP/datahost/folderhost/<name>"
