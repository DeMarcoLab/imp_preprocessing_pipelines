# Use conda base
FROM continuumio/miniconda3
WORKDIR /installs

# Install building tools including gcc
RUN apt update -y
RUN apt install -y build-essential
RUN apt clean all -y

# Download and extract boost
RUN wget https://boostorg.jfrog.io/artifactory/main/release/1.81.0/source/boost_1_81_0.tar.bz2
RUN tar --bzip2 -xf boost_1_81_0.tar.bz2

# Install boost
WORKDIR /installs/boost_1_81_0/
RUN bash bootstrap.sh
RUN ./b2 install

# Enable conda
SHELL ["/bin/bash", "--login", "-c"]
RUN conda init bash

# Copy python env files
WORKDIR /installs
COPY multiresolution-mesh-creator ./multiresolution-mesh-creator
COPY environment-clean.yml .

# Create environment
RUN conda env update --name base --file ./multiresolution-mesh-creator/multiresolution_mesh_creator.yml
RUN conda install -c anaconda cmake

# Install dvidutils
WORKDIR /installs/multiresolution-mesh-creator/dvidutils/build
RUN cmake .. \
    -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_CXX_FLAGS_DEBUG="-g -O0 -DXTENSOR_ENABLE_ASSERT=ON" \
    -DCMAKE_PREFIX_PATH="${CONDA_PREFIX}"
RUN make
RUN make install

# Install pyfqmr
WORKDIR /installs/multiresolution-mesh-creator/pyfqmr-Fast-Quadric-Mesh-Reduction
RUN python setup.py install

# Install multiresolution mesh creator
WORKDIR /installs/multiresolution-mesh-creator
RUN pip install .

# Clean up
RUN conda clean -a -y

# Install IMP packages
WORKDIR /installs
RUN conda env update --name base --file environment-clean.yml

# Update conda packages
RUN conda update --all

# Clean up
RUN conda clean -a -y

# Install imod
RUN wget https://bio3d.colorado.edu/imod/AMD64-RHEL5/imod_4.11.24_RHEL7-64_CUDA10.1.sh
RUN bash imod_4.11.24_RHEL7-64_CUDA10.1.sh

# Run watchdog script...
WORKDIR /app
