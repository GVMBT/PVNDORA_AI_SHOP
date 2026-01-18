import { v4 as uuidv4 } from "uuid";

export const generateId = (prefix: string): string => {
  return `${prefix}_${uuidv4()}`;
};

/**
 * Generate a short random ID (8 characters)
 */
export const generateShortId = (): string => {
  return uuidv4().slice(0, 8);
};

/**
 * Generate a hash-like ID (12 hex characters by default)
 */
export const generateHashId = (length: number = 12): string => {
  const uuid = uuidv4().replaceAll("-", "");
  return uuid.slice(0, length).toUpperCase();
};
