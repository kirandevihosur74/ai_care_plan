import { NextRequest, NextResponse } from 'next/server';
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 180000); 
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/orders/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      const data = await response.json();
      
      return NextResponse.json(data, { status: response.status });
    } catch (error: any) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        return NextResponse.json(
          { detail: 'Request timeout - LLM generation is taking longer than expected' },
          { status: 504 }
        );
      }
      throw error;
    }
  } catch (error: any) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { detail: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}