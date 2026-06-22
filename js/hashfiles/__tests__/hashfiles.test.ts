import * as core from '@actions/core'
import * as glob from '@actions/glob'
import nock from 'nock'
import run from '../hashfiles'

beforeEach(() => {
  jest.resetModules()
  jest.spyOn(core, 'getInput').mockImplementation((name: string): string => {
    if (name === 'token') return '12345'
    return ''
  })
  jest.spyOn(core, 'getBooleanInput').mockImplementation((): boolean => false)

  process.env['GITHUB_REPOSITORY'] = 'example/repository'
})

afterEach(() => {
  expect(nock.pendingMocks()).toEqual([])
  nock.isDone()
  nock.cleanAll()
})

describe('hashfiles action', () => {
  it('runs', async () => {
    await expect(run()).resolves.not.toThrow()
  })

  it('does not fail when no files match and failEmpty is false', async () => {
    const setFailed = jest.spyOn(core, 'setFailed').mockImplementation()
    const setOutput = jest.spyOn(core, 'setOutput').mockImplementation()
    jest.spyOn(core, 'getInput').mockImplementation((name: string): string => {
      if (name === 'files') return 'missing.file'
      if (name === 'format') return 'delimited'
      if (name === 'delimiter') return '\n'
      return ''
    })
    jest.spyOn(core, 'getBooleanInput').mockImplementation((name: string): boolean => {
      if (name === 'failEmpty') return false
      if (name === 'verbose') return false
      return false
    })
    jest.spyOn(glob, 'hashFiles').mockResolvedValue('')

    await expect(run()).resolves.not.toThrow()

    expect(setFailed).not.toHaveBeenCalled()
    expect(setOutput).toHaveBeenCalledWith('value', '')
  })

  it('fails when no files match and failEmpty is true', async () => {
    const setFailed = jest.spyOn(core, 'setFailed').mockImplementation()
    jest.spyOn(core, 'getInput').mockImplementation((name: string): string => {
      if (name === 'files') return 'missing.file'
      if (name === 'format') return 'delimited'
      if (name === 'delimiter') return '\n'
      return ''
    })
    jest.spyOn(core, 'getBooleanInput').mockImplementation((name: string): boolean => {
      if (name === 'failEmpty') return true
      if (name === 'verbose') return false
      return false
    })
    jest.spyOn(glob, 'hashFiles').mockResolvedValue('')

    await expect(run()).resolves.not.toThrow()

    expect(setFailed).toHaveBeenCalledWith('hashfiles failure: No files matched missing.file')
  })
})
