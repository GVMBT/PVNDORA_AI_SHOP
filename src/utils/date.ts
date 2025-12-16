/**
 * Date Formatting Utilities
 * 
 * Centralized date formatting functions.
 */

/**
 * Format date as relative time (e.g., "5m ago", "2h ago", "3d ago")
 * 
 * @param date - Date string or Date object
 * @returns Formatted relative time string
 * 
 * @example
 * ```ts
 * formatRelativeTime('2024-01-01T10:00:00Z') // "2h ago"
 * formatRelativeTime(new Date()) // "just now"
 * ```
 */
export function formatRelativeTime(date: string | Date): string {
  if (!date) return 'Unknown';
  
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return 'Invalid date';
  
  const now = new Date();
  const diffMs = now.getTime() - dateObj.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  
  // For older dates, use absolute format
  return formatDate(dateObj, { dateStyle: 'short' });
}

/**
 * Format date using Intl.DateTimeFormat
 */
export function formatDate(
  date: string | Date,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!date) return 'Unknown';
  
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return 'Invalid date';

  const defaultOptions: Intl.DateTimeFormatOptions = {
    dateStyle: 'medium',
    ...options,
  };

  return new Intl.DateTimeFormat('en-US', defaultOptions).format(dateObj);
}

/**
 * Format date as ISO string (YYYY-MM-DD)
 * 
 * @param date - Date string or Date object
 * @returns ISO date string or empty string if invalid
 * 
 * @example
 * ```ts
 * formatDateISO(new Date()) // "2024-01-01"
 * ```
 */
export function formatDateISO(date: string | Date): string {
  if (!date) return '';
  
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return '';

  return dateObj.toISOString().split('T')[0];
}

/**
 * Format date and time together
 * 
 * @param date - Date string or Date object
 * @param options - Intl.DateTimeFormat options
 * @returns Formatted date and time string
 * 
 * @example
 * ```ts
 * formatDateTime(new Date()) // "Jan 1, 2024, 10:00 AM"
 * ```
 */
export function formatDateTime(
  date: string | Date,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!date) return 'Unknown';
  
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return 'Invalid date';

  const defaultOptions: Intl.DateTimeFormatOptions = {
    dateStyle: 'medium',
    timeStyle: 'short',
    ...options,
  };

  return new Intl.DateTimeFormat('en-US', defaultOptions).format(dateObj);
}












