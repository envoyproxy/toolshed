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
    '^.+\\.ts$': 'ts-jest',
  },
  verbose: true,
  moduleNameMapper: {
    '^@octokit/auth-app$': '<rootDir>/__mocks__/@octokit/auth-app.js',
    '^@octokit/rest$': '<rootDir>/__mocks__/@octokit/rest.js'
  }
}
