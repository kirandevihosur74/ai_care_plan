'use client';
import { useState } from 'react';

interface ExportStats {
  total_orders: number;
  care_plans_generated: number;
  date_range: string;
  providers: string[];
  diagnoses: string[];
}

export default function ExportButton() {
  const [showFilters, setShowFilters] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [stats, setStats] = useState<ExportStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingStats, setLoadingStats] = useState(false);

  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      
      const response = await fetch(`/api/orders/export/stats?${params.toString()}`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      } else {
        alert('Failed to fetch stats');
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
      alert('Error fetching stats');
    } finally {
      setLoadingStats(false);
    }
  };

  const downloadExport = async (format: 'csv' | 'excel') => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('format', format === 'csv' ? 'csv' : 'xlsx');
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      
      const response = await fetch(`/api/orders/export?${params.toString()}`);
      
      if (!response.ok) {
        const error = await response.json();
        alert(error.detail || 'Export failed');
        return;
      }
      
      const blob = await response.blob();
      const contentDisposition = response.headers.get('Content-Disposition');
      const filename = contentDisposition
        ? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
        : `export.${format === 'csv' ? 'csv' : 'xlsx'}`;
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      if (stats) {
        alert(`Export completed! ${stats.total_orders} orders exported.`);
      } else {
        alert('Export completed!');
      }
    } catch (error) {
      console.error('Error downloading export:', error);
      alert('Error downloading export');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-8 border-t pt-8">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Export for Pharma Reporting</h2>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
        >
          {showFilters ? 'Hide Filters' : 'Show Filters'}
        </button>
      </div>
      
      {showFilters && (
        <div className="mb-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                End Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <button
            onClick={fetchStats}
            disabled={loadingStats}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loadingStats ? 'Loading...' : 'Preview Stats'}
          </button>
        </div>
      )}
      
      {stats && (
        <div className="mb-6 bg-blue-50 border border-blue-200 rounded-md p-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Export Preview</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-700">Total Orders:</span>
              <span className="ml-2 text-gray-900">{stats.total_orders}</span>
            </div>
            <div>
              <span className="font-medium text-gray-700">Care Plans Generated:</span>
              <span className="ml-2 text-gray-900">{stats.care_plans_generated}</span>
            </div>
            <div className="col-span-2">
              <span className="font-medium text-gray-700">Date Range:</span>
              <span className="ml-2 text-gray-900">{stats.date_range}</span>
            </div>
            {stats.providers.length > 0 && (
              <div className="col-span-2">
                <span className="font-medium text-gray-700">Providers:</span>
                <span className="ml-2 text-gray-900">{stats.providers.join(', ')}</span>
              </div>
            )}
            {stats.diagnoses.length > 0 && (
              <div className="col-span-2">
                <span className="font-medium text-gray-700">Diagnoses:</span>
                <span className="ml-2 text-gray-900">{stats.diagnoses.join(', ')}</span>
              </div>
            )}
          </div>
        </div>
      )}
      
      <div className="flex gap-4">
        <button
          onClick={() => downloadExport('csv')}
          disabled={loading}
          className="px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Exporting...' : 'Download CSV'}
        </button>
        <button
          onClick={() => downloadExport('excel')}
          disabled={loading}
          className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Exporting...' : 'Download Excel'}
        </button>
      </div>
    </div>
  );
}

