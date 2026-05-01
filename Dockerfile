# Dockerfile for hosted deployment (Fly.io / Render / Railway).
# Streamlit Community Cloud doesn't need this — it builds from requirements.txt directly.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for cache reuse
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app
COPY . .

# Streamlit listens on $PORT in hosted envs (Render, Fly), defaults to 8501
ENV PORT=8501
EXPOSE 8501

# Persist SQLite + runs on a mounted volume; Fly.io: fly volumes create blitz_data --size 1
RUN mkdir -p /app/runs && chmod 777 /app/runs

CMD streamlit run app/Home.py \
    --server.port=${PORT} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
