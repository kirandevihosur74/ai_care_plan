from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.http import HttpResponse, StreamingHttpResponse, FileResponse
from datetime import datetime
import logging
import re
import json
from io import BytesIO
from .models import Patient, Provider, Order
from .serializers import (
    OrderCreateSerializer,
    OrderResponseSerializer,
    ValidationResponseSerializer,
    CarePlanResponseSerializer
)
from .llm import generate_care_plan
from .duplicate_checker import DuplicateChecker
from .export import export_to_csv, export_to_excel, get_export_filename, get_orders_for_export
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
        logger.debug(f"Validating order for patient MRN: {data['patient_mrn']}, provider NPI: {data['provider_npi']}")
        
        validation_result = DuplicateChecker.validate_order(
            patient_first_name=data['patient_first_name'],
            patient_last_name=data['patient_last_name'],
            patient_mrn=data['patient_mrn'],
            provider_name=data['provider_name'],
            provider_npi=data['provider_npi'],
            medication_name=data['medication_name'],
            primary_diagnosis=data.get('primary_diagnosis'),
            additional_diagnoses=data.get('additional_diagnoses', []),
            medication_history=data.get('medication_history', [])
        )
        
        logger.info(f"Validation complete - MRN: {data['patient_mrn']}, valid: {validation_result['valid']}, errors: {len(validation_result['errors'])}, warnings: {len(validation_result['warnings'])}")
        
        if validation_result['valid']:
            return Response(validation_result, status=status.HTTP_200_OK)
        else:
            return Response(validation_result, status=status.HTTP_400_BAD_REQUEST)
            
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
        order.care_plan_generated_at = timezone.now()
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

def export_orders(request):
    try:
        format_param = request.GET.get('format', 'csv').lower()
        if format_param not in ['csv', 'excel', 'xlsx']:
            return HttpResponse(
                json.dumps({"detail": "Invalid format. Must be 'csv' or 'excel'"}),
                content_type='application/json',
                status=400
            )
        
        if format_param == 'excel':
            format_param = 'xlsx'
        
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        provider_npi = request.GET.get('provider_npi')
        diagnosis = request.GET.get('diagnosis')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                if 'T' in start_date_str:
                    start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                else:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                if start_date.tzinfo is None:
                    start_date = timezone.make_aware(start_date)
            except ValueError:
                return HttpResponse(
                    json.dumps({"detail": "Invalid start_date format. Use YYYY-MM-DD"}),
                    content_type='application/json',
                    status=400
                )
        
        if end_date_str:
            try:
                if 'T' in end_date_str:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                else:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                if end_date.tzinfo is None:
                    end_date = timezone.make_aware(end_date)
            except ValueError:
                return HttpResponse(
                    json.dumps({"detail": "Invalid end_date format. Use YYYY-MM-DD"}),
                    content_type='application/json',
                    status=400
                )
        
        logger.info(f"Export request - format: {format_param}, start_date: {start_date}, end_date: {end_date}, provider_npi: {provider_npi}, diagnosis: {diagnosis}")
        
        if format_param == 'csv':
            csv_content = export_to_csv(start_date, end_date, provider_npi, diagnosis)
            filename = get_export_filename('csv', start_date, end_date)
            response = HttpResponse(csv_content, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            logger.info(f"CSV export completed - filename: {filename}")
            return response
        elif format_param == 'xlsx':
            excel_content = export_to_excel(start_date, end_date, provider_npi, diagnosis)
            filename = get_export_filename('xlsx', start_date, end_date)
            response = HttpResponse(excel_content, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            logger.info(f"Excel export completed - filename: {filename}")
            return response
        
        return HttpResponse(
            json.dumps({"detail": "Invalid format"}),
            content_type='application/json',
            status=400
        )
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in export_orders: {str(e)}")
        logger.error(f"Traceback: {error_trace}")
        return HttpResponse(
            json.dumps({"detail": f"Internal server error: {str(e)}"}),
            content_type='application/json',
            status=500
        )

@api_view(['GET'])
def export_stats(request):
    try:
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        provider_npi = request.query_params.get('provider_npi')
        diagnosis = request.query_params.get('diagnosis')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                if 'T' in start_date_str:
                    start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                else:
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                if start_date.tzinfo is None:
                    start_date = timezone.make_aware(start_date)
            except ValueError:
                return Response(
                    {"detail": "Invalid start_date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if end_date_str:
            try:
                if 'T' in end_date_str:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                else:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                if end_date.tzinfo is None:
                    end_date = timezone.make_aware(end_date)
            except ValueError:
                return Response(
                    {"detail": "Invalid end_date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        orders = get_orders_for_export(start_date, end_date, provider_npi, diagnosis)
        
        total_orders = len(orders)
        care_plans_generated = sum(1 for order in orders if order.care_plan)
        
        if start_date and end_date:
            date_range = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elif start_date:
            date_range = f"From {start_date.strftime('%Y-%m-%d')}"
        elif end_date:
            date_range = f"Until {end_date.strftime('%Y-%m-%d')}"
        else:
            date_range = "All time"
        
        providers = list(set(order.provider.name for order in orders))
        diagnoses = list(set(order.primary_diagnosis for order in orders))
        
        stats = {
            "total_orders": total_orders,
            "care_plans_generated": care_plans_generated,
            "date_range": date_range,
            "providers": providers,
            "diagnoses": diagnoses
        }
        
        logger.info(f"Export stats requested - total_orders: {total_orders}, care_plans_generated: {care_plans_generated}")
        return Response(stats)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error in export_stats: {str(e)}")
        logger.error(f"Traceback: {error_trace}")
        return Response(
            {"detail": f"Internal server error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )