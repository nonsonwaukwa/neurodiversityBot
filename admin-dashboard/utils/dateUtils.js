import { format } from 'date-fns';

// Safe date formatting utility functions

/**
 * Safely formats a date of various types (string, number, Firestore timestamp, Date)
 * @param {any} dateValue - The date value to format
 * @param {string} formatString - The date-fns format string
 * @param {string} fallbackValue - Value to return if date is invalid
 * @returns {string} Formatted date string or fallback value
 */
export function safeFormatDate(dateValue, formatString = 'MMM dd, yyyy', fallbackValue = 'N/A') {
  if (!dateValue) return fallbackValue;
  
  try {
    // Handle Firestore timestamp objects
    if (dateValue && typeof dateValue === 'object' && dateValue.seconds) {
      return format(new Date(dateValue.seconds * 1000), formatString);
    }
    
    // Handle regular Date objects
    if (dateValue instanceof Date) {
      return format(dateValue, formatString);
    }
    
    // Handle string dates
    return format(new Date(dateValue), formatString);
  } catch (error) {
    console.warn('Invalid date value:', dateValue, error);
    return fallbackValue;
  }
}

/**
 * Safely converts a date/time value to milliseconds for sorting
 * @param {any} dateValue - The date value to convert
 * @returns {number} Milliseconds since epoch, or 0 if invalid
 */
export function dateToMillis(dateValue) {
  if (!dateValue) return 0;
  
  try {
    // Handle Firestore timestamp objects
    if (dateValue && typeof dateValue === 'object' && dateValue.seconds) {
      return dateValue.seconds * 1000;
    }
    
    // Handle Date objects
    if (dateValue instanceof Date) {
      return dateValue.getTime();
    }
    
    // Handle strings/numbers
    return new Date(dateValue).getTime();
  } catch (error) {
    console.warn('Invalid date value for conversion:', dateValue, error);
    return 0;
  }
} 