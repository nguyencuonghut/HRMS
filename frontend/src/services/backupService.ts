import api from './api'

export interface BackupOption {
  code: string
  label: string
  order: number
}

export interface BackupStatusOption {
  code: string
  label: string
  severity: string
  order: number
}

export interface BackupMetaResponse {
  kinds: BackupOption[]
  job_statuses: BackupStatusOption[]
  restore_statuses: BackupStatusOption[]
}

export interface BackupConfigRead {
  id: number
  kind: string
  kind_label: string
  enabled: boolean
  cron_expression: string
  retention_days: number
  source_endpoint: string | null
  source_bucket: string | null
  source_secure: boolean | null
  target_endpoint: string | null
  target_bucket: string
  target_prefix: string | null
  target_secure: boolean
  notify_emails: string[] | null
  secret_source: string
  source_configured: boolean
  target_configured: boolean
  last_validated_at: string | null
  last_validation_status: string | null
  last_validation_error: string | null
  created_at: string
  updated_at: string
}

export interface BackupConfigUpdatePayload {
  enabled: boolean
  cron_expression: string
  retention_days: number
  source_endpoint: string | null
  source_bucket: string | null
  source_secure: boolean | null
  target_endpoint: string | null
  target_bucket: string
  target_prefix: string | null
  target_secure: boolean
  notify_emails: string[] | null
}

export interface BackupValidateTargetRequest {
  kind: string
}

export interface BackupValidateTargetResponse {
  kind: string
  status: string
  message: string
  checked_at: string
  target_configured: boolean
}

export interface BackupJobCreateRequest {
  kind: string
}

export interface BackupJobSummary {
  id: number
  kind: string
  trigger: string
  status: string
  artifact_key: string | null
  artifact_bucket: string | null
  artifact_size_bytes: number | null
  object_count: number | null
  started_at: string | null
  finished_at: string | null
  error_summary: string | null
  log_excerpt: string | null
  created_at: string
}

export interface BackupSnapshotSummary {
  kind: string
  artifact_key: string
  artifact_bucket: string
  artifact_size_bytes: number | null
  object_count: number | null
  created_at: string
  finished_at: string | null
}

export interface RestoreRequestCreatePayload {
  kind: string
  mode: string
  db_artifact_key: string | null
  object_snapshot_key: string | null
  target_db_name: string | null
  target_bucket: string | null
  confirmation_text: string
  notes: string | null
}

export interface RestoreRequestSummary {
  id: number
  kind: string
  mode: string
  status: string
  db_artifact_key: string | null
  object_snapshot_key: string | null
  target_db_name: string | null
  target_bucket: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface BackupOverviewResponse {
  config_count: number
  configs: BackupConfigRead[]
  latest_jobs: BackupJobSummary[]
  latest_restore_requests: RestoreRequestSummary[]
}

const BASE = '/backups'

export default {
  getMeta() {
    return api.get<BackupMetaResponse>(`${BASE}/meta`)
  },
  getConfig() {
    return api.get<BackupConfigRead[]>(`${BASE}/config`)
  },
  getOverview() {
    return api.get<BackupOverviewResponse>(`${BASE}/overview`)
  },
  updateConfig(kind: string, payload: BackupConfigUpdatePayload) {
    return api.put<BackupConfigRead>(`${BASE}/config/${kind}`, payload)
  },
  validateTarget(payload: BackupValidateTargetRequest) {
    return api.post<BackupValidateTargetResponse>(`${BASE}/validate-target`, payload)
  },
  createJob(payload: BackupJobCreateRequest) {
    return api.post<BackupJobSummary>(`${BASE}/jobs`, payload)
  },
  getJobs(params?: { kind?: string; status?: string; limit?: number }) {
    return api.get<BackupJobSummary[]>(`${BASE}/jobs`, { params })
  },
  getSnapshots(params?: { kind?: string; limit?: number }) {
    return api.get<BackupSnapshotSummary[]>(`${BASE}/snapshots`, { params })
  },
  createRestoreRequest(payload: RestoreRequestCreatePayload) {
    return api.post<RestoreRequestSummary>(`${BASE}/restore-requests`, payload)
  },
  getRestoreRequests(params?: { kind?: string; status?: string; limit?: number }) {
    return api.get<RestoreRequestSummary[]>(`${BASE}/restore-requests`, { params })
  },
}
