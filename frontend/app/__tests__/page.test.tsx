import { render, screen } from '@testing-library/react'
import CarePlanForm from '../page'

global.fetch = jest.fn()

describe('CarePlanForm', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(fetch as jest.Mock).mockClear()
  })

  it('renders the form component', () => {
    render(<CarePlanForm />)
    expect(screen.getByText(/Generate Care Plan/i)).toBeInTheDocument()
  })

  it('renders export button', () => {
    render(<CarePlanForm />)
    expect(screen.getByText(/Export for Pharma Reporting/i)).toBeInTheDocument()
  })
})

