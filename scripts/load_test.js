/**
 * k6 Load Test — HRMS (Plan 15.2 Hiệu năng)
 *
 * Target: 200 concurrent users, p95 < 800ms, error rate < 1%
 *
 * Chạy:
 *   docker run --rm --network host -i grafana/k6 run - < scripts/load_test.js
 *
 * Hoặc với output chi tiết:
 *   docker run --rm --network host -i grafana/k6 run --out json=load_result.json - < scripts/load_test.js
 */

import http from 'k6/http'
import { check, sleep, group } from 'k6'
import { Rate, Trend } from 'k6/metrics'

// ── Custom metrics ──────────────────────────────────────────────────────────
const errorRate = new Rate('errors')
const deptListDuration = new Trend('dept_list_duration')
const employeeListDuration = new Trend('employee_list_duration')

// ── Options ─────────────────────────────────────────────────────────────────
export const options = {
  stages: [
    { duration: '30s', target: 50  },   // ramp up → 50 users
    { duration: '1m',  target: 200 },   // ramp up → 200 users
    { duration: '3m',  target: 200 },   // steady state 200 users
    { duration: '30s', target: 0   },   // ramp down
  ],
  thresholds: {
    // SLA: 95% requests under 800ms
    http_req_duration: ['p(95)<800', 'p(99)<2000'],
    // Error rate < 1%
    http_req_failed: ['rate<0.01'],
    errors: ['rate<0.01'],
    // Cache endpoints should be faster
    dept_list_duration: ['p(95)<200'],
    employee_list_duration: ['p(95)<600'],
  },
}

const BASE = 'http://localhost:8000/api/v1'

// ── Setup: login once, share token ──────────────────────────────────────────
export function setup() {
  const res = http.post(
    `${BASE}/auth/login`,
    JSON.stringify({ email: 'admin@hrms.local', password: 'Hrms@2026' }),
    { headers: { 'Content-Type': 'application/json' } }
  )
  if (res.status !== 200) {
    console.error(`Login failed: ${res.status} ${res.body}`)
    return { token: '' }
  }
  return { token: res.json('access_token') }
}

// ── Main test scenario ───────────────────────────────────────────────────────
export default function (data) {
  const headers = {
    Authorization: `Bearer ${data.token}`,
    'Content-Type': 'application/json',
  }

  // Mix of typical HR operations
  const scenario = Math.random()

  if (scenario < 0.30) {
    // 30%: Read-heavy — departments (should be cache-hit after first requests)
    group('departments', () => {
      const start = Date.now()
      const r = http.get(`${BASE}/departments`, { headers })
      deptListDuration.add(Date.now() - start)
      const ok = check(r, {
        'departments 200': res => res.status === 200,
        'departments has data': res => res.json('length') > 0 || Array.isArray(res.json()),
      })
      errorRate.add(!ok)
    })
  } else if (scenario < 0.60) {
    // 30%: Employee list (paginated, DB query)
    group('employees', () => {
      const start = Date.now()
      const r = http.get(`${BASE}/employees?page=1&page_size=20`, { headers })
      employeeListDuration.add(Date.now() - start)
      const ok = check(r, { 'employees 200': res => res.status === 200 })
      errorRate.add(!ok)
    })
  } else if (scenario < 0.75) {
    // 15%: Job titles (cache-eligible)
    group('job_titles', () => {
      const r = http.get(`${BASE}/job-titles`, { headers })
      const ok = check(r, { 'job_titles 200': res => res.status === 200 })
      errorRate.add(!ok)
    })
  } else if (scenario < 0.85) {
    // 10%: Leave types lookup (cache-eligible)
    group('leave_types', () => {
      const r = http.get(`${BASE}/leave-types?page=1&page_size=50`, { headers })
      const ok = check(r, { 'leave_types 200': res => res.status === 200 })
      errorRate.add(!ok)
    })
  } else if (scenario < 0.92) {
    // 7%: Dashboard summary
    group('dashboard', () => {
      const year = new Date().getFullYear()
      const r = http.get(`${BASE}/reports/dashboard/summary?year=${year}`, { headers })
      const ok = check(r, { 'dashboard 200': res => res.status === 200 })
      errorRate.add(!ok)
    })
  } else {
    // 8%: Health check (baseline)
    group('health', () => {
      const r = http.get(`${BASE.replace('/api/v1', '')}/health`)
      const ok = check(r, {
        'health 200': res => res.status === 200,
        'health ok': res => res.json('status') === 'ok',
      })
      errorRate.add(!ok)
    })
  }

  // Think time: 0.5–2 seconds between requests (realistic user behavior)
  sleep(0.5 + Math.random() * 1.5)
}

// ── Teardown: print summary ──────────────────────────────────────────────────
export function teardown(data) {
  console.log('Load test complete. Check thresholds above for SLA compliance.')
}
