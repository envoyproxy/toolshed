import fs from 'fs'
import os from 'os'
import * as path from 'path'
import tmp from 'tmp'
import {build_filter, cleanup_temp_files} from '../src/filter'
import type {TempFileHandles} from '../src/types'

// Mock dependencies
jest.mock('fs')
jest.mock('os')
jest.mock('tmp')

const mock_fs = fs as jest.Mocked<typeof fs>
const mock_os = os as jest.Mocked<typeof os>
const mock_tmp = tmp as jest.Mocked<typeof tmp>

describe('build_filter', () => {
  const mock_mod_path = path.join(__dirname, '../../../jq')

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('basic filter without filter_fun', () => {
    it('should build filter with imports and no temp file on non-Windows', () => {
      const filter = '. | select(.status == "active")'
      const expected_filter = `import "args" as args; import "bash" as bash; import "gfm" as gfm; import "github" as github; import "str" as str; import "utils" as utils; import "validate" as validate; ${filter}`

      mock_os.platform.mockReturnValue('linux')

      const result = build_filter(filter, undefined, false)

      expect(result.filter_arg).toBe(`'${expected_filter}'`)
      expect(result.filter_fun_arg).toBe(`-L ${mock_mod_path}`)
      expect(result.temp_handles).toEqual({})
    })

    it('should build filter with imports on macOS', () => {
      const filter = '.name'
      const expected_filter = `import "args" as args; import "bash" as bash; import "gfm" as gfm; import "github" as github; import "str" as str; import "utils" as utils; import "validate" as validate; ${filter}`

      mock_os.platform.mockReturnValue('darwin')

      const result = build_filter(filter, undefined, false)

      expect(result.filter_arg).toBe(`'${expected_filter}'`)
      expect(result.filter_fun_arg).toBe(`-L ${mock_mod_path}`)
      expect(result.temp_handles).toEqual({})
    })
  })

  describe('filter with temp file', () => {
    it('should use temp file on Windows platform', () => {
      const filter = '.data'
      const tmp_file_name = '/tmp/filter-123.jq'
      const mock_tmp_file = {
        name: tmp_file_name,
        removeCallback: jest.fn(),
      }

      mock_os.platform.mockReturnValue('win32')
      mock_tmp.fileSync.mockReturnValue(mock_tmp_file as any)
      mock_fs.writeFileSync.mockImplementation()

      const result = build_filter(filter, undefined, false)

      expect(mock_tmp.fileSync).toHaveBeenCalled()
      expect(mock_fs.writeFileSync).toHaveBeenCalled()
      expect(result.filter_arg).toBe(`-f ${tmp_file_name}`)
      expect(result.temp_handles.tmp_file_filter).toBe(mock_tmp_file)
    })

    it('should use temp file when use_tmp_file_for_filter is true', () => {
      const filter = '.items[]'
      const tmp_file_name = '/tmp/filter-456.jq'
      const mock_tmp_file = {
        name: tmp_file_name,
        removeCallback: jest.fn(),
      }

      mock_os.platform.mockReturnValue('linux')
      mock_tmp.fileSync.mockReturnValue(mock_tmp_file as any)
      mock_fs.writeFileSync.mockImplementation()

      const result = build_filter(filter, undefined, true)

      expect(mock_tmp.fileSync).toHaveBeenCalled()
      expect(result.filter_arg).toBe(`-f ${tmp_file_name}`)
      expect(result.temp_handles.tmp_file_filter).toBe(mock_tmp_file)
    })

    it('should write mangled filter to temp file', () => {
      const filter = '.test'
      const tmp_file_name = '/tmp/filter-789.jq'
      const expected_filter = `import "args" as args; import "bash" as bash; import "gfm" as gfm; import "github" as github; import "str" as str; import "utils" as utils; import "validate" as validate; ${filter}`
      const mock_tmp_file = {
        name: tmp_file_name,
        removeCallback: jest.fn(),
      }

      mock_os.platform.mockReturnValue('win32')
      mock_tmp.fileSync.mockReturnValue(mock_tmp_file as any)
      mock_fs.writeFileSync.mockImplementation()

      build_filter(filter, undefined, false)

      expect(mock_fs.writeFileSync).toHaveBeenCalledWith(tmp_file_name, expected_filter)
    })
  })

  describe('filter with filter_fun', () => {
    it('should create temp dir for filter_fun and import it', () => {
      const filter = 'fun::process_data'
      const filter_fun = 'def process_data: . | select(.active)'
      const tmp_dir_name = '/tmp/fun-dir-123'
      const fun_path = path.join(tmp_dir_name, 'fun.jq')
      const mock_tmp_dir = {
        name: tmp_dir_name,
        removeCallback: jest.fn(),
      }

      mock_os.platform.mockReturnValue('linux')
      mock_tmp.dirSync.mockReturnValue(mock_tmp_dir as any)
      mock_fs.writeFileSync.mockImplementation()

      const result = build_filter(filter, filter_fun, false)

      expect(mock_tmp.dirSync).toHaveBeenCalled()
      expect(mock_fs.writeFileSync).toHaveBeenCalledWith(fun_path, filter_fun)
      expect(result.filter_fun_arg).toBe(`-L ${tmp_dir_name}`)
      expect(result.temp_handles.tmp_dir_fun).toBe(mock_tmp_dir)
      const expected_filter = `import "fun" as fun; import "args" as args; import "bash" as bash; import "gfm" as gfm; import "github" as github; import "str" as str; import "utils" as utils; import "validate" as validate; ${filter}`
      expect(result.filter_arg).toBe(`'${expected_filter}'`)
    })

    it('should handle filter_fun with temp file for filter on Windows', () => {
      const filter = 'fun::custom'
      const filter_fun = 'def custom: .field'
      const tmp_dir_name = '/tmp/fun-dir-456'
      const tmp_file_name = '/tmp/filter-456.jq'
      const mock_tmp_dir = {
        name: tmp_dir_name,
        removeCallback: jest.fn(),
      }
      const mock_tmp_file = {
        name: tmp_file_name,
        removeCallback: jest.fn(),
      }

      mock_os.platform.mockReturnValue('win32')
      mock_tmp.dirSync.mockReturnValue(mock_tmp_dir as any)
      mock_tmp.fileSync.mockReturnValue(mock_tmp_file as any)
      mock_fs.writeFileSync.mockImplementation()

      const result = build_filter(filter, filter_fun, false)

      expect(mock_tmp.dirSync).toHaveBeenCalled()
      expect(mock_tmp.fileSync).toHaveBeenCalled()
      expect(result.filter_arg).toBe(`-f ${tmp_file_name}`)
      expect(result.filter_fun_arg).toBe(`-L ${tmp_dir_name}`)
      expect(result.temp_handles.tmp_dir_fun).toBe(mock_tmp_dir)
      expect(result.temp_handles.tmp_file_filter).toBe(mock_tmp_file)
    })

    it('should write filter_fun to fun.jq in temp directory', () => {
      const filter = '.data'
      const filter_fun = 'def helper: . * 2'
      const tmp_dir_name = '/tmp/fun-dir-789'
      const expected_fun_path = path.join(tmp_dir_name, 'fun.jq')
      const mock_tmp_dir = {
        name: tmp_dir_name,
        removeCallback: jest.fn(),
      }

      mock_os.platform.mockReturnValue('linux')
      mock_tmp.dirSync.mockReturnValue(mock_tmp_dir as any)
      mock_fs.writeFileSync.mockImplementation()

      build_filter(filter, filter_fun, false)

      expect(mock_fs.writeFileSync).toHaveBeenCalledWith(expected_fun_path, filter_fun)
    })
  })

  describe('filter imports', () => {
    it('should include all standard imports', () => {
      const filter = '.test'
      mock_os.platform.mockReturnValue('linux')

      const result = build_filter(filter, undefined, false)

      // Check that filter_arg contains all expected imports
      expect(result.filter_arg).toContain('import "args" as args')
      expect(result.filter_arg).toContain('import "bash" as bash')
      expect(result.filter_arg).toContain('import "gfm" as gfm')
      expect(result.filter_arg).toContain('import "github" as github')
      expect(result.filter_arg).toContain('import "str" as str')
      expect(result.filter_arg).toContain('import "utils" as utils')
      expect(result.filter_arg).toContain('import "validate" as validate')
    })

    it('should add fun import when filter_fun is provided', () => {
      const filter = '.test'
      const filter_fun = 'def test: .'
      const mock_tmp_dir = {
        name: '/tmp/fun-dir',
        removeCallback: jest.fn(),
      }

      mock_os.platform.mockReturnValue('linux')
      mock_tmp.dirSync.mockReturnValue(mock_tmp_dir as any)
      mock_fs.writeFileSync.mockImplementation()

      const result = build_filter(filter, filter_fun, false)

      expect(result.filter_arg).toContain('import "fun" as fun')
    })
  })

  describe('edge cases', () => {
    it('should handle empty filter string', () => {
      const filter = ''
      mock_os.platform.mockReturnValue('linux')

      const result = build_filter(filter, undefined, false)

      expect(result.filter_arg).toContain('import "args" as args')
      expect(result.filter_fun_arg).toBe(`-L ${mock_mod_path}`)
    })

    it('should handle complex filter with special characters', () => {
      const filter = '. | select(.name | contains("test"))'
      mock_os.platform.mockReturnValue('linux')

      const result = build_filter(filter, undefined, false)

      expect(result.filter_arg).toContain(filter)
      expect(result.temp_handles).toEqual({})
    })

    it('should handle empty filter_fun string', () => {
      const filter = '.data'
      const filter_fun = ''

      mock_os.platform.mockReturnValue('linux')

      const result = build_filter(filter, filter_fun, false)

      expect(mock_tmp.dirSync).not.toHaveBeenCalled()
      expect(mock_fs.writeFileSync).not.toHaveBeenCalled()
      expect(result.filter_arg).not.toContain('import "fun" as fun')
    })
  })
})

describe('cleanup_temp_files', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should cleanup tmp_file when present', () => {
    const mock_tmp_file = {
      name: '/tmp/file-123',
      removeCallback: jest.fn(),
    }
    const temp_handles: TempFileHandles = {
      tmp_file: mock_tmp_file as any,
    }

    cleanup_temp_files(temp_handles)

    expect(mock_tmp_file.removeCallback).toHaveBeenCalled()
  })

  it('should cleanup tmp_file_filter when present', () => {
    const mock_tmp_file_filter = {
      name: '/tmp/filter-456',
      removeCallback: jest.fn(),
    }
    const temp_handles: TempFileHandles = {
      tmp_file_filter: mock_tmp_file_filter as any,
    }

    cleanup_temp_files(temp_handles)

    expect(mock_tmp_file_filter.removeCallback).toHaveBeenCalled()
  })

  it('should cleanup tmp_dir_fun when present', () => {
    const mock_tmp_dir_fun = {
      name: '/tmp/fun-dir-789',
      removeCallback: jest.fn(),
    }
    const temp_handles: TempFileHandles = {
      tmp_dir_fun: mock_tmp_dir_fun as any,
    }

    cleanup_temp_files(temp_handles)

    expect(mock_tmp_dir_fun.removeCallback).toHaveBeenCalled()
  })

  it('should cleanup all temp files when all are present', () => {
    const mock_tmp_file = {
      name: '/tmp/file-1',
      removeCallback: jest.fn(),
    }
    const mock_tmp_file_filter = {
      name: '/tmp/filter-2',
      removeCallback: jest.fn(),
    }
    const mock_tmp_dir_fun = {
      name: '/tmp/fun-3',
      removeCallback: jest.fn(),
    }
    const temp_handles: TempFileHandles = {
      tmp_file: mock_tmp_file as any,
      tmp_file_filter: mock_tmp_file_filter as any,
      tmp_dir_fun: mock_tmp_dir_fun as any,
    }

    cleanup_temp_files(temp_handles)

    expect(mock_tmp_file.removeCallback).toHaveBeenCalled()
    expect(mock_tmp_file_filter.removeCallback).toHaveBeenCalled()
    expect(mock_tmp_dir_fun.removeCallback).toHaveBeenCalled()
  })

  it('should not throw when temp handles are empty', () => {
    const temp_handles: TempFileHandles = {}

    expect(() => cleanup_temp_files(temp_handles)).not.toThrow()
  })

  it('should not throw when only some handles are present', () => {
    const mock_tmp_file = {
      name: '/tmp/file-1',
      removeCallback: jest.fn(),
    }
    const temp_handles: TempFileHandles = {
      tmp_file: mock_tmp_file as any,
      // tmp_file_filter and tmp_dir_fun are undefined
    }

    expect(() => cleanup_temp_files(temp_handles)).not.toThrow()
    expect(mock_tmp_file.removeCallback).toHaveBeenCalled()
  })
})
