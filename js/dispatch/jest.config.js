const nock = require('nock')
nock.disableNetConnect()

const processStdoutWrite = process.stdout.write.bind(process.stdout)
process.stdout.write = (str, encoding, cb) => {
  if (!str.match(/^##/)) {
    return processStdoutWrite(str, encoding, cb)
  }
  return false
}

module.exports = {
  clearMocks: true,
  moduleFileExtensions: ['js', 'ts'],
  testEnvironment: 'node',
  testMatch: ['**/*.test.ts'],
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', {
      tsconfig: 'tsconfig.test.json',
    }],
    '^.+\\.(js|jsx)$': ['ts-jest', {
      tsconfig: {
        allowJs: true,
        module: 'commonjs',
      },
    }],
  },
  moduleNameMapper: {
    '^@actions/core$': '<rootDir>/node_modules/@actions/core/lib/core.js',
    '^@actions/github$': '<rootDir>/node_modules/@actions/github/lib/github.js',
    '^@actions/exec$': '<rootDir>/node_modules/@actions/exec/lib/exec.js',
    '^@actions/io$': '<rootDir>/node_modules/@actions/io/lib/io.js',
    '^@actions/http-client$': '<rootDir>/node_modules/@actions/http-client/lib/index.js',
    '^@actions/([^/]+)/(.*)$': '<rootDir>/node_modules/@actions/$1/$2.js',
    '^@actions/([^/]+)$': '<rootDir>/node_modules/@actions/$1/lib/index.js',
  },
  transformIgnorePatterns: [],
  verbose: true,
}
