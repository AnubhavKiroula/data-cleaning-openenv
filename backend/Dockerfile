FROM python:3.11-slim as builder

WORKDIR /tmp

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

# Install PostgreSQL client for entrypoint.sh
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY . .

RUN chmod +x /app/entrypoint.sh
RUN mkdir -p /app/uploads

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
