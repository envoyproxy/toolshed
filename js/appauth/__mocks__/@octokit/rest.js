const mockOctokitInstance = {
  apps: {
    listInstallations: jest.fn().mockResolvedValue({ data: [{ id: 123 }] })
  },
  auth: jest.fn().mockResolvedValue({ token: 'test-token' })
}

const MockOctokit = jest.fn().mockImplementation(() => mockOctokitInstance)

module.exports = {
  Octokit: MockOctokit,
  _mockInstance: mockOctokitInstance,
}
