# Use conda base
FROM continuumio/miniconda3:22.11.1
WORKDIR /installs

# Install building tools including gcc
RUN apt update -y && \
    apt install -y build-essential && \
    rm -rf /var/lib/apt/lists/*

# Download and extract and install boost
RUN wget https://boostorg.jfrog.io/artifactory/main/release/1.81.0/source/boost_1_81_0.tar.bz2 && \
    tar --bzip2 -xf boost_1_81_0.tar.bz2 && \
    (cd boost_1_81_0 && bash bootstrap.sh && ./b2 install) && \
    rm boost_1_81_0 -r

# Enable conda
SHELL ["/bin/bash", "--login", "-c"]
RUN conda init bash

# Copy python env files
COPY multiresolution-mesh-creator ./multiresolution-mesh-creator
COPY environment-clean.yml .

# Create environment
RUN conda env update --name base --file ./multiresolution-mesh-creator/multiresolution_mesh_creator.yml && \
    conda install -c anaconda cmake && \
    conda clean -a -y

# Install dvidutils
WORKDIR /installs/multiresolution-mesh-creator/dvidutils/build
RUN cmake .. \
    -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_CXX_FLAGS_DEBUG="-g -O0 -DXTENSOR_ENABLE_ASSERT=ON" \
    -DCMAKE_PREFIX_PATH="${CONDA_PREFIX}" && \
    make && \
    make install && \
    rm ./* -r

# Install pyfqmr
WORKDIR /installs/multiresolution-mesh-creator/pyfqmr-Fast-Quadric-Mesh-Reduction
RUN python setup.py install && \
    rm ./* -r

# Install multiresolution mesh creator
WORKDIR /installs
RUN pip install ./multiresolution-mesh-creator && \
    rm multiresolution-mesh-creator -r

# Install IMP packages
RUN conda env update --name base --file environment-clean.yml && \
    conda clean -a -y && \
    conda update --all && \
    conda clean -a -y

# Install imod
RUN wget https://bio3d.colorado.edu/imod/AMD64-RHEL5/imod_4.11.24_RHEL7-64_CUDA10.1.sh && \
    bash imod_4.11.24_RHEL7-64_CUDA10.1.sh && \
    rm imod_4.11.24_RHEL7-64_CUDA10.1.sh

# Run watchdog script...
WORKDIR /app
