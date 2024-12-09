# Use an official Python runtime as a parent image
FROM ubuntu:20.04

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

RUN apt-get update
RUN apt-get install tcpdump net-tools iptables iproute2 vim -y

# Install any needed packages specified in requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt


CMD ['sleep', '100000']
# Run app.py when the container launches
# CMD ["python", "app.py"]
