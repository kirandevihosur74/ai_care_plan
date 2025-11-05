'use client';
interface Warning {
  type: string;
  message: string;
}
interface WarningModalProps {
  warnings: Warning[];
  onProceed: () => void;
  onCancel: () => void;
}
export default function WarningModal({ warnings, onProceed, onCancel }: WarningModalProps) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h2 className="text-xl font-bold text-red-600 mb-4">⚠️ Validation Warnings</h2>
        <div className="space-y-2 mb-6">
          {warnings.map((warning, index) => (
            <div key={index} className="p-3 bg-yellow-50 border border-yellow-200 rounded">
              <p className="text-sm font-medium text-yellow-800">{warning.message}</p>
            </div>
          ))}
        </div>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={onProceed}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Proceed Anyway
          </button>
        </div>
      </div>
    </div>
  );
}