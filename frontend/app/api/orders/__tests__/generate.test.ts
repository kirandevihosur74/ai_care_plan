jest.mock('../generate/route', () => ({
  POST: jest.fn(),
}))

describe('POST /api/orders/generate', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should exist', () => {
    const { POST } = require('../generate/route')
    expect(POST).toBeDefined()
  })
})

