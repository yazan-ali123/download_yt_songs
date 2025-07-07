# 1. Start with an official Python base image
FROM python:3.11-slim

# 2. Install FFmpeg (This is the crucial step that fixes your error)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Copy your Python requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code into the container
COPY . .

# 6. Expose the port the app will run on
EXPOSE 8000

# 7. Define the command to run your app (This replaces the Procfile)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]