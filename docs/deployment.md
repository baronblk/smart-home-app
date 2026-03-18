# Production Deployment Guide

## Overview

The application is packaged as a multi-stage Docker image. Production deployments use `docker-compose.prod.yml` as an override file on top of the base `docker-compose.yml`.

---

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- A server with at least 1 GB RAM and 2 GB disk
- A domain name (for SSL/TLS)
- SSL certificate (Let's Encrypt recommended)

---

## Deployment Steps

### 1. Prepare the server

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Clone the repository
git clone https://github.com/baronblk/smart-home-app.git
cd smart-home-app
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set production values:

```bash
ENVIRONMENT=production
LOG_LEVEL=WARNING

# Generate a strong secret key
python scripts/generate_secret.py  # copy output to SECRET_KEY

# Use your PostgreSQL credentials
POSTGRES_PASSWORD=<strong_random_password>

# Set FRITZ_MOCK_MODE=false for real hardware
FRITZ_MOCK_MODE=false
FRITZ_HOST=192.168.178.1
FRITZ_USERNAME=admin
FRITZ_PASSWORD=<fritz_password>
```

### 3. Configure SSL

Place your SSL certificate files in `certs/`:
```
certs/
├── fullchain.pem
└── privkey.pem
```

For Let's Encrypt:
```bash
certbot certonly --standalone -d yourdomain.com
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem certs/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem certs/
```

Update `docker/nginx/nginx.conf` to match your domain.

### 4. Start the application

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 5. Run migrations and seed

First-time setup only:
```bash
docker-compose exec app alembic upgrade head
docker-compose exec app python seeds/run_seeds.py
```

### 6. Verify

```bash
# Check all containers are running
docker-compose ps

# Check application health
curl https://yourdomain.com/health

# View logs
docker-compose logs -f app
```

---

## Updating the Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build app

# Migrations run automatically via entrypoint.sh
```

---

## Container Image from GHCR

When using the published GHCR image instead of building locally:

```yaml
# In docker-compose.prod.yml, override the image:
services:
  app:
    image: ghcr.io/baronblk/smart-home-app:latest
    # Remove 'build:' section
```

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Monitoring and Maintenance

```bash
# View logs
docker-compose logs -f app

# Database backup
docker-compose exec db pg_dump -U smarthome smarthome > backup_$(date +%Y%m%d).sql

# Database restore
cat backup_20260101.sql | docker-compose exec -T db psql -U smarthome smarthome

# Container resource usage
docker stats
```

---

## Environment Variables Reference

See [`.env.example`](../.env.example) for the full list of configurable variables.

---

## FRITZ!Box Network Requirements

The application container must be able to reach the FRITZ!Box on port 49000 (TR-064) and port 80 (AHA). If the app runs on a different network segment, ensure routing and firewall rules allow this traffic.
