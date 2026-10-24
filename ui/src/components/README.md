<div align="center">

# 🧩 React Desk Components

**React components for the operator desk interface.**

</div>

---

## Components

| Component | Purpose |
|:---|:---|
| `PipelineTray` | Live pipeline status tray |
| `ReviewQueue` | Human review queue |
| `DocumentDetail` | Document inspection view |
| `DebugConsole` | Debug panel with ring buffer |

## Usage

```jsx
import { PipelineTray } from './components/PipelineTray';

function App() {
  return <PipelineTray />;
}
```

## Related Files

- `../api/` — API client modules
- `../hooks/` — Custom hooks
- `../stores/` — State management
