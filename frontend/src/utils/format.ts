/** Append Z if string has no timezone suffix, so new Date() treats it as UTC. */
function toUtcString(d: string): string {
  return /[Z+\-]\d{2}:\d{2}$|Z$/.test(d) ? d : d + 'Z'
}

export function formatDatetime(d: string | null | undefined): string {
  if (!d) return '—'
  return new Date(toUtcString(d)).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })
}

export function formatDate(d: string | null | undefined): string {
  if (!d) return '—'
  return new Date(toUtcString(d)).toLocaleDateString('vi-VN')
}

/** Parse a naive datetime string from backend as UTC, returning a Date object in local time.
 *  Use this when pre-filling a DatePicker that expects local Date. */
export function parseDatetimeUTC(d: string | null | undefined): Date | null {
  if (!d) return null
  return new Date(toUtcString(d))
}
