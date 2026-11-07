/**
 * Township One — Financial Money & Currency Precision Utility
 * 
 * Provides safe, deterministic currency arithmetic and formatting for Indian Rupee (INR).
 * Eliminates JavaScript floating-point errors by operating on integer paise representation.
 * Safely parses and formats backend Pydantic/SQLAlchemy Decimal values serialized as strings or numbers.
 */

/**
 * Safely parses string, number, or Decimal representation into a float number.
 * Returns 0 if input is null, undefined, empty, or unparseable.
 */
export function parseMoney(val: string | number | null | undefined): number {
  if (val === null || val === undefined) return 0;
  if (typeof val === 'number') {
    return isNaN(val) ? 0 : val;
  }
  if (typeof val === 'string') {
    const cleaned = val.replace(/[₹,\s]/g, '').trim();
    if (!cleaned) return 0;
    const num = parseFloat(cleaned);
    return isNaN(num) ? 0 : num;
  }
  return 0;
}

/**
 * Converts a monetary value to exact integer paise without floating point inaccuracy.
 * e.g., "6370.00" -> 637000, 12.34 -> 1234, -5.50 -> -550
 */
export function toPaise(val: string | number | null | undefined): number {
  if (val === null || val === undefined) return 0;
  if (typeof val === 'number') {
    if (isNaN(val)) return 0;
    return Math.round(val * 100);
  }
  const cleaned = val.replace(/[₹,\s]/g, '').trim();
  if (!cleaned) return 0;

  const isNegative = cleaned.startsWith('-');
  const unsigned = isNegative ? cleaned.slice(1) : cleaned;
  const parts = unsigned.split('.');
  const intPart = parseInt(parts[0] || '0', 10);
  const fracPartStr = (parts[1] || '0').padEnd(2, '0').slice(0, 2);
  const fracPart = parseInt(fracPartStr, 10);

  const paise = intPart * 100 + fracPart;
  return isNegative ? -paise : paise;
}

/**
 * Converts integer paise back to an exact 2-decimal string.
 * e.g., 637000 -> "6370.00"
 */
export function fromPaise(paise: number): string {
  if (isNaN(paise)) return '0.00';
  const isNegative = paise < 0;
  const absPaise = Math.abs(paise);
  const intPart = Math.floor(absPaise / 100);
  const fracPart = absPaise % 100;
  const formatted = `${intPart}.${fracPart.toString().padStart(2, '0')}`;
  return isNegative ? `-${formatted}` : formatted;
}

/**
 * Formats a monetary value (string, number, or Decimal) into standard Indian numbering format.
 * e.g., 6370 -> "₹6,370.00" (or "6,370.00" if showCurrency is false).
 * Never throws TypeError when invoked on string Decimal payloads.
 */
export function formatMoney(
  val: string | number | null | undefined,
  options: { showCurrency?: boolean; decimals?: number } = {}
): string {
  const { showCurrency = true, decimals = 2 } = options;
  const paise = toPaise(val);
  const isNegative = paise < 0;
  const absPaise = Math.abs(paise);
  const intPart = Math.floor(absPaise / 100);
  const fracPart = absPaise % 100;

  // Format integer portion according to Indian numbering system (e.g. 12,34,567)
  const intStr = intPart.toString();
  let formattedInt = '';
  if (intStr.length <= 3) {
    formattedInt = intStr;
  } else {
    const lastThree = intStr.slice(-3);
    const remaining = intStr.slice(0, -3);
    const chunks = remaining.replace(/\B(?=(\d{2})+(?!\d))/g, ',');
    formattedInt = `${chunks},${lastThree}`;
  }

  const fracStr = fracPart.toString().padStart(2, '0').slice(0, decimals);
  const formattedNumber = decimals > 0 ? `${formattedInt}.${fracStr}` : formattedInt;
  const withSign = isNegative ? `-${formattedNumber}` : formattedNumber;
  return showCurrency ? `₹${withSign}` : withSign;
}

/**
 * Performs safe addition of two monetary values using integer paise.
 */
export function addMoney(
  a: string | number | null | undefined,
  b: string | number | null | undefined
): number {
  return (toPaise(a) + toPaise(b)) / 100;
}

/**
 * Performs safe subtraction of two monetary values using integer paise.
 */
export function subMoney(
  a: string | number | null | undefined,
  b: string | number | null | undefined
): number {
  return (toPaise(a) - toPaise(b)) / 100;
}

/**
 * Compares two monetary values using integer paise.
 * Returns -1 if a < b, 0 if a == b, 1 if a > b.
 */
export function compareMoney(
  a: string | number | null | undefined,
  b: string | number | null | undefined
): number {
  const pA = toPaise(a);
  const pB = toPaise(b);
  if (pA < pB) return -1;
  if (pA > pB) return 1;
  return 0;
}

/**
 * Checks whether a monetary value is strictly greater than zero.
 */
export function isPositiveMoney(val: string | number | null | undefined): boolean {
  return toPaise(val) > 0;
}

/**
 * Generates a cryptographically strong UUID v4 idempotency key.
 * Uses window.crypto.randomUUID() when available.
 */
export function generateIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // RFC 4122 v4 fallback
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
