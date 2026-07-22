
FROM python:3.11-slim
 
WORKDIR /app
 
# Install Python dependencies first (cached separately from app code,
# so rebuilds are fast unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy the rest of the app
COPY . .
 
# Where the generated report gets written inside the container
RUN mkdir -p /app/output
 
# FastAPI's default port
EXPOSE 8000
 
# Default: run the API server.
# To run the old CLI script instead, override at run time:
#   docker run ... report-agent python agent_report.py
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
