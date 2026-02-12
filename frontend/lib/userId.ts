/**
 * Utility for managing persistent user_id across sessions
 * This user_id is used to maintain learned categorization rules
 * across multiple statement uploads
 */

const USER_ID_KEY = 'statement_analyzer_user_id'

/**
 * Generate a simple UUID v4
 */
function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

/**
 * Get or create persistent user_id from localStorage
 * Returns the same user_id across all sessions for this browser
 */
export function getUserId(): string {
  // Check if we're in browser environment
  if (typeof window === 'undefined') {
    return '' // Return empty for SSR
  }

  try {
    // Try to get existing user_id
    let userId = localStorage.getItem(USER_ID_KEY)
    
    if (!userId) {
      // Generate new user_id if it doesn't exist
      userId = generateUUID()
      localStorage.setItem(USER_ID_KEY, userId)
      console.log('Generated new user_id:', userId)
    }
    
    return userId
  } catch (error) {
    // Fallback if localStorage is not available
    console.warn('localStorage not available, using session-only user_id')
    return generateUUID()
  }
}

/**
 * Clear the stored user_id (for testing or reset)
 */
export function clearUserId(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(USER_ID_KEY)
  }
}
