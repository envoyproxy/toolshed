import fs from 'fs'
import os from 'os'
import * as path from 'path'
import {process_input} from '../src/input'

jest.mock('fs')
jest.mock('os')
jest.mock('js-yaml', () => ({
  load: jest.fn(),
}))

const mock_fs = fs as jest.Mocked<typeof fs>
const mock_os = os as jest.Mocked<typeof os>

describe('process_input', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('plain input without path or decode', () => {
    it('should return input unchanged for plain format without decode', () => {
      const input = '{"key": "value"}'
      const result = process_input(input, 'json', false)
      expect(result).toBe(input)
    })

    it('should return input unchanged for empty format without decode', () => {
      const input = 'plain text'
      const result = process_input(input, '', false)
      expect(result).toBe(input)
    })
  })

  describe('input from file path', () => {
    it('should read file content for json-path format', () => {
      const input = '/path/to/file.json'
      const file_content = '{"key": "value"}'
      mock_fs.readFileSync.mockReturnValue(file_content)

      const result = process_input(input, 'json-path', false)

      expect(mock_fs.readFileSync).toHaveBeenCalledWith(input, 'utf-8')
      expect(result).toBe(file_content)
    })

    it('should read file content for yaml-path format', () => {
      const input = '/path/to/file.yaml'
      const file_content = 'key: value'
      mock_fs.readFileSync.mockReturnValue(file_content)

      // Mock yaml.load
      const yaml = jest.requireMock('js-yaml')
      yaml.load = jest.fn().mockReturnValue({key: 'value'})

      const result = process_input(input, 'yaml-path', false)

      expect(mock_fs.readFileSync).toHaveBeenCalledWith(input, 'utf-8')
      expect(yaml.load).toHaveBeenCalledWith(file_content)
      expect(result).toBe('{\n  "key": "value"\n}')
    })

    it('should handle Windows path conversion for /tmp paths on win32', () => {
      const input = '/tmp/file.json'
      const file_content = '{"key": "value"}'
      const tmp_dir = 'C:\\Windows\\Temp'
      const expected_path = path.join(tmp_dir, 'file.json')

      mock_os.tmpdir = jest.fn().mockReturnValue(tmp_dir)
      mock_os.platform = jest.fn().mockReturnValue('win32')
      mock_fs.readFileSync.mockReturnValue(file_content)

      // Mock process.platform
      Object.defineProperty(process, 'platform', {
        value: 'win32',
        configurable: true,
      })

      const result = process_input(input, 'json-path', false)

      expect(mock_fs.readFileSync).toHaveBeenCalledWith(expected_path, 'utf-8')
      expect(result).toBe(file_content)

      // Reset
      Object.defineProperty(process, 'platform', {
        value: 'linux',
        configurable: true,
      })
    })

    it('should not convert path on non-Windows platforms', () => {
      const input = '/tmp/file.json'
      const file_content = '{"key": "value"}'

      mock_fs.readFileSync.mockReturnValue(file_content)

      Object.defineProperty(process, 'platform', {
        value: 'linux',
        configurable: true,
      })

      const result = process_input(input, 'json-path', false)

      expect(mock_fs.readFileSync).toHaveBeenCalledWith(input, 'utf-8')
      expect(result).toBe(file_content)
    })
  })

  describe('base64 decode', () => {
    it('should decode base64 input when decode is true', () => {
      const plain_text = 'Hello World'
      const base64_input = Buffer.from(plain_text).toString('base64')

      const result = process_input(base64_input, 'json', true)

      expect(result).toBe(plain_text)
    })

    it('should decode base64 input with UTF-8 characters', () => {
      const plain_text = '{"key": "value with émojis 🎉"}'
      const base64_input = Buffer.from(plain_text).toString('base64')

      const result = process_input(base64_input, 'json', true)

      expect(result).toBe(plain_text)
    })

    it('should not decode when decode is false', () => {
      const input = 'SGVsbG8gV29ybGQ='

      const result = process_input(input, 'json', false)

      expect(result).toBe(input)
    })
  })

  describe('YAML to JSON conversion', () => {
    it('should convert YAML to JSON for yaml format', () => {
      const input = 'key: value\narray:\n  - item1\n  - item2'
      const yaml = jest.requireMock('js-yaml')
      yaml.load = jest.fn().mockReturnValue({
        key: 'value',
        array: ['item1', 'item2'],
      })

      const result = process_input(input, 'yaml', false)

      expect(yaml.load).toHaveBeenCalledWith(input)
      expect(result).toBe('{\n  "key": "value",\n  "array": [\n    "item1",\n    "item2"\n  ]\n}')
    })

    it('should convert YAML to JSON for yaml-path format after reading file', () => {
      const input = '/path/to/file.yaml'
      const file_content = 'key: value'
      mock_fs.readFileSync.mockReturnValue(file_content)

      const yaml = jest.requireMock('js-yaml')
      yaml.load = jest.fn().mockReturnValue({key: 'value'})

      const result = process_input(input, 'yaml-path', false)

      expect(mock_fs.readFileSync).toHaveBeenCalledWith(input, 'utf-8')
      expect(yaml.load).toHaveBeenCalledWith(file_content)
      expect(result).toBe('{\n  "key": "value"\n}')
    })

    it('should not convert YAML for non-yaml formats', () => {
      const input = 'key: value'

      const result = process_input(input, 'json', false)

      expect(result).toBe(input)
    })
  })

  describe('combined operations', () => {
    it('should decode and convert YAML to JSON', () => {
      const yaml_text = 'key: value'
      const base64_input = Buffer.from(yaml_text).toString('base64')

      const yaml = jest.requireMock('js-yaml')
      yaml.load = jest.fn().mockReturnValue({key: 'value'})

      const result = process_input(base64_input, 'yaml', true)

      expect(yaml.load).toHaveBeenCalled()
      expect(result).toBe('{\n  "key": "value"\n}')
    })

    it('should read file and convert YAML to JSON on Windows', () => {
      const input = '/tmp/file.yaml'
      const file_content = 'key: value'
      const tmp_dir = 'C:\\Windows\\Temp'
      const expected_path = path.join(tmp_dir, 'file.yaml')

      mock_os.tmpdir = jest.fn().mockReturnValue(tmp_dir)
      mock_fs.readFileSync.mockReturnValue(file_content)

      Object.defineProperty(process, 'platform', {
        value: 'win32',
        configurable: true,
      })

      const yaml = jest.requireMock('js-yaml')
      yaml.load = jest.fn().mockReturnValue({key: 'value'})

      const result = process_input(input, 'yaml-path', false)

      expect(mock_fs.readFileSync).toHaveBeenCalledWith(expected_path, 'utf-8')
      expect(yaml.load).toHaveBeenCalledWith(file_content)
      expect(result).toBe('{\n  "key": "value"\n}')

      // Reset
      Object.defineProperty(process, 'platform', {
        value: 'linux',
        configurable: true,
      })
    })
  })
})
