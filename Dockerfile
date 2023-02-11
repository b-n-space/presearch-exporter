FROM python:3.11-slim-bullseye

ENV PYTHONUNBUFFERED 1

# Install pip requirements
COPY ./requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Define working directory
RUN mkdir /code
WORKDIR /code

COPY main.py .

# Expose Uvicorn port
EXPOSE 8000

# Command to serve API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# Todo (Nour): Issue with CTRL+C https://github.com/encode/uvicorn/issues/1649

# docker buildx build --platform linux/amd64 --push -t nourspace/presearch-exporter .
