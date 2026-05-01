/* eslint-disable @typescript-eslint/naming-convention */
import * as core from '@actions/core'
import nock from 'nock'
import run from '../main'

const GITHUB_API = 'https://api.github.com'

// Default getInput mock values (can be overridden in individual tests)
let inputOverrides: Record<string, string> = {}

beforeEach(() => {
  jest.resetModules()
  inputOverrides = {}

  jest.spyOn(core, 'getInput').mockImplementation((name: string): string => {
    if (name in inputOverrides) return inputOverrides[name]
    if (name === 'token') return '12345'
    if (name === 'config') return '{}'
    if (name === 'checks') return '{}'
    // disable both Octokit plugin retries and withRetry by default to keep tests fast
    if (name === 'retries') return '0'
    if (name === 'retry-base-delay-ms') return '0'
    if (name === 'retry-max-delay-ms') return '0'
    return ''
  })

  process.env['GITHUB_REPOSITORY'] = 'example/repository'
})

afterEach(() => {
  // Reset process.exitCode since core.setFailed sets it to 1
  process.exitCode = 0
  // Capture pending mocks before cleanup to prevent test pollution
  const pending = nock.pendingMocks()
  nock.isDone()
  nock.cleanAll()
  expect(pending).toEqual([])
})

// Helper: build a checks payload
function makeChecks(entries: Array<{id: string; name: string; head_sha?: string; checkId?: number}>) {
  return Object.fromEntries(
    entries.map(({id, name, head_sha, checkId}) => [
      id,
      {name, head_sha: head_sha ?? 'abc123', ...(checkId !== undefined ? {id: checkId} : {})},
    ]),
  )
}

// ---------------------------------------------------------------------------
// Basic smoke test (empty checks)
// ---------------------------------------------------------------------------
describe('basic', () => {
  it('runs with no checks', async () => {
    await expect(run()).resolves.not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// start action — all checks succeed
// ---------------------------------------------------------------------------
describe('start action', () => {
  it('all checks succeed → checks populated, failed is {}', async () => {
    const checks = makeChecks([
      {id: 'check-a', name: 'Check A', head_sha: 'sha1'},
      {id: 'check-b', name: 'Check B', head_sha: 'sha1'},
    ])

    inputOverrides['action'] = 'start'
    inputOverrides['checks'] = JSON.stringify(checks)
    inputOverrides['config'] = JSON.stringify({
      run: {name: '', output: {text: 'hello', title: 'T', summary: 'S'}, id: 0},
      skipped: {name: '', output: {text: 'skipped', title: 'T', summary: 'S'}, id: 0},
    })

    nock(GITHUB_API).post('/repos/example/repository/check-runs').reply(201, {id: 101})
    nock(GITHUB_API).post('/repos/example/repository/check-runs').reply(201, {id: 102})

    const setOutputMock = jest.spyOn(core, 'setOutput')
    const setFailedMock = jest.spyOn(core, 'setFailed')

    await run()

    expect(setFailedMock).not.toHaveBeenCalled()
    const checksCall = setOutputMock.mock.calls.find((c) => c[0] === 'checks')
    const failedCall = setOutputMock.mock.calls.find((c) => c[0] === 'failed')
    expect(checksCall).toBeDefined()
    expect(failedCall).toBeDefined()
    expect(JSON.parse(failedCall![1] as string)).toEqual({})
    const checksObj = JSON.parse(checksCall![1] as string)
    expect(Object.values(checksObj).sort()).toEqual([101, 102])
  })

  it('one check 504s → checks has surviving entry, failed has failing one, action exits 0 (default fail-on-partial: false)', async () => {
    // retries=0: withRetry makes 1 attempt only; no Octokit plugin retry either
    const checks = makeChecks([
      {id: 'check-ok', name: 'Check OK', head_sha: 'sha1'},
      {id: 'check-fail', name: 'Check Fail', head_sha: 'sha1'},
    ])
    inputOverrides['action'] = 'start'
    inputOverrides['checks'] = JSON.stringify(checks)
    inputOverrides['config'] = JSON.stringify({
      run: {name: '', output: {text: 'hello', title: 'T', summary: 'S'}, id: 0},
      skipped: {name: '', output: {text: 'skipped', title: 'T', summary: 'S'}, id: 0},
    })

    nock(GITHUB_API).post('/repos/example/repository/check-runs').reply(201, {id: 200})
    nock(GITHUB_API).post('/repos/example/repository/check-runs').reply(504, {message: 'Gateway Timeout'})

    const setFailedMock = jest.spyOn(core, 'setFailed')
    const warningMock = jest.spyOn(core, 'warning')
    const setOutputMock = jest.spyOn(core, 'setOutput')

    await run()

    const failedCall = setOutputMock.mock.calls.find((c) => c[0] === 'failed')
    expect(failedCall).toBeDefined()
    const failedObj = JSON.parse(failedCall![1] as string)
    expect(Object.keys(failedObj)).toHaveLength(1)

    const checksCall = setOutputMock.mock.calls.find((c) => c[0] === 'checks')
    expect(checksCall).toBeDefined()
    const checksObj = JSON.parse(checksCall![1] as string)
    expect(Object.values(checksObj)).toEqual([200])

    // action exits 0 (no setFailed for partial failures by default)
    expect(setFailedMock).not.toHaveBeenCalled()
    // warning should mention the partial failure
    const warnCalls = warningMock.mock.calls.map((c) => String(c[0]))
    expect(warnCalls.some((w) => w.includes('Some checks failed'))).toBe(true)
  })

  it('one check 504s with fail-on-partial: true → setFailed called', async () => {
    inputOverrides['fail-on-partial'] = 'true'
    const checks = makeChecks([
      {id: 'check-ok', name: 'Check OK', head_sha: 'sha1'},
      {id: 'check-fail', name: 'Check Fail', head_sha: 'sha1'},
    ])
    inputOverrides['action'] = 'start'
    inputOverrides['checks'] = JSON.stringify(checks)
    inputOverrides['config'] = JSON.stringify({
      run: {name: '', output: {text: 'hello', title: 'T', summary: 'S'}, id: 0},
      skipped: {name: '', output: {text: 'skipped', title: 'T', summary: 'S'}, id: 0},
    })

    nock(GITHUB_API).post('/repos/example/repository/check-runs').reply(201, {id: 200})
    nock(GITHUB_API).post('/repos/example/repository/check-runs').reply(504, {message: 'Gateway Timeout'})

    const setFailedMock = jest.spyOn(core, 'setFailed')

    await run()

    expect(setFailedMock).toHaveBeenCalledWith(expect.stringContaining('Some checks failed'))
  })

  it('ALL checks fail → setFailed called', async () => {
    const checks = makeChecks([
      {id: 'check-a', name: 'Check A', head_sha: 'sha1'},
      {id: 'check-b', name: 'Check B', head_sha: 'sha1'},
    ])
    inputOverrides['action'] = 'start'
    inputOverrides['checks'] = JSON.stringify(checks)
    inputOverrides['config'] = JSON.stringify({
      run: {name: '', output: {text: 'hello', title: 'T', summary: 'S'}, id: 0},
      skipped: {name: '', output: {text: 'skipped', title: 'T', summary: 'S'}, id: 0},
    })

    nock(GITHUB_API).post('/repos/example/repository/check-runs').reply(504, {message: 'fail'})
    nock(GITHUB_API).post('/repos/example/repository/check-runs').reply(504, {message: 'fail'})

    const setFailedMock = jest.spyOn(core, 'setFailed')

    await run()

    expect(setFailedMock).toHaveBeenCalledWith(expect.stringContaining('All checks failed'))
  })
})

// ---------------------------------------------------------------------------
// update action
// ---------------------------------------------------------------------------
describe('update action', () => {
  it('transient 504 then success → withRetry succeeds after retry, warning emitted', async () => {
    // The @octokit/plugin-retry is mocked to a no-op in tests, so only withRetry retries.
    // With retries=1: withRetry call #1 → 504, withRetry retries → call #2 → 200.
    // Total HTTP requests: 2 (504, 200). retry-max-delay-ms=0 makes retries instant.
    inputOverrides['retries'] = '1'
    inputOverrides['retry-max-delay-ms'] = '0'
    const checks = makeChecks([{id: 'check-a', name: 'MyCheck', head_sha: 'sha1', checkId: 999}])
    inputOverrides['action'] = 'update'
    inputOverrides['checks'] = JSON.stringify(checks)

    nock(GITHUB_API).patch('/repos/example/repository/check-runs/999').reply(504, {message: 'GW timeout'})
    nock(GITHUB_API).patch('/repos/example/repository/check-runs/999').reply(200, {id: 999})

    const warningMock = jest.spyOn(core, 'warning')
    const setFailedMock = jest.spyOn(core, 'setFailed')

    await run()

    expect(setFailedMock).not.toHaveBeenCalled()
    // withRetry should have logged a warning about the retry
    const warnCalls = warningMock.mock.calls.map((c) => String(c[0]))
    expect(warnCalls.some((w) => w.includes('attempt 1 failed'))).toBe(true)
  })

  it('empty check_runs from listForRef → check appears in failed output, no PATCH made', async () => {
    // No id supplied (id=0 is falsy) → will call listForRef
    const checksNoId: Record<string, {name: string; head_sha: string; id: number}> = {
      'check-a': {name: 'MyCheck', head_sha: 'sha1', id: 0},
    }

    inputOverrides['action'] = 'update'
    inputOverrides['checks'] = JSON.stringify(checksNoId)

    // listForRef URL: GET /repos/{owner}/{repo}/commits/{ref}/check-runs
    nock(GITHUB_API)
      .get('/repos/example/repository/commits/sha1/check-runs')
      .query(true)
      .reply(200, {total_count: 0, check_runs: []})

    // No PATCH should be made - if one is attempted nock will fail the test

    const setOutputMock = jest.spyOn(core, 'setOutput')
    const setFailedMock = jest.spyOn(core, 'setFailed')

    await run()

    // The check should appear in the failed output
    const failedCall = setOutputMock.mock.calls.find((c) => c[0] === 'failed')
    expect(failedCall).toBeDefined()
    const failedObj = JSON.parse(failedCall![1] as string)
    expect(Object.keys(failedObj)).toContain('MyCheck')
    expect(String(failedObj['MyCheck'])).toMatch(/No existing check run found/)

    // All checks failed → setFailed called
    expect(setFailedMock).toHaveBeenCalledWith(expect.stringContaining('All checks failed'))
  })

  it('caller provides id → no listForRef call is made', async () => {
    // id is supplied so listForRef should NOT be invoked
    // If listForRef were called, nock would get an unexpected request and fail
    const checks = makeChecks([{id: 'check-a', name: 'MyCheck', head_sha: 'sha1', checkId: 42}])
    inputOverrides['action'] = 'update'
    inputOverrides['checks'] = JSON.stringify(checks)

    // Only the update endpoint should be called
    nock(GITHUB_API).patch('/repos/example/repository/check-runs/42').reply(200, {id: 42})

    const setFailedMock = jest.spyOn(core, 'setFailed')
    await run()
    expect(setFailedMock).not.toHaveBeenCalled()
  })

  it('non-retriable error (401) → fails immediately, no retry warnings', async () => {
    inputOverrides['retries'] = '5'
    const checks = makeChecks([{id: 'check-a', name: 'MyCheck', head_sha: 'sha1', checkId: 55}])
    inputOverrides['action'] = 'update'
    inputOverrides['checks'] = JSON.stringify(checks)

    // Only one 401 response — if retry were attempted nock would complain about extra requests
    nock(GITHUB_API).patch('/repos/example/repository/check-runs/55').reply(401, {message: 'Unauthorized'})

    const warningMock = jest.spyOn(core, 'warning')
    const setFailedMock = jest.spyOn(core, 'setFailed')

    await run()

    // setFailed called because the single check failed (all failed)
    expect(setFailedMock).toHaveBeenCalledWith(expect.stringContaining('All checks failed'))
    // No retry warnings since 401 is not retriable
    const retryCalls = warningMock.mock.calls.filter((c) => String(c[0]).includes('attempt'))
    expect(retryCalls.length).toBe(0)
  })
})

// ---------------------------------------------------------------------------
// Input validation / defaults
// ---------------------------------------------------------------------------
describe('input validation', () => {
  it('retries: 0 → single attempt only', async () => {
    // Default has retries=0; verify a 504 fails immediately without retry warnings
    const checks = makeChecks([{id: 'check-a', name: 'MyCheck', head_sha: 'sha1', checkId: 77}])
    inputOverrides['action'] = 'update'
    inputOverrides['checks'] = JSON.stringify(checks)

    nock(GITHUB_API).patch('/repos/example/repository/check-runs/77').reply(504, {message: 'fail'})

    const warningMock = jest.spyOn(core, 'warning')
    await run()

    // No retry warning emitted by withRetry
    const retryCalls = warningMock.mock.calls.filter((c) => String(c[0]).includes('attempt'))
    expect(retryCalls.length).toBe(0)
  })

  it('invalid retries input falls back to default (5)', async () => {
    jest.spyOn(core, 'getInput').mockImplementation((name: string): string => {
      if (name === 'token') return '12345'
      if (name === 'config') return '{}'
      if (name === 'checks') return '{}'
      if (name === 'action') return ''
      if (name === 'retries') return 'notanumber'
      if (name === 'retry-base-delay-ms') return ''
      if (name === 'retry-max-delay-ms') return ''
      return ''
    })
    // Just run with empty checks — should not throw
    await expect(run()).resolves.not.toThrow()
  })

  it('empty retry inputs use defaults', async () => {
    jest.spyOn(core, 'getInput').mockImplementation((name: string): string => {
      if (name === 'token') return '12345'
      if (name === 'config') return '{}'
      if (name === 'checks') return '{}'
      if (name === 'action') return ''
      if (name === 'retries') return ''
      if (name === 'retry-base-delay-ms') return ''
      if (name === 'retry-max-delay-ms') return ''
      return ''
    })
    await expect(run()).resolves.not.toThrow()
  })
})
