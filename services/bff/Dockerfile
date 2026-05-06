FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY src/ src/
COPY resources/ resources/

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
EXPOSE 30001

CMD ["python", "src/main.py"]
