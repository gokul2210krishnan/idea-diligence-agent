FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    DEFAULT_MODEL_PROVIDER=gemini \
    DEFAULT_MODEL_ID=gemini-3.6-flash

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY examples ./examples

EXPOSE 8000

CMD ["python", "-m", "src.main", "--web", "--port", "8000"]
