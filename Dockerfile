# Use micromamba base
# FROM condaforge/micromambaforge:23.1.0-1
FROM mambaorg/micromamba
# FROM ubuntu:20.04

WORKDIR /installs
# Install micromicromamba
# RUN curl micro.micromamba.pm/install.sh | bash

# Install building tools including gcc
USER root
RUN apt update -y && \
    apt install -y build-essential wget bzip2 && \
    rm -rf /var/lib/apt/lists/*

# Download and extract and install boost
RUN wget https://boostorg.jfrog.io/artifactory/main/release/1.81.0/source/boost_1_81_0.tar.bz2 && \
    tar --bzip2 -xf boost_1_81_0.tar.bz2 && \
    (cd boost_1_81_0 && bash bootstrap.sh && ./b2 install) && \
    rm boost_1_81_0* -r

# Enable conda
# SHELL ["/bin/bash", "--login", "-c"]
# RUN micromamba init bash

# Create environment
COPY multiresolution-mesh-creator ./multiresolution-mesh-creator
RUN micromamba install --name base --file ./multiresolution-mesh-creator/multiresolution_mesh_creator.yml && \
    micromamba install --name base -c anaconda cmake && \
    micromamba clean -a -y
ARG MAMBA_DOCKERFILE_ACTIVATE=1

# Install dvidutils
WORKDIR /installs/multiresolution-mesh-creator/dvidutils/build

# RUN . /opt/conda/etc/profile.d/conda.sh && \
#     conda activate multi && \
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
# RUN /opt/conda/envs/multi/bin/pip install ./multiresolution-mesh-creator && \
RUN pip install ./multiresolution-mesh-creator && \
    rm multiresolution-mesh-creator -r

# Install IMP packages
COPY environment-clean.yml .
RUN micromamba install --name base --file environment-clean.yml && \
    micromamba clean -a -y && \
    # conda update --all && \
    # conda clean -a -y && \
    rm environment-clean.yml

RUN micromamba shell init -s bash -p ~/micromamba

# Copy scripts
WORKDIR /app
# COPY with_segmentation_map ./with_segmentation_map
# COPY obj_list ./obj_list
COPY pipeline ./pipeline

# Run watchdog processor...
# USER 1001
WORKDIR /app/pipeline
ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "python", "processor.py", "/remote/input", "/remote/staging", "/remote/output", "/app/mongo_config.json"]
