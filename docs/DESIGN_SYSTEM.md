# Wumbo App - Design System

> **Note**: This document will be finalized during Phase 1 implementation. The structure below provides a framework for maintaining consistent design across web and mobile platforms.

## Overview

This design system ensures consistent visual design and user experience across:
- **Web Application** (Next.js)
- **Mobile Application** (React Native/Expo)

## Design Principles

### Core Principles (To be defined)
1. **Clarity** - Clear, understandable interface elements
2. **Consistency** - Same patterns across platforms
3. **Efficiency** - Quick access to financial information
4. **Accessibility** - WCAG 2.1 AA compliance
5. **Trust** - Professional, reliable appearance for financial data

---

## Design Tokens

Design tokens are platform-agnostic values that define the visual language of the application.

### Colors

**To be defined during Phase 1**

```typescript
// packages/ui/tokens/colors.ts

export const colors = {
  // Brand colors
  primary: {
    50: '#...',
    100: '#...',
    // ... 500 (main), 900
  },

  // Semantic colors
  success: '#...',
  warning: '#...',
  error: '#...',
  info: '#...',

  // Neutral colors
  gray: {
    50: '#...',
    // ... to 900
  },

  // Background
  background: {
    primary: '#...',
    secondary: '#...',
  },

  // Text
  text: {
    primary: '#...',
    secondary: '#...',
    disabled: '#...',
  },

  // Dark mode variants
  dark: {
    // ...
  }
}
```

**Considerations**:
- Financial apps often use blue/green for trust
- Red for expenses, green for income (standard)
- High contrast for accessibility
- Dark mode support from day 1

### Typography

**To be defined during Phase 1**

```typescript
// packages/ui/tokens/typography.ts

export const typography = {
  fontFamily: {
    primary: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    mono: '"JetBrains Mono", "SF Mono", Consolas, monospace', // For currency/numbers
  },

  fontSize: {
    xs: '12px',
    sm: '14px',
    base: '16px',
    lg: '18px',
    xl: '20px',
    '2xl': '24px',
    '3xl': '30px',
    '4xl': '36px',
  },

  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  lineHeight: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.75,
  },
}
```

**Considerations**:
- Monospace font for currency amounts (alignment)
- Clear hierarchy (headings vs. body)
- Optimized for readability of financial data

### Spacing

**To be defined during Phase 1**

```typescript
// packages/ui/tokens/spacing.ts

export const spacing = {
  0: '0px',
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
  20: '80px',
}
```

**System**: 4px base unit (standard for both web and mobile)

### Border Radius

```typescript
export const borderRadius = {
  none: '0px',
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  full: '9999px',
}
```

### Shadows

```typescript
export const shadows = {
  sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
}
```

---

## Components

All components follow a consistent API across web and mobile platforms.

### Component Structure

Each component has:
- Shared TypeScript types
- Platform-specific implementations (web/mobile)
- Consistent prop API
- Size variants: `sm`, `md`, `lg`
- Style variants: `primary`, `secondary`, `outline`, `ghost`

### Core Components (Phase 1)

#### Button

```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  onPress: () => void;
  children: ReactNode;
}
```

**Usage**:
```tsx
<Button variant="primary" size="md" onPress={handleSubmit}>
  Add Transaction
</Button>
```

#### Input

```typescript
interface InputProps {
  type?: 'text' | 'email' | 'password' | 'number' | 'currency';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  error?: string;
  label?: string;
  placeholder?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  value: string;
  onChange: (value: string) => void;
}
```

**Special**: `type="currency"` for formatted money input

#### Card

```typescript
interface CardProps {
  variant?: 'default' | 'outlined' | 'elevated';
  padding?: keyof typeof spacing;
  children: ReactNode;
  onPress?: () => void; // Makes card interactive
}
```

#### Badge

```typescript
interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  size?: 'sm' | 'md' | 'lg';
  children: ReactNode;
}
```

**Usage**: Category labels, status indicators

### Financial Components (Phase 2+)

#### CurrencyDisplay

```typescript
interface CurrencyDisplayProps {
  amount: number;
  currency?: 'USD' | 'EUR' | 'GBP'; // Extensible
  variant?: 'default' | 'compact' | 'accounting';
  showSign?: boolean; // +/- prefix
  colorize?: boolean; // Red for negative, green for positive
}
```

#### TransactionCard

Financial transaction display with consistent styling

#### BudgetProgress

Progress bar showing budget usage

#### CategoryIcon

Standardized category icons

---

## Platform Considerations

### Web (Next.js + Tailwind)

- Uses Tailwind CSS utility classes
- Server Components where possible
- Responsive breakpoints:
  - sm: 640px
  - md: 768px
  - lg: 1024px
  - xl: 1280px
  - 2xl: 1536px

### Mobile (React Native + NativeWind)

- NativeWind for Tailwind-like utilities
- Native components (TouchableOpacity, TextInput)
- Safe area handling
- Platform-specific adjustments (iOS vs Android)

### Cross-Platform Compatibility

**Shared**:
- Same prop APIs
- Same color tokens
- Same spacing scale
- Same component variants

**Platform-Specific**:
- Web: HTML elements, CSS
- Mobile: React Native components, StyleSheet

---

## Accessibility

### Requirements (WCAG 2.1 AA)

- [ ] Color contrast ratio ≥ 4.5:1 for normal text
- [ ] Color contrast ratio ≥ 3:1 for large text
- [ ] Interactive elements ≥ 44x44px touch target (mobile)
- [ ] Keyboard navigation support (web)
- [ ] Screen reader compatibility
- [ ] Focus indicators
- [ ] Semantic HTML (web)
- [ ] Accessible labels (mobile)

### Financial Data Accessibility

- Screen readers announce currency amounts clearly
- Color not the only indicator (use icons/text)
- High contrast for readability of numbers
- Clear visual hierarchy for transactions

---

## Dark Mode

### Strategy

- Support from launch (Phase 1)
- System preference detection
- Manual toggle option
- Persistent user preference

### Implementation

```typescript
// Use semantic color tokens that adapt to theme
<Card backgroundColor={colors.background.primary}>
```

Dark mode variants defined in color tokens.

---

## Component Development Workflow

### Creating a New Component

1. **Define types** in `packages/ui/components/{ComponentName}/types.ts`
2. **Create web implementation** in `packages/ui/web/{ComponentName}.tsx`
3. **Create mobile implementation** in `packages/ui/mobile/{ComponentName}.tsx`
4. **Export** from `packages/ui/index.ts`
5. **Document** in Storybook (optional)
6. **Test** on both platforms

### Example Structure

```
packages/ui/components/Button/
├── types.ts           # Shared TypeScript types
├── Button.web.tsx     # Web implementation
├── Button.native.tsx  # Mobile implementation
└── index.ts           # Platform-specific export
```

```typescript
// packages/ui/components/Button/index.ts
import { Platform } from 'react-native';

export { ButtonProps } from './types';

if (Platform.OS === 'web') {
  export { Button } from './Button.web';
} else {
  export { Button } from './Button.native';
}
```

---

## Storybook (Optional)

Consider adding Storybook for component documentation and testing:
- Visual regression testing
- Component playground
- Documentation
- Design review

---

## Future Enhancements

- [ ] Animation/transition library
- [ ] Iconography system (custom icon set)
- [ ] Illustration style guide
- [ ] Email template design system
- [ ] Data visualization standards (charts, graphs)
- [ ] Empty states library
- [ ] Error states library
- [ ] Loading states library
- [ ] Form validation patterns

---

## Resources

### Design Tools
- **Figma** (optional) - Design mockups
- **Storybook** (optional) - Component catalog
- **Chromatic** (optional) - Visual testing

### Inspiration
- Stripe Dashboard (clean financial UI)
- Notion (modern, consistent design)
- Linear (excellent dark mode)
- shadcn/ui (component API patterns)

### References
- [Material Design 3](https://m3.material.io/)
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [WCAG 2.1](https://www.w3.org/WAI/WCAG21/quickref/)

---

*This document will be iteratively updated during Phase 1 implementation as design decisions are made.*
