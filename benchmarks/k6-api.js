// k6 load test for hrms-backend. Run: k6 run -e BASE=http://127.0.0.1:8000 -e EMAIL=... -e PASSWORD=... benchmarks/k6-api.js
import http from 'k6/http';
import { check } from 'k6';

const BASE = __ENV.BASE || 'http://127.0.0.1:8000';
export const options = {
  summaryTrendStats: ['min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max', 'avg'],
  scenarios: {
    list_employees: { executor: 'constant-vus', vus: 50, duration: '30s', exec: 'listEmployees' },
    me:             { executor: 'constant-vus', vus: 50, duration: '30s', exec: 'me', startTime: '35s' },
    login:          { executor: 'constant-vus', vus: 20, duration: '20s', exec: 'login', startTime: '70s' },
  },
  thresholds: {
    'http_req_failed': ['rate<0.01'],
    // per-endpoint breakdown (limits are deliberately loose; they exist so k6 reports each endpoint separately)
    'http_req_duration{name:GET /employees}': ['p(95)<60000'],
    'http_req_duration{name:GET /auth/me}': ['p(95)<60000'],
    'http_req_duration{name:POST /auth/login}': ['p(95)<60000'],
    'http_reqs{name:GET /employees}': ['count>0'],
    'http_reqs{name:GET /auth/me}': ['count>0'],
    'http_reqs{name:POST /auth/login}': ['count>0'],
    'http_req_failed{name:GET /employees}': ['rate<1'],
    'http_req_failed{name:GET /auth/me}': ['rate<1'],
    'http_req_failed{name:POST /auth/login}': ['rate<1'],
  },
};

function auth(token) { return { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } }; }
function doLogin() {
  return http.post(`${BASE}/api/v1/auth/login`, JSON.stringify({ email: __ENV.EMAIL, password: __ENV.PASSWORD }),
    { headers: { 'Content-Type': 'application/json' }, tags: { name: 'POST /auth/login' } });
}

export function setup() {
  const r = doLogin();
  const token = r.json('data.access_token');
  // seed 200 employees so the list endpoint returns real rows (idempotent-ish: codes are unique per run)
  const run = Date.now();
  for (let i = 0; i < 200; i++) {
    http.post(`${BASE}/api/v1/employees`, JSON.stringify({
      employee_code: `B${run}-${i}`, first_name: `First${i}`, last_name: `Last${i}`,
      email: `e${run}-${i}@example.com`, joining_date: '2024-01-15', designation: 'Engineer',
    }), auth(token));
  }
  return { token };
}

export function listEmployees(d) {
  const r = http.get(`${BASE}/api/v1/employees?page=1&page_size=20`, Object.assign(auth(d.token), { tags: { name: 'GET /employees' } }));
  check(r, { 'list 200': (x) => x.status === 200 });
}
export function me(d) {
  const r = http.get(`${BASE}/api/v1/auth/me`, Object.assign(auth(d.token), { tags: { name: 'GET /auth/me' } }));
  check(r, { 'me 200': (x) => x.status === 200 });
}
export function login() {
  const r = doLogin();
  check(r, { 'login 200': (x) => x.status === 200 });
}
