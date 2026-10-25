<div align="center">

# 🪝 React Desk Hooks

**Custom React hooks for the operator desk.**

</div>

---

## Hooks

| Hook | Purpose |
|:---|:---|
| `useWebSocket` | WebSocket connection management |
| `usePipeline` | Pipeline state and events |
| `useReviewQueue` | Review queue operations |
| `useDebug` | Debug ring buffer access |

## Usage

```jsx
import { usePipeline } from './hooks/usePipeline';

function PipelineTray() {
  const { traces, status } = usePipeline();
  // ...
}
```

## Related Files

- `../components/` — React components
- `../api/` — API client modules
- `../stores/` — State management
