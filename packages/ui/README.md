# @family-budget/ui

Shared UI component library for Family Budget web and mobile applications.

## Overview

This package contains platform-agnostic React components that work across both web (Next.js) and mobile (React Native) platforms.

## Structure

```
packages/ui/
├── src/
│   ├── tokens/              # Design tokens
│   │   ├── colors.ts
│   │   ├── spacing.ts
│   │   ├── typography.ts
│   │   └── index.ts
│   ├── components/          # Shared components
│   │   ├── Button/
│   │   ├── Input/
│   │   ├── Card/
│   │   └── ...
│   ├── web/                 # Web-specific implementations
│   └── mobile/              # Mobile-specific implementations
└── dist/                    # Built output
```

## Usage

### Install

This package is automatically linked in the monorepo. Just import it:

```typescript
import { Button, Input, Card } from '@family-budget/ui';
import { colors, spacing } from '@family-budget/ui/tokens';
```

### Example Component

```typescript
import { Button } from '@family-budget/ui';

export function MyComponent() {
  return (
    <Button
      variant="primary"
      size="md"
      onPress={() => console.log('Clicked!')}
    >
      Add Transaction
    </Button>
  );
}
```

## Design Tokens

### Colors

```typescript
import { colors } from '@family-budget/ui/tokens';

const primary = colors.primary[500];
const success = colors.success;
```

### Spacing

```typescript
import { spacing } from '@family-budget/ui/tokens';

const margin = spacing[4]; // 16px
```

### Typography

```typescript
import { typography } from '@family-budget/ui/tokens';

const fontFamily = typography.fontFamily.primary;
const fontSize = typography.fontSize.lg;
```

## Components

### Button

```typescript
<Button
  variant="primary" | "secondary" | "outline" | "ghost" | "danger"
  size="sm" | "md" | "lg"
  disabled={false}
  loading={false}
  fullWidth={false}
  leftIcon={<Icon />}
  rightIcon={<Icon />}
  onPress={() => {}}
>
  Button Text
</Button>
```

### Input

```typescript
<Input
  type="text" | "email" | "password" | "number" | "currency"
  size="sm" | "md" | "lg"
  disabled={false}
  error="Error message"
  label="Input Label"
  placeholder="Placeholder"
  value={value}
  onChange={(value) => setValue(value)}
/>
```

### Card

```typescript
<Card
  variant="default" | "outlined" | "elevated"
  padding={spacing[4]}
  onPress={() => {}} // Optional, makes card interactive
>
  <Text>Card content</Text>
</Card>
```

## Development

### Build

```bash
npm run build
```

### Watch Mode

```bash
npm run dev
```

### Type Checking

```bash
npm run type-check
```

### Linting

```bash
npm run lint
```

## Adding New Components

1. Create component folder in `src/components/`
2. Create types in `{Component}/types.ts`
3. Create web implementation in `src/web/{Component}.tsx`
4. Create mobile implementation in `src/mobile/{Component}.tsx`
5. Export from `src/components/{Component}/index.ts`

Example:

```typescript
// src/components/Badge/types.ts
export interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'error';
  children: React.ReactNode;
}

// src/web/Badge.tsx
import { BadgeProps } from '../components/Badge/types';

export function Badge({ variant = 'default', children }: BadgeProps) {
  // Web implementation
}

// src/mobile/Badge.tsx
import { BadgeProps } from '../components/Badge/types';

export function Badge({ variant = 'default', children }: BadgeProps) {
  // Mobile implementation
}

// src/components/Badge/index.ts
import { Platform } from 'react-native';

if (Platform.OS === 'web') {
  export { Badge } from '../../web/Badge';
} else {
  export { Badge } from '../../mobile/Badge';
}
```

## Testing

```bash
npm run test
```

## Notes

- All components should have consistent APIs across platforms
- Use design tokens instead of hard-coded values
- Follow the design system guidelines
- Write tests for all components
