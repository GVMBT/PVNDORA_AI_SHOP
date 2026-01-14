/**
 * Random Utilities
 *
 * Utility functions for random number generation.
 *
 * SECURITY NOTE:
 * These functions use Math.random() which is NOT cryptographically secure.
 * This is intentional and safe for our use cases:
 * - UI animations and visual effects
 * - Mock data generation for charts
 * - Particle systems and audio effects
 * - Session IDs for display purposes only
 *
 * For cryptographic/security purposes (tokens, passwords, auth),
 * use crypto.getRandomValues() or the Web Crypto API instead.
 *
 * @see https://developer.mozilla.org/en-US/docs/Web/API/Crypto/getRandomValues
 */

/**
 * Generate random number between min and max (inclusive)
 */
export function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * Generate random floating point number between min and max
 */
export function randomFloat(min: number, max: number): number {
  return Math.random() * (max - min) + min;
}

/**
 * Generate random item from array
 */
export function randomItem<T>(array: readonly T[]): T {
  return array[randomInt(0, array.length - 1)];
}

/**
 * Generate random character from string
 */
export function randomChar(chars: string): string {
  return chars[randomInt(0, chars.length - 1)];
}

/**
 * Random boolean (50/50 chance)
 */
export function randomBool(): boolean {
  return Math.random() >= 0.5;
}

/**
 * Random boolean with probability
 * @param probability - Probability between 0 and 1 (e.g., 0.3 = 30% chance)
 */
export function randomBoolWithProbability(probability: number): boolean {
  return Math.random() < probability;
}

/**
 * Shuffle array in place (Fisher-Yates)
 */
export function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = randomInt(0, i);
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}
