FROM python:3.11-bullseye

RUN apt-get update && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install jupyterlab

EXPOSE 8888

RUN useradd -ms /bin/bash jupyter
USER jupyter

CMD [ "jupyter", "lab", "--ip", "0.0.0.0", "--port", "8888" ]
