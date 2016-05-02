FROM ubuntu:14.04
MAINTAINER Niko Sonnenschein <niko.sonnenschein@gmail.com>
USER root
RUN echo "from scratch"
RUN apt-get -y update && apt-get install -y swig libzmq3-dev libgmp-dev libglpk-dev glpk-utils \
            pandoc libxml2 libxml2-dev zlib1g zlib1g-dev bzip2 libbz2-dev build-essential wget curl
ADD miniconda.sh miniconda.sh
ADD requirements.txt requirements.txt
ADD cplex cplex
RUN bash miniconda.sh -b -p /root/miniconda
ENV PATH "/root/miniconda/bin:$PATH"
RUN hash -r
RUN conda config --set always_yes yes --set changeps1 no
RUN conda update -q conda
# Useful for debugging any issues with conda
RUN conda info -a
RUN conda create -y -n app scipy numpy bokeh pandas numexpr jupyter lxml python=3.4
RUN /bin/bash -c "source activate app && pip install -r requirements.txt"
RUN /bin/bash -c "source activate app && cd cplex/python/3.4/x86-64_linux/ && python setup.py install"

EXPOSE 5000

COPY . /app
WORKDIR /app
ENTRYPOINT ["/root/miniconda/envs/app/bin/python"]
CMD ["metabolic-ninja.py"]