import '@testing-library/jest-dom'

if (typeof window !== 'undefined') {
  if (!window.URL.createObjectURL) {
    window.URL.createObjectURL = jest.fn(() => 'mock-url')
  }
  if (!window.URL.revokeObjectURL) {
    window.URL.revokeObjectURL = jest.fn()
  }
  if (!window.URL) {
    window.URL = {
      createObjectURL: jest.fn(() => 'mock-url'),
      revokeObjectURL: jest.fn(),
    }
  }
}

if (typeof global !== 'undefined') {
  if (!global.Blob) {
    global.Blob = class Blob {
      constructor(parts, options) {
        this.parts = parts || []
        this.type = options?.type || ''
        this.size = this.parts.reduce((acc, part) => acc + (part.length || 0), 0)
      }
      slice(start, end, contentType) {
        return new Blob(this.parts.slice(start, end), { type: contentType || this.type })
      }
    }
  }
}

global.Request = class Request {
  constructor(input, init) {
    this.url = typeof input === 'string' ? input : input.url
    this.method = init?.method || 'GET'
    this.headers = new Headers(init?.headers || {})
    this.body = init?.body || null
  }
}

global.Response = class Response {
  constructor(body, init) {
    this.body = body
    this.status = init?.status || 200
    this.statusText = init?.statusText || 'OK'
    this.headers = new Headers(init?.headers || {})
    this.ok = this.status >= 200 && this.status < 300
  }
  json() {
    return Promise.resolve(this.body)
  }
  text() {
    return Promise.resolve(String(this.body))
  }
  blob() {
    return Promise.resolve(new Blob([this.body]))
  }
}

global.Headers = class Headers {
  constructor(init) {
    this._headers = {}
    if (init) {
      Object.entries(init).forEach(([key, value]) => {
        this._headers[key.toLowerCase()] = value
      })
    }
  }
  get(name) {
    return this._headers[name.toLowerCase()] || null
  }
  set(name, value) {
    this._headers[name.toLowerCase()] = value
  }
  has(name) {
    return name.toLowerCase() in this._headers
  }
}

