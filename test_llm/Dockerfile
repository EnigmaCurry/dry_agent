FROM ghcr.io/abetlen/llama-cpp-python:latest
RUN pip install instructor pydantic
RUN mkdir -p /llama
ADD schema.json /llama/schema.json
ADD docker.py /llama/docker.py

