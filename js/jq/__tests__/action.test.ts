import * as core from '@actions/core'
import os from 'os'
import * as path from 'path'
import {run_github_action} from '../src/action'
import * as runner from '../src/runner'
import * as output from '../src/output'
import type {JqResult} from '../src/types'

// Mock dependencies
jest.mock('@actions/core')
jest.mock('os')
jest.mock('../src/runner')
jest.mock('../src/output')

const mock_core = core as jest.Mocked<typeof core>
const mock_os = os as jest.Mocked<typeof os>
const mock_runner = runner as jest.Mocked<typeof runner>
const mock_output = output as jest.Mocked<typeof output>

describe('run_github_action', () => {
  beforeEach(() => {
    jest.clearAllMocks()

    // Set default mock implementations
    mock_core.getInput.mockReturnValue('')
    mock_core.getBooleanInput.mockReturnValue(false)
    mock_core.setOutput.mockImplementation()
    mock_core.setFailed.mockImplementation()
    mock_core.debug.mockImplementation()
    mock_core.exportVariable.mockImplementation()
    mock_output.process_output.mockImplementation((output) => output)
    mock_output.write_output.mockImplementation()

    // Mock summary
    mock_core.summary = {
      addRaw: jest.fn().mockReturnValue({write: jest.fn()}),
    } as any
  })

  describe('early return on empty input', () => {
    it('should return early when input is empty string', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return ''
        return ''
      })

      await run_github_action()

      expect(mock_runner.run_jq).not.toHaveBeenCalled()
    })

    it('should return early when input is not provided', async () => {
      mock_core.getInput.mockReturnValue('')

      await run_github_action()

      expect(mock_runner.run_jq).not.toHaveBeenCalled()
    })

    it('should continue when input is provided', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"test": 1}'
        return ''
      })

      const jq_result: JqResult = {output: '1', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)

      await run_github_action()

      expect(mock_runner.run_jq).toHaveBeenCalled()
    })
  })

  describe('config building from inputs', () => {
    it('should build config with all inputs', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        const inputs: Record<string, string> = {
          input: '{"data": "value"}',
          filter: '.data',
          options: '-r',
          'input-format': 'json',
          'filter-fun': 'def custom: .',
          'output-path': '/tmp/output.txt',
          env_var: 'MY_VAR',
        }
        return inputs[name] || ''
      })

      mock_core.getBooleanInput.mockImplementation((name: string) => {
        const bool_inputs: Record<string, boolean> = {
          'use-tmp-file': true,
          'use-tmp-file-filter': true,
          decode: true,
          encode: false,
          'print-output': true,
          'print-result': false,
          'trim-result': true,
        }
        return bool_inputs[name] || false
      })

      const jq_result: JqResult = {output: '"value"', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)
      mock_output.process_output.mockReturnValue('"value"')

      await run_github_action()

      expect(mock_runner.run_jq).toHaveBeenCalledWith({
        input: '{"data": "value"}',
        filter: '.data',
        options: '-r',
        input_format: 'json',
        use_tmp_file: true,
        use_tmp_file_for_filter: true,
        filter_fun: 'def custom: .',
        decode: true,
        encode: false,
        print_output: true,
        print_result: false,
        trim_result: true,
        env_var: 'MY_VAR',
        output_path: '/tmp/output.txt',
      })
    })

    it('should handle Windows path conversion for /tmp paths', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"test": 1}'
        if (name === 'filter') return '.test'
        if (name === 'output-path') return '/tmp/output.json'
        return ''
      })

      const tmp_dir = 'C:\\Windows\\Temp'
      mock_os.tmpdir.mockReturnValue(tmp_dir)

      Object.defineProperty(process, 'platform', {
        value: 'win32',
        configurable: true,
      })

      const jq_result: JqResult = {output: '1', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)

      await run_github_action()

      const expected_path = path.join(tmp_dir, 'output.json')
      expect(mock_runner.run_jq).toHaveBeenCalledWith(
        expect.objectContaining({
          output_path: expected_path,
        }),
      )

      // Reset
      Object.defineProperty(process, 'platform', {
        value: 'linux',
        configurable: true,
      })
    })

    it('should not convert path on non-Windows platforms', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"test": 1}'
        if (name === 'filter') return '.test'
        if (name === 'output-path') return '/tmp/output.json'
        return ''
      })

      Object.defineProperty(process, 'platform', {
        value: 'linux',
        configurable: true,
      })

      const jq_result: JqResult = {output: '1', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)

      await run_github_action()

      expect(mock_runner.run_jq).toHaveBeenCalledWith(
        expect.objectContaining({
          output_path: '/tmp/output.json',
        }),
      )
    })

    it('should set filter_fun to undefined when empty', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"test": 1}'
        if (name === 'filter') return '.test'
        return ''
      })

      const jq_result: JqResult = {output: '1', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)

      await run_github_action()

      expect(mock_runner.run_jq).toHaveBeenCalledWith(
        expect.objectContaining({
          filter_fun: undefined,
        }),
      )
    })

    it('should set env_var to undefined when empty', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"test": 1}'
        if (name === 'filter') return '.test'
        return ''
      })

      const jq_result: JqResult = {output: '1', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)

      await run_github_action()

      expect(mock_runner.run_jq).toHaveBeenCalledWith(
        expect.objectContaining({
          env_var: undefined,
        }),
      )
    })

    it('should set output_path to undefined when empty', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"test": 1}'
        if (name === 'filter') return '.test'
        return ''
      })

      const jq_result: JqResult = {output: '1', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)

      await run_github_action()

      expect(mock_runner.run_jq).toHaveBeenCalledWith(
        expect.objectContaining({
          output_path: undefined,
        }),
      )
    })
  })

  describe('output handling', () => {
    it('should set output value', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"result": 42}'
        if (name === 'filter') return '.result'
        return ''
      })

      const jq_result: JqResult = {output: '42', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)
      mock_output.process_output.mockReturnValue('42')

      await run_github_action()

      expect(mock_core.setOutput).toHaveBeenCalledWith('value', '42')
    })

    it('should process output with correct options', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"data": "test"}'
        if (name === 'filter') return '.data'
        if (name === 'output-path') return '/tmp/out.txt'
        return ''
      })

      mock_core.getBooleanInput.mockImplementation((name: string) => {
        if (name === 'encode') return true
        if (name === 'print-output') return true
        if (name === 'print-result') return true
        if (name === 'trim-result') return true
        return false
      })

      const jq_result: JqResult = {output: '"test"', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)
      mock_output.process_output.mockReturnValue('dGVzdA==')

      await run_github_action()

      expect(mock_output.process_output).toHaveBeenCalledWith('"test"', {
        encode: true,
        print_output: true,
        print_result: true,
        trim_result: true,
        output_path: '/tmp/out.txt',
      })
    })

    it('should export environment variable when env_var is provided', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"value": "test"}'
        if (name === 'filter') return '.value'
        if (name === 'env_var') return 'MY_RESULT'
        return ''
      })

      const jq_result: JqResult = {output: '"test"', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)
      mock_output.process_output.mockReturnValue('"test"')

      await run_github_action()

      // exportVariable should be called with the correct value
      // Note: process.env is NOT set directly - core.exportVariable handles this
      expect(mock_core.exportVariable).toHaveBeenCalledWith('MY_RESULT', '"test"')
      expect(process.env['MY_RESULT']).toBeUndefined()
    })

    it('should not export environment variable when env_var is empty', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"value": "test"}'
        if (name === 'filter') return '.value'
        return ''
      })

      const jq_result: JqResult = {output: '"test"', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)

      await run_github_action()

      expect(mock_core.exportVariable).not.toHaveBeenCalled()
    })

    it('should print output when print_output is true', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"msg": "hello"}'
        if (name === 'filter') return '.msg'
        return ''
      })

      mock_core.getBooleanInput.mockImplementation((name: string) => {
        if (name === 'print-output') return true
        return false
      })

      const stdout_write_spy = jest.spyOn(process.stdout, 'write').mockImplementation()

      const jq_result: JqResult = {output: '"hello"', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)
      mock_output.process_output.mockReturnValue('"hello"')

      await run_github_action()

      expect(stdout_write_spy).toHaveBeenCalledWith('"hello"')
      stdout_write_spy.mockRestore()
    })

    it('should trim output when printing with trim_result true', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"msg": "hello"}'
        if (name === 'filter') return '.msg'
        return ''
      })

      mock_core.getBooleanInput.mockImplementation((name: string) => {
        if (name === 'print-output') return true
        if (name === 'trim-result') return true
        return false
      })

      const stdout_write_spy = jest.spyOn(process.stdout, 'write').mockImplementation()

      const jq_result: JqResult = {output: '  "hello"  \n', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)
      mock_output.process_output.mockReturnValue('  "hello"  \n')

      await run_github_action()

      expect(stdout_write_spy).toHaveBeenCalledWith('"hello"')
      stdout_write_spy.mockRestore()
    })

    it('should not print output when print_output is false', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"msg": "hello"}'
        if (name === 'filter') return '.msg'
        return ''
      })

      const stdout_write_spy = jest.spyOn(process.stdout, 'write').mockImplementation()

      const jq_result: JqResult = {output: '"hello"', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)

      await run_github_action()

      expect(stdout_write_spy).not.toHaveBeenCalled()
      stdout_write_spy.mockRestore()
    })

    it('should write output to file/summary', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"data": 123}'
        if (name === 'filter') return '.data'
        if (name === 'output-path') return 'GITHUB_STEP_SUMMARY'
        return ''
      })

      const jq_result: JqResult = {output: '123', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)
      mock_output.process_output.mockReturnValue('123')

      await run_github_action()

      expect(mock_output.write_output).toHaveBeenCalledWith('123', 'GITHUB_STEP_SUMMARY', mock_core.summary)
    })

    it('should write stderr when present', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"data": 1}'
        if (name === 'filter') return '.data'
        return ''
      })

      const stderr_write_spy = jest.spyOn(process.stderr, 'write').mockImplementation()

      const jq_result: JqResult = {output: '1', stderr: 'warning: deprecated syntax'}
      mock_runner.run_jq.mockResolvedValue(jq_result)

      await run_github_action()

      expect(stderr_write_spy).toHaveBeenCalledWith('stderr: warning: deprecated syntax')
      stderr_write_spy.mockRestore()
    })

    it('should not write stderr when not present', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"data": 1}'
        if (name === 'filter') return '.data'
        return ''
      })

      const stderr_write_spy = jest.spyOn(process.stderr, 'write').mockImplementation()

      const jq_result: JqResult = {output: '1', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)

      await run_github_action()

      expect(stderr_write_spy).not.toHaveBeenCalled()
      stderr_write_spy.mockRestore()
    })
  })

  describe('error handling', () => {
    it('should set failed status when run_jq throws error', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return 'invalid json'
        if (name === 'filter') return '.data'
        return ''
      })

      const jq_error = new Error('jq parse error')
      mock_runner.run_jq.mockRejectedValue(jq_error)

      const console_error_spy = jest.spyOn(console, 'error').mockImplementation()

      await run_github_action()

      expect(mock_core.setFailed).toHaveBeenCalledWith('jq failure: Error: jq parse error')
      expect(console_error_spy).toHaveBeenCalledWith('jq parse error')
      console_error_spy.mockRestore()
    })

    it('should log stderr when error has stderr property', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"data": null}'
        if (name === 'filter') return '.data.invalid'
        return ''
      })

      const jq_error = Object.assign(new Error('jq error'), {
        stderr: 'null (null) cannot be accessed',
      })
      mock_runner.run_jq.mockRejectedValue(jq_error)

      const console_error_spy = jest.spyOn(console, 'error').mockImplementation()

      await run_github_action()

      expect(console_error_spy).toHaveBeenCalledWith('jq stderr: null (null) cannot be accessed')
      expect(console_error_spy).toHaveBeenCalledWith('jq error')
      expect(mock_core.setFailed).toHaveBeenCalled()
      console_error_spy.mockRestore()
    })

    it('should handle non-Error exceptions', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"data": 1}'
        if (name === 'filter') return '.data'
        return ''
      })

      mock_runner.run_jq.mockRejectedValue('string error')

      await run_github_action()

      expect(mock_core.setFailed).toHaveBeenCalledWith('jq failure: string error')
    })

    it('should call debug with config', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"test": 1}'
        if (name === 'filter') return '.test'
        return ''
      })

      const jq_result: JqResult = {output: '1', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)

      await run_github_action()

      expect(mock_core.debug).toHaveBeenCalled()
      const debug_call = mock_core.debug.mock.calls[0][0]
      expect(debug_call).toContain('Running jq with config:')
    })
  })

  describe('integration scenarios', () => {
    it('should handle complete workflow with all options', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        const inputs: Record<string, string> = {
          input: '{"users": [{"name": "Alice", "active": true}]}',
          filter: '.users[] | select(.active) | .name',
          options: '-r',
          'input-format': 'json',
          'output-path': '/tmp/result.txt',
          env_var: 'USER_NAME',
        }
        return inputs[name] || ''
      })

      mock_core.getBooleanInput.mockImplementation((name: string) => {
        const bool_inputs: Record<string, boolean> = {
          'print-output': true,
          'trim-result': true,
        }
        return bool_inputs[name] || false
      })

      const stdout_write_spy = jest.spyOn(process.stdout, 'write').mockImplementation()

      const jq_result: JqResult = {output: 'Alice', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)
      mock_output.process_output.mockReturnValue('Alice')

      await run_github_action()

      expect(mock_runner.run_jq).toHaveBeenCalled()
      expect(mock_output.process_output).toHaveBeenCalled()
      expect(mock_core.setOutput).toHaveBeenCalledWith('value', 'Alice')
      expect(mock_core.exportVariable).toHaveBeenCalledWith('USER_NAME', 'Alice')
      expect(stdout_write_spy).toHaveBeenCalledWith('Alice')
      expect(mock_output.write_output).toHaveBeenCalled()

      stdout_write_spy.mockRestore()
    })

    it('should handle minimal configuration', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"a": 1}'
        if (name === 'filter') return '.a'
        return ''
      })

      const jq_result: JqResult = {output: '1', stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)

      await run_github_action()

      expect(mock_runner.run_jq).toHaveBeenCalled()
      expect(mock_core.setOutput).toHaveBeenCalledWith('value', '1')
    })
  })

  describe('multiline output handling', () => {
    it('should handle multiline output correctly with setOutput', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"lines": ["line1", "line2", "line3"]}'
        if (name === 'filter') return '.lines | join("\\n")'
        return ''
      })

      const multiline_output = 'line1\nline2\nline3'
      const jq_result: JqResult = {output: multiline_output, stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)
      mock_output.process_output.mockReturnValue(multiline_output)

      await run_github_action()

      // setOutput should be called with multiline string
      // @actions/core handles the EOF delimiter automatically
      expect(mock_core.setOutput).toHaveBeenCalledWith('value', multiline_output)
    })

    it('should handle multiline output with exportVariable', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"text": "Hello\\nWorld\\nTest"}'
        if (name === 'filter') return '.text'
        if (name === 'env_var') return 'MY_MULTILINE_VAR'
        return ''
      })

      const multiline_output = 'Hello\nWorld\nTest'
      const jq_result: JqResult = {output: multiline_output, stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)
      mock_output.process_output.mockReturnValue(multiline_output)

      await run_github_action()

      // exportVariable should be called with multiline string
      // @actions/core handles the EOF delimiter automatically  
      expect(mock_core.exportVariable).toHaveBeenCalledWith('MY_MULTILINE_VAR', multiline_output)
      
      // process.env should NOT be set directly as it's redundant
      // and doesn't persist across steps
      expect(process.env['MY_MULTILINE_VAR']).toBeUndefined()
    })

    it('should handle multiline output with special characters', async () => {
      mock_core.getInput.mockImplementation((name: string) => {
        if (name === 'input') return '{"data": "line1\\n\\nline3\\n"}'
        if (name === 'filter') return '.data'
        if (name === 'env_var') return 'SPECIAL_VAR'
        return ''
      })

      const multiline_output = 'line1\n\nline3\n'
      const jq_result: JqResult = {output: multiline_output, stderr: undefined}
      mock_runner.run_jq.mockResolvedValue(jq_result)
      mock_output.process_output.mockReturnValue(multiline_output)

      await run_github_action()

      expect(mock_core.setOutput).toHaveBeenCalledWith('value', multiline_output)
      expect(mock_core.exportVariable).toHaveBeenCalledWith('SPECIAL_VAR', multiline_output)
      expect(process.env['SPECIAL_VAR']).toBeUndefined()
    })
  })
})
