module.exports = {
  Octokit: jest.fn().mockImplementation(() => ({
    apps: {
      listInstallations: jest.fn().mockResolvedValue({ data: [{ id: 123 }] })
    },
    auth: jest.fn().mockResolvedValue({ token: 'test-token' })
  }))
}
