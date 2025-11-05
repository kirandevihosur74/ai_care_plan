'use client';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useState } from 'react';
import WarningModal from '../components/WarningModal';
import ExportButton from '../components/ExportButton';
const orderSchema = z.object({
  patientFirstName: z.string().min(1, 'First name is required'),
  patientLastName: z.string().min(1, 'Last name is required'),
  patientMRN: z.string().regex(/^\d{6}$/, 'MRN must be exactly 6 digits'),
  providerName: z.string().min(1, 'Provider name is required'),
  providerNPI: z.string().regex(/^\d{10}$/, 'NPI must be exactly 10 digits'),
  primaryDiagnosis: z.string().regex(/^[A-Z]\d{2}(\.\d{1,2})?$/, 'Invalid ICD-10 format (e.g., G70.00)'),
  medicationName: z.string().min(1, 'Medication name is required'),
  additionalDiagnoses: z.string().optional(),
  medicationHistory: z.string().optional(),
  patientRecords: z.string().min(1, 'Patient records are required'),
});
type OrderFormData = z.infer<typeof orderSchema>;
interface Warning {
  type: string;
  message: string;
}
export default function CarePlanForm() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<OrderFormData>({
    resolver: zodResolver(orderSchema),
  });
  const [warnings, setWarnings] = useState<Warning[]>([]);
  const [showWarningModal, setShowWarningModal] = useState(false);
  const [carePlan, setCarePlan] = useState('');
  const [pendingSubmit, setPendingSubmit] = useState<(() => void) | null>(null);
  const onSubmit = async (data: OrderFormData) => {
    console.log('[Form] Submitting order form', {
      mrn: data.patientMRN,
      medication: data.medicationName,
      providerNPI: data.providerNPI,
    });
    
    try {
      
      console.log('[API] Calling validate endpoint');
      const validateResponse = await fetch('/api/orders/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          patient_first_name: data.patientFirstName,
          patient_last_name: data.patientLastName,
          patient_mrn: data.patientMRN,
          provider_name: data.providerName,
          provider_npi: data.providerNPI,
          primary_diagnosis: data.primaryDiagnosis,
          medication_name: data.medicationName,
          additional_diagnoses: data.additionalDiagnoses
            ? data.additionalDiagnoses.split(',').map((d) => d.trim()).filter(Boolean)
            : [],
          medication_history: data.medicationHistory
            ? data.medicationHistory.split(',').map((m) => m.trim()).filter(Boolean)
            : [],
          patient_records: data.patientRecords,
        }),
      });
      const validationResult = await validateResponse.json();
      console.log('[API] Validation response:', {
        valid: validationResult.valid,
        warningsCount: validationResult.warnings?.length || 0,
        warnings: validationResult.warnings,
      });
      if (validationResult.warnings && validationResult.warnings.length > 0) {
        console.warn('[Validation] Warnings found:', validationResult.warnings);
        setWarnings(validationResult.warnings);
        setShowWarningModal(true);
        setPendingSubmit(() => () => proceedWithGeneration(data));
        return;
      }
      console.log('[Validation] No warnings, proceeding with care plan generation');
      
      await proceedWithGeneration(data);
    } catch (error) {
      console.error('[Error] Form submission failed:', error);
      if (error instanceof Error) {
        console.error('[Error] Error details:', {
          message: error.message,
          stack: error.stack,
        });
      }
      alert('An error occurred. Please try again.');
    }
  };
  const proceedWithGeneration = async (data: OrderFormData) => {
    console.log('[Generation] Starting care plan generation', {
      mrn: data.patientMRN,
      medication: data.medicationName,
    });
    
    
    
    console.log('[API] Calling generate endpoint');
    const controller = new AbortController();
    let timeoutId: NodeJS.Timeout | null = setTimeout(() => controller.abort(), 180000); 
    
    try {
        const generateResponse = await fetch('/api/orders/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          signal: controller.signal,
          body: JSON.stringify({
            patient_first_name: data.patientFirstName,
            patient_last_name: data.patientLastName,
            patient_mrn: data.patientMRN,
            provider_name: data.providerName,
            provider_npi: data.providerNPI,
            primary_diagnosis: data.primaryDiagnosis,
            medication_name: data.medicationName,
            additional_diagnoses: data.additionalDiagnoses
              ? data.additionalDiagnoses.split(',').map((d) => d.trim()).filter(Boolean)
              : [],
            medication_history: data.medicationHistory
              ? data.medicationHistory.split(',').map((m) => m.trim()).filter(Boolean)
              : [],
            patient_records: data.patientRecords,
          }),
        });
        if (timeoutId) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
        if (!generateResponse.ok) {
          const errorText = await generateResponse.text();
          console.error('[API] Generate endpoint error:', {
            status: generateResponse.status,
            statusText: generateResponse.statusText,
            body: errorText,
          });
          throw new Error(`Failed to generate care plan: ${generateResponse.statusText}`);
        }
        const result = await generateResponse.json();
        console.log('[API] Care plan generated successfully', {
          orderId: result.order_id,
          carePlanLength: result.care_plan?.length || 0,
        });
        
        setCarePlan(result.care_plan);
        setShowWarningModal(false);
        setWarnings([]);
        console.log('[Form] Care plan displayed to user');
    } catch (error) {
      console.error('[Error] Care plan generation failed:', error);
      if (error instanceof Error) {
        console.error('[Error] Error details:', {
          message: error.message,
          stack: error.stack,
        });
        if (error.name === 'AbortError') {
          alert('Request timed out. The care plan generation is taking longer than expected. Please try again or check the backend logs.');
        } else {
          alert('Failed to generate care plan. Please try again.');
        }
      } else {
        alert('Failed to generate care plan. Please try again.');
      }
    } finally {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    }
  };
  const handleProceed = () => {
    console.log('[Warning] User chose to proceed despite warnings');
    if (pendingSubmit) {
      pendingSubmit();
      setPendingSubmit(null);
    }
  };
  const handleCancel = () => {
    console.log('[Warning] User canceled form submission');
    setShowWarningModal(false);
    setWarnings([]);
    setPendingSubmit(null);
  };
  const downloadCarePlan = () => {
    if (!carePlan) {
      console.warn('[Download] No care plan to download');
      return;
    }
    console.log('[Download] Downloading care plan');
    const blob = new Blob([carePlan], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `care-plan-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white shadow-lg rounded-lg p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">
            AI Care Plan Generator
          </h1>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {}
            <div className="border-b pb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Patient Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    First Name *
                  </label>
                  <input
                    {...register('patientFirstName')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  {errors.patientFirstName && (
                    <p className="text-red-500 text-sm mt-1">{errors.patientFirstName.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Last Name *
                  </label>
                  <input
                    {...register('patientLastName')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  {errors.patientLastName && (
                    <p className="text-red-500 text-sm mt-1">{errors.patientLastName.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    MRN (6 digits) *
                  </label>
                  <input
                    {...register('patientMRN')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    maxLength={6}
                  />
                  {errors.patientMRN && (
                    <p className="text-red-500 text-sm mt-1">{errors.patientMRN.message}</p>
                  )}
                </div>
              </div>
            </div>
            {}
            <div className="border-b pb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Provider Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Provider Name *
                  </label>
                  <input
                    {...register('providerName')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  {errors.providerName && (
                    <p className="text-red-500 text-sm mt-1">{errors.providerName.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    NPI (10 digits) *
                  </label>
                  <input
                    {...register('providerNPI')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    maxLength={10}
                  />
                  {errors.providerNPI && (
                    <p className="text-red-500 text-sm mt-1">{errors.providerNPI.message}</p>
                  )}
                </div>
              </div>
            </div>
            {}
            <div className="border-b pb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Clinical Data</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Primary Diagnosis (ICD-10) *
                  </label>
                  <input
                    {...register('primaryDiagnosis')}
                    placeholder="e.g., G70.00"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  {errors.primaryDiagnosis && (
                    <p className="text-red-500 text-sm mt-1">{errors.primaryDiagnosis.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Additional Diagnoses (comma-separated)
                  </label>
                  <input
                    {...register('additionalDiagnoses')}
                    placeholder="G70.01, E11.9"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Medication Name *
                  </label>
                  <input
                    {...register('medicationName')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  {errors.medicationName && (
                    <p className="text-red-500 text-sm mt-1">{errors.medicationName.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Medication History (comma-separated)
                  </label>
                  <input
                    {...register('medicationHistory')}
                    placeholder="Lisinopril 10mg, Metformin 500mg"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>
            {}
            <div className="border-b pb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Patient Records</h2>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Patient Records (Text) *
                </label>
                <textarea
                  {...register('patientRecords')}
                  rows={8}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter patient records, clinical notes, or paste PDF content here..."
                />
                {errors.patientRecords && (
                  <p className="text-red-500 text-sm mt-1">{errors.patientRecords.message}</p>
                )}
              </div>
            </div>
            {}
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Generating...' : 'Generate Care Plan'}
              </button>
            </div>
          </form>
          {}
          {carePlan && (
            <div className="mt-8 border-t pt-8">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold text-gray-900">Generated Care Plan</h2>
                <button
                  onClick={downloadCarePlan}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                >
                  Download as Text File
                </button>
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-md p-6">
                <pre className="whitespace-pre-wrap font-sans text-sm text-gray-900">
                  {carePlan}
                </pre>
              </div>
            </div>
          )}
          <ExportButton />
        </div>
      </div>
      {showWarningModal && (
        <WarningModal
          warnings={warnings}
          onProceed={handleProceed}
          onCancel={handleCancel}
        />
      )}
    </div>
  );
}