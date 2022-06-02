#python multiplyObjects2.py ./synthetic_2/objects synthetic_2/synthetic2_particles.csv


for dir in "$1"/objects/*/; 
    do 
     echo "$dir";
     name=$(basename "$dir")
     echo "$name"
     #echo "${dir##*/}"
     create-multiresolution-meshes $dir -n 10
    
    #rename resulting folder to match for easier upload
     mkdir  "$1/bucket/dataset/coordinates/${name%%*( )}.mesh/" 
     cp -r $dir/meshes/multires/*  $1/bucket/dataset/coordinates/${name%%*( )}.mesh/
     #rm -rf "$dir/meshes/multires/"
    done

#copy the stuff over