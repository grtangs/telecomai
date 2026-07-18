# Use the official Astral UV image as the build builder stage
FROM astralsh/uv:python3.12-bookworm-slim AS build

# Set the working directory
WORKDIR /app

# Enable bytecode compilation for faster load times
ENV UV_COMPILE_BYTECODE=1

# Copy only the dependency definitions to take advantage of Docker caching
COPY pyproject.toml /app/

# Synchronize dependencies (generates .venv and downloads packages)
RUN uv sync --no-install-project --no-dev

# Use a clean, slim Python image for the final runtime image
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy the virtual environment from the build stage
COPY --from=build /app/.venv /app/.venv

# Put the virtual environment's bin folder at the front of the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy the application source code files
COPY telecom_agent.py app.py database.py /app/

# Expose port 8080 (default for Cloud Run)
EXPOSE 8080

# Define runtime environment defaults
ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Run the Gradio dashboard
CMD ["python", "app.py"]
