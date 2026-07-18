# ---- Build stage: install dependencies using uv ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS build

WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files first to leverage Docker layer caching
COPY pyproject.toml uv.lock README.md /app/

# Install dependencies into a virtual environment (no project install, no dev deps)
RUN uv sync --frozen --no-install-project --no-dev

# ---- Runtime stage: slim Python image ----
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy the virtual environment from the build stage
COPY --from=build /app/.venv /app/.venv

# Add the venv bin to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source files
COPY telecom_agent.py app.py database.py /app/

# Expose Cloud Run's default port
EXPOSE 8080

# Runtime environment variables
ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Launch the Gradio app
CMD ["python", "app.py"]
