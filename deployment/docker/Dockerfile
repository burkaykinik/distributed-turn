FROM ubuntu:20.04

WORKDIR /app

# Install required packages
RUN apt-get update && \
    apt-get install -y \
    python3 \
    tcpdump \
    net-tools \
    iptables \
    iproute2 \
    traceroute \
    vim

# Create directory structure
RUN mkdir -p /app/src/server /app/src/peer

# Copy application files
COPY src/server/*.py /app/src/server/
COPY src/peer/*.py /app/src/peer/
COPY deployment/docker/startup_scripts/ /app/startup_scripts/

# Make startup scripts executable
RUN chmod +x /app/startup_scripts/*.sh

# Create __init__.py files for Python packages
RUN touch /app/src/__init__.py /app/src/server/__init__.py /app/src/peer/__init__.py

CMD ["tail", "-f", "/dev/null"]