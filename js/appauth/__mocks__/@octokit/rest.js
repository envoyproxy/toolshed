const mockOctokitInstance = {
  apps: {
    listInstallations: jest.fn().mockResolvedValue({ data: [{ id: 123 }] })
  },
  auth: jest.fn().mockResolvedValue({ token: 'test-token' })
}

const MockOctokit = jest.fn().mockImplementation(() => mockOctokitInstance)

MockOctokit.plugin = jest.fn().mockReturnValue(MockOctokit)

module.exports = {
  Octokit: MockOctokit,
  _mockInstance: mockOctokitInstance,
}
