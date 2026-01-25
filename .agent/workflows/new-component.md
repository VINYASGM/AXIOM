---
description: Create a new React component for AXIOM frontend
---

# Create New Frontend Component

## AXIOM Design Principles
- Rich, premium aesthetics (gradients, glassmorphism, micro-animations)
- Confidence scores always visible
- Real-time feedback on user actions
- Dark mode first

## Steps

1. Create component in `apps/web/components/{ComponentName}/`
```
{ComponentName}/
├── index.tsx           # Main component
├── {ComponentName}.module.css  # Scoped styles (if needed)
└── types.ts            # TypeScript types
```

2. Component template:
```tsx
'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';

interface {ComponentName}Props {
  // Define props
}

export function {ComponentName}({ }: {ComponentName}Props) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="..."
    >
      {/* Component content */}
    </motion.div>
  );
}
```

3. Export from `apps/web/components/index.ts`

// turbo
4. Check for type errors
```bash
cd apps/web && npm run typecheck
```

## Key Components to Reference
- `IntentCanvas` - Main input interface
- `ReviewPanel` - Output display with confidence
- `ConfidenceIndicator` - Reusable confidence display
