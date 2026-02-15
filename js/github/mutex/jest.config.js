module.exports = {
    clearMocks: true,
    moduleFileExtensions: ['js', 'ts'],
    testEnvironment: 'node',
    testMatch: ['**/*.test.ts'],
    testRunner: 'jest-circus/runner',
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
      '^@actions/exec$': '<rootDir>/node_modules/@actions/exec/lib/exec.js',
      '^@actions/io$': '<rootDir>/node_modules/@actions/io/lib/io.js',
      '^@actions/http-client$': '<rootDir>/node_modules/@actions/http-client/lib/index.js',
      '^@actions/http-client/(.*)$': '<rootDir>/node_modules/@actions/http-client/$1.js',
      '^@actions/([^/]+)/(.*)$': '<rootDir>/node_modules/@actions/$1/$2.js',
    },
    transformIgnorePatterns: [],
    verbose: true
}
