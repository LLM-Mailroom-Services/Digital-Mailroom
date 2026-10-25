<div align="center">

# 🌐 Nginx Configuration

**Nginx reverse proxy configuration for the Operator Desk.**

</div>

---

## Purpose

Nginx serves as a reverse proxy for the Mailroom Operator Desk, routing requests to the appropriate backend services.

## Configuration

| File | Purpose |
|:---|:---|
| `nginx.conf` | Main Nginx configuration |

## Usage

The Nginx configuration is automatically loaded when running the Operator Desk via Docker Compose.

## Related Files

- `../docker-compose.yml` — Docker Compose configuration
- `../` — Operator Desk directory
