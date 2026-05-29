import { onUnmounted, ref } from 'vue'

import exportService, {
  type ExportJobStatusResponse,
} from '@/services/exportService'

export function useExportPolling() {
  const pollingJobId = ref<string | null>(null)
  const latestStatus = ref<ExportJobStatusResponse | null>(null)
  const isPolling = ref(false)
  let timer: number | null = null

  function stop() {
    if (timer !== null) {
      window.clearTimeout(timer)
      timer = null
    }
    isPolling.value = false
    pollingJobId.value = null
  }

  async function pollOnce(jobId: string) {
    const res = await exportService.getStatus(jobId)
    latestStatus.value = res.data
    return res.data
  }

  async function start(
    jobId: string,
    options?: {
      intervalMs?: number
      onDone?: (status: ExportJobStatusResponse) => void | Promise<void>
      onFailed?: (status: ExportJobStatusResponse) => void | Promise<void>
    },
  ) {
    stop()
    pollingJobId.value = jobId
    isPolling.value = true

    const intervalMs = options?.intervalMs ?? 2000

    const tick = async () => {
      if (!pollingJobId.value) return
      const status = await pollOnce(jobId)
      if (status.status === 'done') {
        stop()
        await options?.onDone?.(status)
        return
      }
      if (status.status === 'failed') {
        stop()
        await options?.onFailed?.(status)
        return
      }
      timer = window.setTimeout(tick, intervalMs)
    }

    await tick()
  }

  onUnmounted(() => {
    stop()
  })

  return {
    pollingJobId,
    latestStatus,
    isPolling,
    start,
    stop,
    pollOnce,
  }
}
