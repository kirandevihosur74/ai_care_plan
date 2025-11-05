import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const format = searchParams.get('format') || 'csv';
    const startDate = searchParams.get('start_date');
    const endDate = searchParams.get('end_date');
    const providerNpi = searchParams.get('provider_npi');
    const diagnosis = searchParams.get('diagnosis');
    
    const params = new URLSearchParams();
    params.append('format', format);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (providerNpi) params.append('provider_npi', providerNpi);
    if (diagnosis) params.append('diagnosis', diagnosis);
    
    const response = await fetch(`${BACKEND_URL}/api/orders/export?${params.toString()}`, {
      method: 'GET',
      headers: {
        'Accept': format === 'csv' || format === 'xlsx' ? (format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') : 'text/csv',
      },
    });
    
    if (!response.ok) {
      let errorMessage = 'Export failed';
      try {
        const error = await response.json();
        errorMessage = error.detail || errorMessage;
      } catch {
        errorMessage = `Export failed with status ${response.status}`;
      }
      return NextResponse.json(
        { detail: errorMessage },
        { status: response.status }
      );
    }
    
    const blob = await response.blob();
    const filename = response.headers.get('Content-Disposition')?.split('filename=')[1]?.replace(/"/g, '') || `export.${format === 'csv' ? 'csv' : 'xlsx'}`;
    
    return new NextResponse(blob, {
      headers: {
        'Content-Type': format === 'csv' ? 'text/csv' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    });
  } catch (error: any) {
    console.error('Export proxy error:', error);
    return NextResponse.json(
      { detail: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

