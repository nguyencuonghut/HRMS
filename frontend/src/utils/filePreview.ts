const IMAGE_MIME_PREFIX = 'image/'
const PDF_MIME = 'application/pdf'
const PREVIEWABLE_EXTENSIONS = new Set([
  '.pdf',
  '.png',
  '.jpg',
  '.jpeg',
  '.gif',
  '.webp',
  '.bmp',
  '.svg',
])

export function isPreviewableFile(mimeType?: string | null, fileName?: string | null): boolean {
  const normalizedMime = (mimeType ?? '').trim().toLowerCase()
  if (normalizedMime === PDF_MIME || normalizedMime.startsWith(IMAGE_MIME_PREFIX)) {
    return true
  }

  const normalizedName = (fileName ?? '').trim().toLowerCase()
  for (const ext of PREVIEWABLE_EXTENSIONS) {
    if (normalizedName.endsWith(ext)) {
      return true
    }
  }
  return false
}

