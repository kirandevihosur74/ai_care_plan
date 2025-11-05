from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
import json
import logging
from .models import Patient, Provider, Order
from .serializers import (
    OrderCreateSerializer,
    OrderResponseSerializer,
    ValidationResponseSerializer,
    CarePlanResponseSerializer
)
from .llm import generate_care_plan
logger = logging.getLogger('orders')
@api_view(['GET'])
def api_root(request):
    logger.info(f"API root accessed from {request.META.get('REMOTE_ADDR', 'unknown')}")
    return Response({"message": "AI Care Plan Generator API"})
@api_view(['POST'])
def validate_order(request):
    try:
        logger.info(f"Validation request received - MRN: {request.data.get('patient_mrn', 'N/A')}, NPI: {request.data.get('provider_npi', 'N/A')}")
        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        warnings = []
        logger.debug(f"Validating order for patient MRN: {data['patient_mrn']}, provider NPI: {data['provider_npi']}")
        try:
            existing_patient = Patient.objects.get(mrn=data['patient_mrn'])
            logger.info(f"Duplicate patient found - MRN: {data['patient_mrn']}")
            if (existing_patient.first_name.lower() != data['patient_first_name'].lower() or
                existing_patient.last_name.lower() != data['patient_last_name'].lower()):
                warning_msg = f"Patient MRN {data['patient_mrn']} already exists with different name: {existing_patient.first_name} {existing_patient.last_name}"
                logger.warning(warning_msg)
                warnings.append({
                    "type": "duplicate_patient_name_mismatch",
                    "message": warning_msg
                })
            else:
                logger.info(f"Duplicate patient confirmed - MRN: {data['patient_mrn']}")
                warnings.append({
                    "type": "duplicate_patient",
                    "message": f"Patient MRN {data['patient_mrn']} already exists in system"
                })
        except Patient.DoesNotExist:
            logger.debug(f"New patient - MRN: {data['patient_mrn']}")
            pass
        try:
            patient = Patient.objects.get(mrn=data['patient_mrn'])
            recent_orders = Order.objects.filter(
                patient=patient,
                medication_name=data['medication_name'],
                created_at__gte=timezone.now() - timedelta(days=1)
            )
        except Patient.DoesNotExist:
            recent_orders = Order.objects.none()
        if recent_orders.exists():
            order_ids = ', '.join(str(o.id) for o in recent_orders)
            warning_msg = f"Similar order found for this patient and medication within the last 24 hours. Order ID(s): {order_ids}"
            logger.warning(warning_msg)
            warnings.append({
                "type": "potential_duplicate_order",
                "message": warning_msg
            })
        try:
            existing_provider_by_npi = Provider.objects.get(npi=data['provider_npi'])
            if existing_provider_by_npi.name.lower() != data['provider_name'].lower():
                warning_msg = f"NPI {data['provider_npi']} already exists with provider name: '{existing_provider_by_npi.name}'. You are submitting a different name: '{data['provider_name']}'. NPI has a one-to-one relationship with provider - this is a data integrity issue."
                logger.error(f"CRITICAL: {warning_msg}")
                warnings.append({
                    "type": "provider_npi_name_mismatch",
                    "severity": "CRITICAL",
                    "message": warning_msg
                })
        except Provider.DoesNotExist:
            logger.debug(f"New provider - NPI: {data['provider_npi']}")
            pass
        try:
            existing_provider_by_name = Provider.objects.get(name__iexact=data['provider_name'])
            if existing_provider_by_name.npi != data['provider_npi']:
                warning_msg = f"Provider '{data['provider_name']}' already exists with NPI: {existing_provider_by_name.npi}. You are submitting a different NPI: {data['provider_npi']}. Each provider must have exactly one NPI - this is a data integrity issue for pharma reporting."
                logger.error(f"CRITICAL: {warning_msg}")
                warnings.append({
                    "type": "provider_npi_mismatch",
                    "severity": "CRITICAL",
                    "message": warning_msg
                })
        except Provider.DoesNotExist:
            pass
        logger.info(f"Validation complete - MRN: {data['patient_mrn']}, warnings: {len(warnings)}")
        return Response({
            "valid": True,
            "warnings": warnings
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in validate_order: {str(e)}")
        logger.error(f"Traceback: {error_trace}")
        return Response(
            {"detail": f"Internal server error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['POST'])
def generate_order(request):
    logger.info(f"Generate order request received - MRN: {request.data.get('patient_mrn', 'N/A')}, Medication: {request.data.get('medication_name', 'N/A')}")
    serializer = OrderCreateSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Generate order validation failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    data = serializer.validated_data
    logger.debug(f"Generating care plan for patient MRN: {data['patient_mrn']}, medication: {data['medication_name']}")
    patient, created = Patient.objects.get_or_create(
        mrn=data['patient_mrn'],
        defaults={
            'first_name': data['patient_first_name'],
            'last_name': data['patient_last_name']
        }
    )
    if created:
        logger.info(f"New patient created - MRN: {patient.mrn}, Name: {patient.first_name} {patient.last_name}")
    if patient.first_name != data['patient_first_name'] or patient.last_name != data['patient_last_name']:
        logger.info(f"Updating patient names - MRN: {patient.mrn}")
        patient.first_name = data['patient_first_name']
        patient.last_name = data['patient_last_name']
        patient.save()
    try:
        provider = Provider.objects.get(npi=data['provider_npi'])
        logger.debug(f"Existing provider found - NPI: {provider.npi}, Name: {provider.name}")
        if provider.name != data['provider_name']:
            logger.info(f"Updating provider name - NPI: {provider.npi}, Old: {provider.name}, New: {data['provider_name']}")
            provider.name = data['provider_name']
            provider.save()
    except Provider.DoesNotExist:
        logger.info(f"New provider created - NPI: {data['provider_npi']}, Name: {data['provider_name']}")
        provider = Provider.objects.create(
            npi=data['provider_npi'],
            name=data['provider_name']
        )
    order = Order.objects.create(
        patient=patient,
        provider=provider,
        primary_diagnosis=data['primary_diagnosis'],
        additional_diagnoses=data.get('additional_diagnoses', []),
        medication_name=data['medication_name'],
        medication_history=data.get('medication_history', []),
        patient_records=data['patient_records'],
    )
    logger.info(f"Order created - ID: {order.id}, Patient MRN: {patient.mrn}, Medication: {data['medication_name']}")
    try:
        logger.info(f"Starting LLM care plan generation for order ID: {order.id}")
        care_plan = generate_care_plan(
            patient_records=data['patient_records'],
            primary_diagnosis=data['primary_diagnosis'],
            medication_name=data['medication_name'],
            additional_diagnoses=data.get('additional_diagnoses', []),
            medication_history=data.get('medication_history', []),
            patient_first_name=data['patient_first_name'],
            patient_last_name=data['patient_last_name'],
            patient_mrn=data['patient_mrn'],
        )
        order.care_plan = care_plan
        order.save()
        logger.info(f"Care plan generated successfully for order ID: {order.id}, length: {len(care_plan)} chars")
        response_serializer = CarePlanResponseSerializer(data={
            "care_plan": care_plan,
            "order_id": order.id
        })
        response_serializer.is_valid()
        return Response(response_serializer.validated_data, status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f"Failed to generate care plan for order ID: {order.id}, error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        order.delete()
        logger.info(f"Order {order.id} deleted due to care plan generation failure")
        return Response(
            {"detail": f"Failed to generate care plan: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['GET'])
def get_orders(request):
    skip = int(request.query_params.get('skip', 0))
    limit = int(request.query_params.get('limit', 100))
    orders = Order.objects.all()[skip:skip+limit]
    serializer = OrderResponseSerializer(orders, many=True)
    return Response(serializer.data)
@api_view(['GET'])
def get_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        serializer = OrderResponseSerializer(order)
        return Response(serializer.data)
    except Order.DoesNotExist:
        return Response(
            {"detail": "Order not found"},
            status=status.HTTP_404_NOT_FOUND
        )
@api_view(['GET'])
def export_all_care_plans(request):
    orders = Order.objects.filter(care_plan__isnull=False).exclude(care_plan='')
    export_data = []
    for order in orders:
        export_data.append({
            "order_id": order.id,
            "patient": {
                "name": f"{order.patient.first_name} {order.patient.last_name}",
                "mrn": order.patient.mrn,
            },
            "provider": {
                "name": order.provider.name,
                "npi": order.provider.npi,
            },
            "primary_diagnosis": order.primary_diagnosis,
            "medication": order.medication_name,
            "care_plan": order.care_plan,
            "created_at": order.created_at.isoformat(),
        })
    return Response({
        "total_orders": len(export_data),
        "orders": export_data,
    })