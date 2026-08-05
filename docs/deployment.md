# Deployment Guide

The application is fully containerized using Docker, making deployment to a VPS (e.g. AWS EC2, DigitalOcean Droplet) straightforward.

## Production Checklist

Before deploying, ensure you have:
1. Replaced the dummy `SECRET_KEY` in `.env` with a strong cryptographic key (`openssl rand -hex 32`).
2. Configured a valid `GOOGLE_API_KEY`.
3. Set `ENVIRONMENT=production`.

## Docker Compose Deployment

The provided `docker-compose.yml` runs the Postgres database, FastAPI backend, and Next.js frontend.

```bash
# Start all services in detached mode
docker-compose up -d --build
```

### Persistent Volumes
The following Docker volumes are created to ensure data persists across container restarts:
- `postgres_data`: Relational data (users, documents, analysis results).
- `backend_uploads`: The actual uploaded PDF/DOCX files.
- `backend_chroma`: The embedded ChromaDB vector store.

## Reverse Proxy (Nginx)

For a production deployment, you should place a reverse proxy like Nginx in front of the application to handle SSL/TLS termination and route traffic.

* Route `yourdomain.com/api/*` to the FastAPI backend (`http://localhost:8000/api/`).
* Route all other traffic to the Next.js frontend (`http://localhost:3000`).
