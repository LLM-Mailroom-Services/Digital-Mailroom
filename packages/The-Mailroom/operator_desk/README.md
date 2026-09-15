<div align="center">

# 🖥️ Operator Desk

**Docker Compose configuration for the Mailroom Operator Desk.**

</div>

---

## Structure

| Path | Contents |
| :--- | :--- |
| [`docker-compose.yml`](docker-compose.yml) | Docker Compose configuration |
| [`nginx/`](nginx/) | Nginx reverse proxy configuration |

## Running

```bash
cd packages/The-Mailroom/operator_desk
docker compose --profile ui up --build
```

## Profiles

| Profile | Services |
| :--- | :--- |
| `ui` | React operator desk + backend |
| `default` | Pixel console + backend |

## Related Files

- `ui/` — React operator desk source
- `hosted/` — Observatory (hosted edition)
- `server/` — Backend server
