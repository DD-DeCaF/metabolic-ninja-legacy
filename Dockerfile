FROM biosustain/cameo-solvers:647d6ebdf3dd

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH /app

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --upgrade --process-dependency-links -r requirements.txt

COPY . /app
