import fs from 'fs'
import {exec} from 'child_process'
import tmp from 'tmp'
import {process_output, write_output, type OutputOptions} from '../src/output'

// Mock dependencies
jest.mock('fs')
jest.mock('child_process')
jest.mock('tmp')

const mock_fs = fs as jest.Mocked<typeof fs>
const mock_exec = exec as jest.MockedFunction<typeof exec>
const mock_tmp = tmp as jest.Mocked<typeof tmp>

describe('process_output', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('trim_result option', () => {
    it('should trim output when trim_result is true', () => {
      const output = '  result with spaces  \n'
      const options: OutputOptions = {
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: true,
      }

      const result = process_output(output, options)

      expect(result).toBe('result with spaces')
    })

    it('should not trim output when trim_result is false', () => {
      const output = '  result with spaces  \n'
      const options: OutputOptions = {
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      const result = process_output(output, options)

      expect(result).toBe(output)
    })
  })

  describe('encode option', () => {
    it('should encode output to base64 when encode is true', () => {
      const output = 'Hello World'
      const options: OutputOptions = {
        encode: true,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      const result = process_output(output, options)

      // Decode to verify
      const decoded = Buffer.from(result, 'base64').toString('utf-8')
      expect(decoded).toBe(output)
    })

    it('should encode UTF-8 output correctly', () => {
      const output = '{"key": "value with émojis 🎉"}'
      const options: OutputOptions = {
        encode: true,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      const result = process_output(output, options)

      // Decode to verify
      const decoded = Buffer.from(result, 'base64').toString('utf-8')
      expect(decoded).toBe(output)
    })

    it('should not encode when encode is false', () => {
      const output = 'Hello World'
      const options: OutputOptions = {
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      const result = process_output(output, options)

      expect(result).toBe(output)
    })
  })

  describe('print_result option', () => {
    it('should create temp file and execute jq command when print_result is true', () => {
      const output = '{"key": "value"}'
      const tmp_file_name = '/tmp/test-file-123'
      const mock_tmp_file = {
        name: tmp_file_name,
        removeCallback: jest.fn(),
      }

      mock_tmp.fileSync.mockReturnValue(mock_tmp_file as any)
      mock_fs.writeFileSync.mockImplementation()

      // Mock exec to capture command
      mock_exec.mockImplementation(((command: string, callback: any) => {
        // Verify command format
        expect(command).toBe(`cat ${tmp_file_name} | jq -C '.'`)
        // Call callback with result
        callback(null, '{\n  "key": "value"\n}', '')
        return {} as any
      }) as any)

      const options: OutputOptions = {
        encode: false,
        print_output: false,
        print_result: true,
        trim_result: false,
      }

      const result = process_output(output, options)

      expect(mock_tmp.fileSync).toHaveBeenCalled()
      expect(mock_fs.writeFileSync).toHaveBeenCalledWith(tmp_file_name, output)
      expect(mock_exec).toHaveBeenCalled()
      expect(result).toBe(output)
    })

    it('should trim printed result when trim_result is true', () => {
      const output = '  {"key": "value"}  \n'
      const tmp_file_name = '/tmp/test-file-123'
      const mock_tmp_file = {
        name: tmp_file_name,
        removeCallback: jest.fn(),
      }

      mock_tmp.fileSync.mockReturnValue(mock_tmp_file as any)
      mock_fs.writeFileSync.mockImplementation()

      // Mock stdout.write to capture output
      const stdout_write_spy = jest.spyOn(process.stdout, 'write').mockImplementation()

      mock_exec.mockImplementation(((_command: string, callback: any) => {
        callback(null, '{\n  "key": "value"\n}', '')
        return {} as any
      }) as any)

      const options: OutputOptions = {
        encode: false,
        print_output: false,
        print_result: true,
        trim_result: true,
      }

      const result = process_output(output, options)

      expect(result).toBe('{"key": "value"}')
      stdout_write_spy.mockRestore()
    })

    it('should not execute jq command when print_result is false', () => {
      const output = '{"key": "value"}'
      const options: OutputOptions = {
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      const result = process_output(output, options)

      expect(mock_tmp.fileSync).not.toHaveBeenCalled()
      expect(mock_exec).not.toHaveBeenCalled()
      expect(result).toBe(output)
    })
  })

  describe('combined options', () => {
    it('should trim and encode output', () => {
      const output = '  result  \n'
      const options: OutputOptions = {
        encode: true,
        print_output: false,
        print_result: false,
        trim_result: true,
      }

      const result = process_output(output, options)

      const decoded = Buffer.from(result, 'base64').toString('utf-8')
      expect(decoded).toBe('result')
    })

    it('should handle all options disabled', () => {
      const output = '{"key": "value"}'
      const options: OutputOptions = {
        encode: false,
        print_output: false,
        print_result: false,
        trim_result: false,
      }

      const result = process_output(output, options)

      expect(result).toBe(output)
    })
  })
})

describe('write_output', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('no output path', () => {
    it('should not write anything when output_path is undefined', () => {
      const output = '{"key": "value"}'

      write_output(output, undefined)

      expect(mock_fs.writeFileSync).not.toHaveBeenCalled()
    })
  })

  describe('file output path', () => {
    it('should write to file when output_path is a file path', () => {
      const output = '{"key": "value"}'
      const output_path = '/path/to/output.json'

      write_output(output, output_path)

      expect(mock_fs.writeFileSync).toHaveBeenCalledWith(output_path, output)
    })

    it('should write to relative file path', () => {
      const output = 'result'
      const output_path = 'output.txt'

      write_output(output, output_path)

      expect(mock_fs.writeFileSync).toHaveBeenCalledWith(output_path, output)
    })
  })

  describe('GITHUB_STEP_SUMMARY', () => {
    it('should use summary writer when output_path is GITHUB_STEP_SUMMARY', () => {
      const output = '# Test Summary\nResults here'
      const output_path = 'GITHUB_STEP_SUMMARY'
      const mock_summary_writer = {
        addRaw: jest.fn().mockReturnValue({
          write: jest.fn(),
        }),
      }

      write_output(output, output_path, mock_summary_writer)

      expect(mock_summary_writer.addRaw).toHaveBeenCalledWith(output)
      expect(mock_summary_writer.addRaw(output).write).toHaveBeenCalled()
      expect(mock_fs.writeFileSync).not.toHaveBeenCalled()
    })

    it('should not fail when summary writer is undefined for GITHUB_STEP_SUMMARY', () => {
      const output = '# Test Summary'
      const output_path = 'GITHUB_STEP_SUMMARY'

      expect(() => write_output(output, output_path, undefined)).not.toThrow()

      expect(mock_fs.writeFileSync).not.toHaveBeenCalled()
    })
  })

  describe('edge cases', () => {
    it('should handle empty output string', () => {
      const output = ''
      const output_path = '/path/to/output.txt'

      write_output(output, output_path)

      expect(mock_fs.writeFileSync).toHaveBeenCalledWith(output_path, output)
    })

    it('should handle multi-line output', () => {
      const output = 'line1\nline2\nline3'
      const output_path = '/path/to/output.txt'

      write_output(output, output_path)

      expect(mock_fs.writeFileSync).toHaveBeenCalledWith(output_path, output)
    })
  })
})
