<div align="center">

# 🗄️ React Desk Stores

**State management stores for the React operator desk.**

</div>

---

## Stores

| Store | Purpose |
|:---|:---|
| `pipelineStore` | Pipeline state and events |
| `reviewStore` | Review queue state |
| `debugStore` | Debug ring buffer state |

## Usage

```jsx
import { usePipelineStore } from './stores/pipelineStore';

function PipelineTray() {
  const { traces, status } = usePipelineStore();
  // ...
}
```

## Related Files

- `../components/` — React components
- `../hooks/` — Custom hooks
- `../api/` — API client modules
