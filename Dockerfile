# Use conda base
# FROM ubuntu:focal
FROM continuumio/miniconda3:22.11.1
# FROM hzhan3/imod:4.11.5

WORKDIR /installs

# Install building tools including gcc
RUN apt update -y && \
    apt install -y build-essential wget bzip2 && \
    rm -rf /var/lib/apt/lists/*

# Install miniconda
# RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
#     bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda && \
#     rm Miniconda3-latest-Linux-x86_64.sh

# ENV PATH=/opt/conda/bin:$PATH

# Download and extract and install boost
RUN wget https://boostorg.jfrog.io/artifactory/main/release/1.81.0/source/boost_1_81_0.tar.bz2 && \
    tar --bzip2 -xf boost_1_81_0.tar.bz2 && \
    (cd boost_1_81_0 && bash bootstrap.sh && ./b2 install) && \
    rm boost_1_81_0* -r

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

RUN . /opt/conda/etc/profile.d/conda.sh && \
    conda activate base

# Install dvidutils
WORKDIR /installs/multiresolution-mesh-creator/dvidutils/build

# RUN . /opt/conda/etc/profile.d/conda.sh && \
#     conda activate base && \
RUN cmake .. \
    -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_CXX_FLAGS_DEBUG="-g -O0 -DXTENSOR_ENABLE_ASSERT=ON" \
    -DCMAKE_PREFIX_PATH="${CONDA_PREFIX}" && \
    make && \
    make install && \
    rm ./* -r

# Install pyfqmr
WORKDIR /installs/multiresolution-mesh-creator/pyfqmr-Fast-Quadric-Mesh-Reduction
# RUN . /opt/conda/etc/profile.d/conda.sh && \
#     conda activate base && \
RUN python setup.py install && \
    rm ./* -r

# Install multiresolution mesh creator
WORKDIR /installs
# RUN . /opt/conda/etc/profile.d/conda.sh && \
#     conda activate base && \
RUN pip install ./multiresolution-mesh-creator && \
    rm multiresolution-mesh-creator -r

# Install IMP packages
# RUN . /opt/conda/etc/profile.d/conda.sh && \
#     conda activate base && \
RUN conda env update --name base --file environment-clean.yml && \
    conda clean -a -y && \
    conda update --all && \
    conda clean -a -y && \
    rm environment-clean.yml

# Install imod dependancies
# Not from documentation chat-gpt suggested packages
# RUN apt-get update -y
# RUN ls lib/
# RUN DEBIAN_FRONTEND=noninteractive apt install -y libx11-dev libglu1-mesa-dev libxrandr-dev libxinerama-dev libxcursor-dev libfreetype6-dev libfontconfig1-dev libtiff5-dev libfftw3-dev libxm4 && \
#     rm -rf /var/lib/apt/lists/*


# Install imod
# RUN . /opt/conda/etc/profile.d/conda.sh && \
#     conda activate base && \
# RUN wget https://bio3d.colorado.edu/imod/AMD64-RHEL5/imod_4.11.24_RHEL7-64_CUDA10.1.sh && \
#     bash imod_4.11.24_RHEL7-64_CUDA10.1.sh -yes && \
#     rm imod_4.11.24_RHEL7-64_CUDA10.1.sh
    # wget https://bio3d.colorado.edu/imod/nightlyBuilds/imod_4.12.40_RHEL7-64_CUDA10.1.sh && \
    # bash imod_4.12.40_RHEL7-64_CUDA10.1.sh -yes && \
    # rm imod_4.12.40_RHEL7-64_CUDA10.1.sh

# Failed Workaround:
# Copy host's imod installation since installing fails
# IMOD looks like it's trying to do something clever to determine the OS and bit32/64 which fails in a docker container
# COPY imod /usr/local
# COPY imod-script /etc/profile.d
# ENV PATH=/usr/local/IMOD/bin:$PATH
# RUN echo 'export PATH="/usr/local/IMOD/bin$PATH"' >> ~/.bashrc

# New workaround: Network with this already installed docker container
# https://hub.docker.com/r/hzhan3/imod

# Copy scripts
WORKDIR /app
COPY with_segmentation_map ./with_segmentation_map
COPY obj_list ./obj_list
COPY new_obj ./new_obj

# Run watchdog script...
# RUN python watchdog_test