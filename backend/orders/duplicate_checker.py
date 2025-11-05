from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from django.utils import timezone
from datetime import timedelta
from .models import Patient, Provider, Order

@dataclass
class DuplicateWarning:
    warning_type: str
    severity: str
    message: str
    existing_record: Optional[Dict[str, Any]] = None

    def to_dict(self):
        result = {
            "type": self.warning_type,
            "severity": self.severity,
            "message": self.message
        }
        if self.existing_record:
            result["existing_record"] = self.existing_record
        return result

class DuplicateChecker:
    
    @staticmethod
    def check_duplicate_patient(mrn: str, first_name: str, last_name: str) -> Optional[DuplicateWarning]:
        try:
            existing_patient = Patient.objects.get(mrn=mrn)
            if (existing_patient.first_name.lower() != first_name.lower() or
                existing_patient.last_name.lower() != last_name.lower()):
                return DuplicateWarning(
                    warning_type="duplicate_patient_name_mismatch",
                    severity="error",
                    message=f"Patient MRN {mrn} already exists with different name: {existing_patient.first_name} {existing_patient.last_name}",
                    existing_record={
                        "mrn": existing_patient.mrn,
                        "first_name": existing_patient.first_name,
                        "last_name": existing_patient.last_name,
                        "created_at": existing_patient.created_at.isoformat()
                    }
                )
            else:
                return DuplicateWarning(
                    warning_type="duplicate_patient",
                    severity="warning",
                    message=f"Patient MRN {mrn} already exists in system",
                    existing_record={
                        "mrn": existing_patient.mrn,
                        "first_name": existing_patient.first_name,
                        "last_name": existing_patient.last_name,
                        "created_at": existing_patient.created_at.isoformat()
                    }
                )
        except Patient.DoesNotExist:
            return None
    
    @staticmethod
    def check_duplicate_provider(provider_name: str, npi: str) -> Optional[DuplicateWarning]:
        try:
            existing_provider_by_npi = Provider.objects.get(npi=npi)
            if existing_provider_by_npi.name.lower() != provider_name.lower():
                return DuplicateWarning(
                    warning_type="duplicate_provider_npi_name_mismatch",
                    severity="error",
                    message=f"NPI {npi} already exists with provider name: '{existing_provider_by_npi.name}'. You are submitting a different name: '{provider_name}'. NPI has a one-to-one relationship with provider - this is a critical data integrity issue for pharma reporting.",
                    existing_record={
                        "npi": existing_provider_by_npi.npi,
                        "name": existing_provider_by_npi.name,
                        "created_at": existing_provider_by_npi.created_at.isoformat()
                    }
                )
        except Provider.DoesNotExist:
            pass
        
        try:
            existing_provider_by_name = Provider.objects.get(name__iexact=provider_name)
            if existing_provider_by_name.npi != npi:
                return DuplicateWarning(
                    warning_type="duplicate_provider_npi_mismatch",
                    severity="error",
                    message=f"Provider '{provider_name}' already exists with NPI: {existing_provider_by_name.npi}. You are submitting a different NPI: {npi}. Each provider must have exactly one NPI - this is a critical data integrity issue for pharma reporting.",
                    existing_record={
                        "npi": existing_provider_by_name.npi,
                        "name": existing_provider_by_name.name,
                        "created_at": existing_provider_by_name.created_at.isoformat()
                    }
                )
        except Provider.DoesNotExist:
            pass
        
        return None
    
    @staticmethod
    def check_duplicate_order(mrn: str, medication_name: str) -> Optional[DuplicateWarning]:
        try:
            patient = Patient.objects.get(mrn=mrn)
            recent_orders = Order.objects.filter(
                patient=patient,
                medication_name=medication_name,
                created_at__gte=timezone.now() - timedelta(days=1)
            )
            
            if recent_orders.exists():
                order_details = []
                for order in recent_orders:
                    order_details.append({
                        "order_id": order.id,
                        "medication_name": order.medication_name,
                        "primary_diagnosis": order.primary_diagnosis,
                        "created_at": order.created_at.isoformat()
                    })
                
                order_ids = ', '.join(str(o.id) for o in recent_orders)
                return DuplicateWarning(
                    warning_type="potential_duplicate_order",
                    severity="warning",
                    message=f"Similar order found for this patient and medication within the last 24 hours. Order ID(s): {order_ids}",
                    existing_record={
                        "orders": order_details,
                        "count": len(order_details)
                    }
                )
        except Patient.DoesNotExist:
            pass
        
        return None
    
    @staticmethod
    def validate_order(
        patient_first_name: str,
        patient_last_name: str,
        patient_mrn: str,
        provider_name: str,
        provider_npi: str,
        medication_name: str,
        primary_diagnosis: str = None,
        additional_diagnoses: list = None,
        medication_history: list = None
    ) -> Dict[str, Any]:
        
        warnings = []
        errors = []
        
        patient_warning = DuplicateChecker.check_duplicate_patient(
            patient_mrn, patient_first_name, patient_last_name
        )
        if patient_warning:
            if patient_warning.severity == "error":
                errors.append(patient_warning.to_dict())
            else:
                warnings.append(patient_warning.to_dict())
        
        provider_warning = DuplicateChecker.check_duplicate_provider(
            provider_name, provider_npi
        )
        if provider_warning:
            if provider_warning.severity == "error":
                errors.append(provider_warning.to_dict())
            else:
                warnings.append(provider_warning.to_dict())
        
        order_warning = DuplicateChecker.check_duplicate_order(
            patient_mrn, medication_name
        )
        if order_warning:
            if order_warning.severity == "error":
                errors.append(order_warning.to_dict())
            else:
                warnings.append(order_warning.to_dict())
        
        valid = len(errors) == 0
        
        message = "Validation passed"
        if errors:
            message = f"Validation failed: {len(errors)} error(s) found that must be resolved"
        elif warnings:
            message = f"Validation passed with {len(warnings)} warning(s) requiring confirmation"
        
        return {
            "valid": valid,
            "warnings": warnings,
            "errors": errors,
            "message": message
        }
