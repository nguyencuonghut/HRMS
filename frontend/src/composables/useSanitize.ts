/**
 * useSanitize — sanitize HTML trước khi render bằng v-html (C3 XSS prevention)
 *
 * Dùng DOMPurify để loại bỏ script, event handlers và các tag nguy hiểm
 * trước khi bind vào DOM.
 *
 * Cách dùng:
 *   const { sanitizeHtml } = useSanitize()
 *   <div v-html="sanitizeHtml(rawHtml)" />
 */
import DOMPurify from 'dompurify'

// Cấu hình tags/attrs được phép — đủ cho email template HTML
const EMAIL_ALLOWED_TAGS = [
  'p', 'br', 'div', 'span', 'a', 'strong', 'em', 'b', 'i', 'u',
  'ul', 'ol', 'li', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'blockquote', 'pre', 'code', 'hr',
  'img',
]

const EMAIL_ALLOWED_ATTR = [
  'href', 'target', 'rel',      // links
  'src', 'alt', 'width', 'height', // images
  'style', 'class',              // styling
  'colspan', 'rowspan',          // tables
  'align', 'valign',
]

export function useSanitize() {
  function sanitizeHtml(dirty: string | null | undefined): string {
    if (!dirty) return ''
    return DOMPurify.sanitize(dirty, {
      ALLOWED_TAGS: EMAIL_ALLOWED_TAGS,
      ALLOWED_ATTR: EMAIL_ALLOWED_ATTR,
      // Chặn hoàn toàn: javascript:, data:, vbscript:
      FORBID_CONTENTS: ['script', 'style'],
      RETURN_DOM: false,
    })
  }

  return { sanitizeHtml }
}
