FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    requests \
    openai \
    pydantic \
    fastmcp

# Copy environment code
COPY envs/data_cleaning_env/server/ ./server/
COPY envs/data_cleaning_env/tasks/ ./tasks/

# Copy inference script
COPY inference.py .

# Expose port
EXPOSE 7860

# Start server
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]