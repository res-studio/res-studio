FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py playwright_scan.py deep_scan.py deep_jobs.py index.html ./
RUN useradd --create-home --uid 10001 resstudio && mkdir -p /data/jobs && chown -R resstudio:resstudio /data
USER resstudio
EXPOSE 8765
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8765"]
