FROM mcr.microsoft.com/devcontainers/python:3.10

# System-level deps for native extensions (kuzu builds from source on some archs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
