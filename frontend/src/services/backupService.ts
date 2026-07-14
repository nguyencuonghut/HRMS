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
  backup_set_id: number | null
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

export interface BackupSetSummary {
  id: number
  trigger: string
  status: string
  db_job_id: number | null
  object_job_id: number | null
  db_artifact_key: string | null
  object_snapshot_key: string | null
  artifact_bucket: string | null
  started_at: string | null
  finished_at: string | null
  error_summary: string | null
  created_at: string
  updated_at: string
}

export interface RestoreRequestCreatePayload {
  kind: string
  mode: string
  backup_set_id: number | null
  db_artifact_key: string | null
  object_snapshot_key: string | null
  target_db_name: string | null
  target_bucket: string | null
  confirmation_text: string
  notes: string | null
}

export interface RestoreRequestSummary {
  id: number
  backup_set_id: number | null
  kind: string
  mode: string
  status: string
  db_artifact_key: string | null
  object_snapshot_key: string | null
  target_db_name: string | null
  target_bucket: string | null
  requested_by_id: number | null
  approved_by_id: number | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface BackupOverviewResponse {
  config_count: number
  configs: BackupConfigRead[]
  latest_jobs: BackupJobSummary[]
  latest_backup_sets: BackupSetSummary[]
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
  createBackupSet() {
    return api.post<BackupSetSummary>(`${BASE}/sets`)
  },
  getJobs(params?: { kind?: string; status?: string; limit?: number }) {
    return api.get<BackupJobSummary[]>(`${BASE}/jobs`, { params })
  },
  getBackupSets(params?: { status?: string; limit?: number }) {
    return api.get<BackupSetSummary[]>(`${BASE}/sets`, { params })
  },
  getSnapshots(params?: { kind?: string; limit?: number }) {
    return api.get<BackupSnapshotSummary[]>(`${BASE}/snapshots`, { params })
  },
  createRestoreRequest(payload: RestoreRequestCreatePayload) {
    return api.post<RestoreRequestSummary>(`${BASE}/restore-requests`, payload)
  },
  approveRestoreRequest(id: number) {
    return api.post<RestoreRequestSummary>(`${BASE}/restore-requests/${id}/approve`)
  },
  retryRestoreRequest(id: number) {
    return api.post<RestoreRequestSummary>(`${BASE}/restore-requests/${id}/retry`)
  },
  cancelRestoreRequest(id: number) {
    return api.post<RestoreRequestSummary>(`${BASE}/restore-requests/${id}/cancel`)
  },
  getRestoreRequests(params?: { kind?: string; status?: string; limit?: number }) {
    return api.get<RestoreRequestSummary[]>(`${BASE}/restore-requests`, { params })
  },
}
