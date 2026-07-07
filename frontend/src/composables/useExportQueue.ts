import { ref, onBeforeUnmount } from 'vue'
import { useToast } from 'primevue/usetoast'
import exportService, { ExportReportType, ExportFormat } from '@/services/exportService'

export function useExportQueue() {
  const toast = useToast()
  const isExporting = ref(false)
  const exportProgress = ref(0)
  const showExportDialog = ref(false)
  const currentJobId = ref<string | null>(null)
  let pollInterval: number | null = null

  function cleanup() {
    if (pollInterval !== null) {
      window.clearInterval(pollInterval)
      pollInterval = null
    }
  }

  onBeforeUnmount(cleanup)

  async function startExport(
    reportType: ExportReportType,
    filters: Record<string, unknown> = {},
    filename?: string | null,
    format: ExportFormat = 'xlsx'
  ) {
    cleanup()
    isExporting.value = true
    exportProgress.value = 0
    currentJobId.value = null

    // Remove null/undefined/empty string parameters from filters
    const cleanedFilters = Object.fromEntries(
      Object.entries(filters).filter(
        ([, value]) => value !== null && value !== undefined && value !== ''
      )
    )

    try {
      const res = await exportService.createJob({
        report_type: reportType,
        format,
        filters: cleanedFilters,
        filename: filename || null,
      })

      const job = res.data
      currentJobId.value = job.id

      if (job.status === 'done') {
        await exportService.downloadJob(job.id, job.filename || filename || 'download.xlsx')
        toast.add({
          severity: 'success',
          summary: 'Thành công',
          detail: 'Tải file thành công',
          life: 3000,
        })
        isExporting.value = false
        return
      }

      // If async, open dialog and start polling
      showExportDialog.value = true
      pollInterval = window.setInterval(async () => {
        try {
          const statusRes = await exportService.getStatus(job.id)
          const currentJob = statusRes.data

          if (currentJob.status === 'done') {
            cleanup()
            await exportService.downloadJob(job.id, currentJob.filename || filename || 'download.xlsx')
            toast.add({
              severity: 'success',
              summary: 'Thành công',
              detail: 'Xuất file thành công',
              life: 3000,
            })
            showExportDialog.value = false
            isExporting.value = false
          } else if (currentJob.status === 'failed') {
            cleanup()
            toast.add({
              severity: 'error',
              summary: 'Lỗi xuất file',
              detail: currentJob.error_message || 'Quá trình xuất file thất bại',
              life: 4000,
            })
            showExportDialog.value = false
            isExporting.value = false
          } else {
            exportProgress.value = currentJob.progress_pct || 0
          }
        } catch (err) {
          cleanup()
          toast.add({
            severity: 'error',
            summary: 'Lỗi',
            detail: 'Không thể kết nối đến máy chủ để kiểm tra tiến trình',
            life: 4000,
          })
          showExportDialog.value = false
          isExporting.value = false
        }
      }, 2000)

    } catch (err: any) {
      cleanup()
      const apiErr = err?.response?.data?.detail || 'Không thể tạo tiến trình xuất báo cáo'
      toast.add({
        severity: 'error',
        summary: 'Lỗi export',
        detail: apiErr,
        life: 4000,
      })
      isExporting.value = false
    }
  }

  async function cancelExport() {
    cleanup()
    if (currentJobId.value) {
      try {
        await exportService.deleteJob(currentJobId.value)
      } catch (err) {
        console.error('Failed to delete job on cancel:', err)
      }
    }
    showExportDialog.value = false
    isExporting.value = false
  }

  return {
    isExporting,
    exportProgress,
    showExportDialog,
    startExport,
    cancelExport,
  }
}
