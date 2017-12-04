FROM biosustain/cameo-solvers:647d6ebdf3dd
RUN apt-get -y update && apt-get install -y git

ADD requirements.txt requirements.txt
RUN pip install --upgrade --process-dependency-links -r requirements.txt

ADD . ./metabolic-ninja
WORKDIR metabolic-ninja

ENV PYTHONPATH $PYTHONPATH:/metabolic-ninja
RUN pwd