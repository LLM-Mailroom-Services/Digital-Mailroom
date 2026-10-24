<div align="center">

# 📐 React Desk Types

**TypeScript type definitions for the React operator desk.**

</div>

---

## Type Definitions

| File | Purpose |
|:---|:---|
| `pipeline.ts` | Pipeline trace and status types |
| `review.ts` | Review queue types |
| `document.ts` | Document and extraction types |
| `debug.ts` | Debug event types |

## Usage

```typescript
import { PipelineTrace } from './types/pipeline';

const trace: PipelineTrace = {
  id: '...',
  status: 'completed',
  // ...
};
```

## Related Files

- `../components/` — React components
- `../api/` — API client modules
- `../stores/` — State management
