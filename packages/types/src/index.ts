// Shared TypeScript types and interfaces

// User types
export interface User {
  id: string;
  email: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}

// Household types
export interface Household {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}

// Transaction types
export interface Transaction {
  id: string;
  accountId: string;
  householdId: string;
  amount: number;
  date: string;
  name: string;
  merchantName?: string;
  categoryId?: string;
  pending: boolean;
  isManual: boolean;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

// Budget types
export interface Budget {
  id: string;
  householdId: string;
  categoryId: string;
  amount: number;
  periodType: 'monthly' | 'custom';
  startDate?: string;
  endDate?: string;
  rolloverEnabled: boolean;
  createdAt: string;
}

// Category types
export interface Category {
  id: string;
  householdId: string;
  name: string;
  type: 'income' | 'expense';
  color: string;
  icon?: string;
  parentCategoryId?: string;
  isSystem: boolean;
  createdAt: string;
}

// Bill types
export interface Bill {
  id: string;
  householdId: string;
  name: string;
  amount: number;
  dueDate: string;
  recurrenceRule?: string;
  categoryId?: string;
  isAutomatic: boolean;
  reminderDaysBefore?: number;
  createdAt: string;
}

// Savings Goal types
export interface SavingsGoal {
  id: string;
  householdId: string;
  name: string;
  targetAmount: number;
  currentAmount: number;
  targetDate?: string;
  categoryId?: string;
  priority: number;
  createdAt: string;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// Error types
export interface ApiError {
  message: string;
  code: string;
  details?: Record<string, unknown>;
}
