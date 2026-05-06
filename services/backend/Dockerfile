FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY src/ src/

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
EXPOSE 30002

CMD ["python", "src/main.py"]
