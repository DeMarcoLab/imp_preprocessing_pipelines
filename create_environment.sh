echo "Creating preprocessing environment..."
conda clean -a
conda remove -n preprocessing --all
conda env update -n preprocessing --file ./multiresolution-mesh-creator/multiresolution_mesh_creator.yml
conda activate preprocessing

echo "Building and installing dvidutils..."
rm -r ./multiresolution-mesh-creator/dvidutils/build
mkdir ./multiresolution-mesh-creator/dvidutils/build
(cd ./multiresolution-mesh-creator/dvidutils/build && cmake .. \
    -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_CXX_FLAGS_DEBUG="-g -O0 -DXTENSOR_ENABLE_ASSERT=ON" \
    -DCMAKE_PREFIX_PATH="${CONDA_PREFIX}" && make && make install)

echo "Installing pyfqmr..."
(cd ./multiresolution-mesh-creator/pyfqmr-Fast-Quadric-Mesh-Reduction && python setup.py install)

echo "Installing multiresolution mesh creator..."
pip install ./multiresolution-mesh-creator

echo "Updating with IMP packages..."
conda env update --file environment-clean.yml
conda update --all