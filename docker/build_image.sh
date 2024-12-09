#!/bin/bash

# Define the image name and tag
IMAGE_NAME="distributed-turn"
TAG="latest"
FULL_TAG="${IMAGE_NAME}:${TAG}"

# Check if an image with the same tag exists and remove it
if docker images -q $FULL_TAG > /dev/null; then
    echo "Image with tag $FULL_TAG exists. Removing..."
    docker rmi $FULL_TAG
fi

# Build the new image
echo "Building image $FULL_TAG..."
docker build -t $FULL_TAG .

echo "Build complete."
