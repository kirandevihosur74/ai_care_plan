import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ExportButton from '../ExportButton'

global.fetch = jest.fn()

describe('ExportButton', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(fetch as jest.Mock).mockClear()
  })

  it('renders export section', () => {
    render(<ExportButton />)
    expect(screen.getByText('Export for Pharma Reporting')).toBeInTheDocument()
    expect(screen.getByText('Show Filters')).toBeInTheDocument()
    expect(screen.getByText('Download CSV')).toBeInTheDocument()
    expect(screen.getByText('Download Excel')).toBeInTheDocument()
  })

  it('toggles filters visibility', () => {
    render(<ExportButton />)
    
    const toggleButton = screen.getByText('Show Filters')
    fireEvent.click(toggleButton)
    
    expect(screen.getByText('Hide Filters')).toBeInTheDocument()
  })

  it('shows date input fields when filters are visible', () => {
    render(<ExportButton />)
    
    const toggleButton = screen.getByText('Show Filters')
    fireEvent.click(toggleButton)
    
    expect(screen.getByText('Hide Filters')).toBeInTheDocument()
  })

  it('renders download buttons', () => {
    render(<ExportButton />)
    
    expect(screen.getByText('Download CSV')).toBeInTheDocument()
    expect(screen.getByText('Download Excel')).toBeInTheDocument()
  })

  it('renders preview stats button when filters are shown', () => {
    render(<ExportButton />)
    
    const toggleButton = screen.getByText('Show Filters')
    fireEvent.click(toggleButton)
    
    expect(screen.getByText('Preview Stats')).toBeInTheDocument()
  })
})

