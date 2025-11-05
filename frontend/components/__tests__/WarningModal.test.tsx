import { render, screen, fireEvent } from '@testing-library/react'
import WarningModal from '../WarningModal'

describe('WarningModal', () => {
  const mockWarnings = [
    { type: 'duplicate_patient', message: 'Patient MRN 123456 already exists' },
    { type: 'potential_duplicate_order', message: 'Similar order found within 24 hours' }
  ]

  const mockOnProceed = jest.fn()
  const mockOnCancel = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders warning messages', () => {
    render(
      <WarningModal
        warnings={mockWarnings}
        onProceed={mockOnProceed}
        onCancel={mockOnCancel}
      />
    )

    expect(screen.getByText(/Validation Warnings/i)).toBeInTheDocument()
    expect(screen.getByText('Patient MRN 123456 already exists')).toBeInTheDocument()
    expect(screen.getByText('Similar order found within 24 hours')).toBeInTheDocument()
  })

  it('calls onProceed when Proceed Anyway is clicked', () => {
    render(
      <WarningModal
        warnings={mockWarnings}
        onProceed={mockOnProceed}
        onCancel={mockOnCancel}
      />
    )

    const proceedButton = screen.getByText('Proceed Anyway')
    fireEvent.click(proceedButton)

    expect(mockOnProceed).toHaveBeenCalledTimes(1)
    expect(mockOnCancel).not.toHaveBeenCalled()
  })

  it('calls onCancel when Cancel is clicked', () => {
    render(
      <WarningModal
        warnings={mockWarnings}
        onProceed={mockOnProceed}
        onCancel={mockOnCancel}
      />
    )

    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)

    expect(mockOnCancel).toHaveBeenCalledTimes(1)
    expect(mockOnProceed).not.toHaveBeenCalled()
  })

  it('renders with empty warnings array', () => {
    render(
      <WarningModal
        warnings={[]}
        onProceed={mockOnProceed}
        onCancel={mockOnCancel}
      />
    )

    expect(screen.getByText(/Validation Warnings/i)).toBeInTheDocument()
  })
})

