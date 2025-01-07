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

# Copy application files
COPY src/ /app/
COPY deployment/docker/startup_scripts/ /app/startup_scripts/

# Make startup scripts executable
RUN chmod +x /app/startup_scripts/*.sh

CMD ["tail", "-f", "/dev/null"]