/**
 * Deep transformation between snake_case and camelCase for API boundaries.
 * Django sends snake_case; frontend uses camelCase.
 */

function snakeToSingleCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_match, letter: string) => letter.toUpperCase());
}

function camelToSingleSnake(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

export class CaseTransformer {
  static snakeToCamel(obj: unknown): unknown {
    if (obj === null || obj === undefined) return obj;
    if (Array.isArray(obj)) return obj.map((item) => CaseTransformer.snakeToCamel(item));
    if (typeof obj === "object") {
      const result: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
        result[snakeToSingleCamel(key)] = CaseTransformer.snakeToCamel(value);
      }
      return result;
    }
    return obj;
  }

  static camelToSnake(obj: unknown): unknown {
    if (obj === null || obj === undefined) return obj;
    if (Array.isArray(obj)) return obj.map((item) => CaseTransformer.camelToSnake(item));
    if (typeof obj === "object") {
      const result: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
        result[camelToSingleSnake(key)] = CaseTransformer.camelToSnake(value);
      }
      return result;
    }
    return obj;
  }
}
