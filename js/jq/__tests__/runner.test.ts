import fs from 'fs'
import os from 'os'
import {exec} from 'child_process'
import tmp from 'tmp'
import {run_jq} from '../src/runner'
import * as input from '../src/input'
import * as filter from '../src/filter'
import type {JqConfig, TempFileHandles} from '../src/types'

// Mock dependencies
jest.mock('fs')
jest.mock('os')
jest.mock('child_process')
jest.mock('tmp')
jest.mock('../src/input')
jest.mock('../src/filter')

const mock_fs = fs as jest.Mocked<typeof fs>
const mock_os = os as jest.Mocked<typeof os>
const mock_exec = exec as jest.MockedFunction<typeof exec>
const mock_tmp = tmp as jest.Mocked<typeof tmp>
const mock_input = input as jest.Mocked<typeof input>
const mock_filter = filter as jest.Mocked<typeof filter>

describe('run_jq', () => {
  beforeEach(() => {
    jest.clearAllMocks()

    // Set default mock implementations
    mock_input.process_input.mockImplementation((input) => input)
    mock_filter.cleanup_temp_files.mockImplementation()
  })

  describe('successful execution', () => {
    it('should execute jq and return output', async () => {
      const config: JqConfig = {
        input: '{"name": "test"}',
        filter: '.name',
        options: '-r',
        input_format: 'json',
        use_tmp_file: false,
        use_tmp_file_for_filter: false,
        decode: false,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      const temp_handles: TempFileHandles = {}
      mock_filter.build_filter.mockReturnValue({
        filter_arg: "'.name'",
        filter_fun_arg: '-L /path/to/jq',
        temp_handles: temp_handles,
      })

      mock_os.platform.mockReturnValue('linux')

      mock_exec.mockImplementation(((_command: string, callback: any) => {
        callback(null, 'test', '')
        return {on: jest.fn()} as any
      }) as any)

      const result = await run_jq(config)

      expect(mock_input.process_input).toHaveBeenCalledWith('{"name": "test"}', 'json', false)
      expect(mock_filter.build_filter).toHaveBeenCalledWith('.name', undefined, false)
      expect(mock_filter.cleanup_temp_files).toHaveBeenCalledWith(temp_handles)
      expect(result.output).toBe('test')
      expect(result.stderr).toBeUndefined()
    })

    it('should return stderr when present', async () => {
      const config: JqConfig = {
        input: '{"data": 123}',
        filter: '.data',
        options: '',
        input_format: 'json',
        use_tmp_file: false,
        use_tmp_file_for_filter: false,
        decode: false,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      mock_filter.build_filter.mockReturnValue({
        filter_arg: "'.data'",
        filter_fun_arg: '-L /path/to/jq',
        temp_handles: {},
      })

      mock_os.platform.mockReturnValue('linux')

      mock_exec.mockImplementation(((_command: string, callback: any) => {
        callback(null, '123', 'warning: something')
        return {on: jest.fn()} as any
      }) as any)

      const result = await run_jq(config)

      expect(result.output).toBe('123')
      expect(result.stderr).toBe('warning: something')
    })

    it('should use processed input from process_input', async () => {
      const config: JqConfig = {
        input: 'base64encodedstring',
        filter: '.value',
        options: '',
        input_format: 'json',
        use_tmp_file: false,
        use_tmp_file_for_filter: false,
        decode: true,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      const processed_input = '{"value": 42}'
      mock_input.process_input.mockReturnValue(processed_input)

      mock_filter.build_filter.mockReturnValue({
        filter_arg: "'.value'",
        filter_fun_arg: '-L /path/to/jq',
        temp_handles: {},
      })

      mock_os.platform.mockReturnValue('linux')

      mock_exec.mockImplementation(((command: string, callback: any) => {
        // Verify the processed input is used in the command
        expect(command).toContain(processed_input)
        callback(null, '42', '')
        return {on: jest.fn()} as any
      }) as any)

      await run_jq(config)

      expect(mock_input.process_input).toHaveBeenCalledWith('base64encodedstring', 'json', true)
    })
  })

  describe('command building', () => {
    it('should build command with printf on non-Windows platforms', async () => {
      const config: JqConfig = {
        input: '{"test": "value"}',
        filter: '.test',
        options: '-r',
        input_format: 'json',
        use_tmp_file: false,
        use_tmp_file_for_filter: false,
        decode: false,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      mock_filter.build_filter.mockReturnValue({
        filter_arg: "'.test'",
        filter_fun_arg: '-L /path/to/jq',
        temp_handles: {},
      })

      mock_os.platform.mockReturnValue('linux')

      mock_exec.mockImplementation(((command: string, callback: any) => {
        expect(command).toBe("printf '%s' '{\"test\": \"value\"}' | jq -r -L /path/to/jq '.test'")
        callback(null, 'value', '')
        return {on: jest.fn()} as any
      }) as any)

      await run_jq(config)
    })

    it('should build command with temp file on Windows', async () => {
      const config: JqConfig = {
        input: '{"data": "test"}',
        filter: '.data',
        options: '',
        input_format: 'json',
        use_tmp_file: false,
        use_tmp_file_for_filter: false,
        decode: false,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      const tmp_file_name = 'C:\\Temp\\tmp-123'
      const mock_tmp_file = {
        name: tmp_file_name,
        removeCallback: jest.fn(),
      }

      mock_filter.build_filter.mockReturnValue({
        filter_arg: "'.data'",
        filter_fun_arg: '-L C:\\jq',
        temp_handles: {},
      })

      mock_os.platform.mockReturnValue('win32')
      mock_tmp.fileSync.mockReturnValue(mock_tmp_file as any)
      mock_fs.writeFileSync.mockImplementation()

      mock_exec.mockImplementation(((command: string, callback: any) => {
        expect(command).toBe(`cat ${tmp_file_name} | jq  -L C:\\jq '.data'`)
        callback(null, 'test', '')
        return {on: jest.fn()} as any
      }) as any)

      await run_jq(config)

      expect(mock_tmp.fileSync).toHaveBeenCalled()
      expect(mock_fs.writeFileSync).toHaveBeenCalledWith(tmp_file_name, '{"data": "test"}')
    })

    it('should build command with temp file when use_tmp_file is true', async () => {
      const config: JqConfig = {
        input: '{"value": 100}',
        filter: '.value',
        options: '-r',
        input_format: 'json',
        use_tmp_file: true,
        use_tmp_file_for_filter: false,
        decode: false,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      const tmp_file_name = '/tmp/input-456'
      const mock_tmp_file = {
        name: tmp_file_name,
        removeCallback: jest.fn(),
      }

      mock_filter.build_filter.mockReturnValue({
        filter_arg: "'.value'",
        filter_fun_arg: '-L /path/to/jq',
        temp_handles: {},
      })

      mock_os.platform.mockReturnValue('linux')
      mock_tmp.fileSync.mockReturnValue(mock_tmp_file as any)
      mock_fs.writeFileSync.mockImplementation()

      mock_exec.mockImplementation(((command: string, callback: any) => {
        expect(command).toBe(`cat ${tmp_file_name} | jq -r -L /path/to/jq '.value'`)
        callback(null, '100', '')
        return {on: jest.fn()} as any
      }) as any)

      await run_jq(config)

      expect(mock_tmp.fileSync).toHaveBeenCalled()
      expect(mock_fs.writeFileSync).toHaveBeenCalledWith(tmp_file_name, '{"value": 100}')
    })

    it('should include filter_fun and filter args in command', async () => {
      const config: JqConfig = {
        input: '{"x": 1}',
        filter: 'fun::custom',
        filter_fun: 'def custom: .x * 2',
        options: '',
        input_format: 'json',
        use_tmp_file: false,
        use_tmp_file_for_filter: false,
        decode: false,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      mock_filter.build_filter.mockReturnValue({
        filter_arg: "'-f /tmp/filter.jq'",
        filter_fun_arg: '-L /tmp/fun-dir',
        temp_handles: {},
      })

      mock_os.platform.mockReturnValue('linux')

      mock_exec.mockImplementation(((command: string, callback: any) => {
        expect(command).toContain('-L /tmp/fun-dir')
        expect(command).toContain("'-f /tmp/filter.jq'")
        callback(null, '2', '')
        return {on: jest.fn()} as any
      }) as any)

      await run_jq(config)
    })
  })

  describe('error handling', () => {
    it('should reject when exec returns error', async () => {
      const config: JqConfig = {
        input: 'invalid json',
        filter: '.data',
        options: '',
        input_format: 'json',
        use_tmp_file: false,
        use_tmp_file_for_filter: false,
        decode: false,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      mock_filter.build_filter.mockReturnValue({
        filter_arg: "'.data'",
        filter_fun_arg: '-L /path/to/jq',
        temp_handles: {},
      })

      mock_os.platform.mockReturnValue('linux')

      const exec_error = new Error('jq parse error')
      mock_exec.mockImplementation(((_command: string, callback: any) => {
        callback(exec_error, '', 'parse error: Invalid numeric literal')
        return {on: jest.fn()} as any
      }) as any)

      await expect(run_jq(config)).rejects.toThrow('jq parse error')

      expect(mock_filter.cleanup_temp_files).toHaveBeenCalled()
    })

    it('should reject when process exits with non-zero code before callback', async () => {
      const config: JqConfig = {
        input: '{"data": null}',
        filter: '.data.nested',
        options: '',
        input_format: 'json',
        use_tmp_file: false,
        use_tmp_file_for_filter: false,
        decode: false,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      mock_filter.build_filter.mockReturnValue({
        filter_arg: "'.data.nested'",
        filter_fun_arg: '-L /path/to/jq',
        temp_handles: {},
      })

      mock_os.platform.mockReturnValue('linux')

      mock_exec.mockImplementation(((_command: string, callback: any) => {
        const mock_proc = {
          on: jest.fn((event, cb) => {
            if (event === 'exit') {
              setTimeout(() => cb(1), 0)
            }
          }),
        }
        setTimeout(() => callback(null, '', 'error'), 10)
        return mock_proc as any
      }) as any)

      await expect(run_jq(config)).rejects.toThrow('Child process exited with code 1')
    })

    it('should cleanup temp files even when error occurs', async () => {
      const config: JqConfig = {
        input: '{"test": 1}',
        filter: '.invalid',
        options: '',
        input_format: 'json',
        use_tmp_file: false,
        use_tmp_file_for_filter: false,
        decode: false,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      const temp_handles: TempFileHandles = {
        tmp_file: {name: '/tmp/test', removeCallback: jest.fn()} as any,
      }

      mock_filter.build_filter.mockReturnValue({
        filter_arg: "'.invalid'",
        filter_fun_arg: '-L /path/to/jq',
        temp_handles: temp_handles,
      })

      mock_os.platform.mockReturnValue('linux')

      mock_exec.mockImplementation(((_command: string, callback: any) => {
        callback(new Error('jq error'), '', 'error')
        return {on: jest.fn()} as any
      }) as any)

      await expect(run_jq(config)).rejects.toThrow()

      expect(mock_filter.cleanup_temp_files).toHaveBeenCalledWith(temp_handles)
    })

    it('should reject when process_input throws error', async () => {
      const config: JqConfig = {
        input: '/nonexistent/file.json',
        filter: '.data',
        options: '',
        input_format: 'json-path',
        use_tmp_file: false,
        use_tmp_file_for_filter: false,
        decode: false,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      mock_input.process_input.mockImplementation(() => {
        throw new Error('File not found')
      })

      mock_filter.build_filter.mockReturnValue({
        filter_arg: "'.data'",
        filter_fun_arg: '-L /path/to/jq',
        temp_handles: {},
      })

      await expect(run_jq(config)).rejects.toThrow('File not found')
    })

    it('should reject when build_filter throws error', async () => {
      const config: JqConfig = {
        input: '{"data": 1}',
        filter: '.data',
        options: '',
        input_format: 'json',
        use_tmp_file: false,
        use_tmp_file_for_filter: false,
        decode: false,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      mock_filter.build_filter.mockImplementation(() => {
        throw new Error('Failed to create temp file')
      })

      await expect(run_jq(config)).rejects.toThrow('Failed to create temp file')
    })
  })

  describe('integration with filter and input modules', () => {
    it('should pass correct parameters to build_filter', async () => {
      const config: JqConfig = {
        input: '{"test": 1}',
        filter: '.test',
        filter_fun: 'def custom: . * 2',
        options: '',
        input_format: 'json',
        use_tmp_file: false,
        use_tmp_file_for_filter: true,
        decode: false,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      mock_filter.build_filter.mockReturnValue({
        filter_arg: "'-f /tmp/filter'",
        filter_fun_arg: '-L /tmp/fun',
        temp_handles: {},
      })

      mock_os.platform.mockReturnValue('linux')

      mock_exec.mockImplementation(((_command: string, callback: any) => {
        callback(null, '2', '')
        return {on: jest.fn()} as any
      }) as any)

      await run_jq(config)

      expect(mock_filter.build_filter).toHaveBeenCalledWith('.test', 'def custom: . * 2', true)
    })

    it('should pass correct parameters to process_input', async () => {
      const config: JqConfig = {
        input: 'base64string',
        filter: '.data',
        options: '',
        input_format: 'yaml',
        use_tmp_file: false,
        use_tmp_file_for_filter: false,
        decode: true,
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      mock_input.process_input.mockReturnValue('{"data": "value"}')

      mock_filter.build_filter.mockReturnValue({
        filter_arg: "'.data'",
        filter_fun_arg: '-L /path/to/jq',
        temp_handles: {},
      })

      mock_os.platform.mockReturnValue('linux')

      mock_exec.mockImplementation(((_command: string, callback: any) => {
        callback(null, '"value"', '')
        return {on: jest.fn()} as any
      }) as any)

      await run_jq(config)

      expect(mock_input.process_input).toHaveBeenCalledWith('base64string', 'yaml', true)
    })
  })
})
