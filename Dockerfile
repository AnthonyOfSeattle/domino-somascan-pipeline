FROM python:3.12-bookworm

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt from your current directory to the container
COPY requirements.txt .

# Install dependencies without caching to keep the image small
RUN pip install --no-cache-dir -r requirements.txt
