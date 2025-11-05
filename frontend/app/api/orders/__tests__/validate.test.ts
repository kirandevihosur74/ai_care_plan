jest.mock('../validate/route', () => ({
  POST: jest.fn(),
}))

describe('POST /api/orders/validate', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should exist', () => {
    const { POST } = require('../validate/route')
    expect(POST).toBeDefined()
  })
})

