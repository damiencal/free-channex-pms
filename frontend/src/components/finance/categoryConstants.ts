export const EXPENSE_CATEGORIES = [
  'repairs_maintenance',
  'supplies',
  'utilities',
  'non_mortgage_interest',
  'owner_reimbursable',
  'advertising',
  'travel_transportation',
  'professional_services',
  'legal',
  'insurance',
  'resort_lot_rental',
  'cleaning_service',
]

export const NON_EXPENSE_CATEGORIES = [
  'owner_deposit',
  'loan_payment',
  'transfer',
  'personal',
]

export const ALL_CATEGORIES = [...EXPENSE_CATEGORIES, ...NON_EXPENSE_CATEGORIES]

export function formatCategoryName(cat: string): string {
  return cat
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}
