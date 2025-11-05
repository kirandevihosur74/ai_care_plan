from rest_framework import serializers
from .models import Patient, Provider, Order
import re
class OrderCreateSerializer(serializers.Serializer):
    patient_first_name = serializers.CharField()
    patient_last_name = serializers.CharField()
    patient_mrn = serializers.CharField(max_length=6)
    provider_name = serializers.CharField()
    provider_npi = serializers.CharField(max_length=10)
    primary_diagnosis = serializers.CharField()
    medication_name = serializers.CharField()
    additional_diagnoses = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    medication_history = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    patient_records = serializers.CharField()
    def validate_patient_mrn(self, value):
        if not re.match(r'^\d{6}$', value):
            raise serializers.ValidationError('MRN must be exactly 6 digits')
        return value
    def validate_provider_npi(self, value):
        if not re.match(r'^\d{10}$', value):
            raise serializers.ValidationError('NPI must be exactly 10 digits')
        return value
    def validate_primary_diagnosis(self, value):
        if not re.match(r'^[A-Z]\d{2}(\.\d{1,2})?$', value):
            raise serializers.ValidationError('Invalid ICD-10 code format. Expected format: Letter + 2 digits + optional .digit(s) (e.g., G70.00)')
        return value
class OrderResponseSerializer(serializers.ModelSerializer):
    patient_mrn = serializers.CharField(source='patient.mrn', read_only=True)
    provider_npi = serializers.CharField(source='provider.npi', read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'patient_mrn', 'provider_npi', 'primary_diagnosis', 'medication_name', 'care_plan', 'created_at']
class ValidationResponseSerializer(serializers.Serializer):
    valid = serializers.BooleanField()
    warnings = serializers.ListField(
        child=serializers.DictField()
    )
class CarePlanResponseSerializer(serializers.Serializer):
    care_plan = serializers.CharField()
    order_id = serializers.IntegerField()