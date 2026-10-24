<div align="center">

# 📁 React Desk Source

**Source code for the optional React operator desk.**

</div>

---

## Structure

| Path | Contents |
|:---|:---|
| [`api/`](api/) | API client modules |
| [`components/`](components/) | React components |
| [`hooks/`](hooks/) | Custom React hooks |
| [`stores/`](stores/) | State management stores |
| [`types/`](types/) | TypeScript type definitions |

## Development

```bash
cd packages/The-Mailroom/ui
npm install
npm run dev      # http://127.0.0.1:5173 (proxies /api /v1 /ws → :8001)
npm run build    # ui/dist → mailroom-web mounts /desk
```

## Related Files

- `../README.md` — React desk documentation
- `../package.json` — Dependencies
