from django.db import models
from django.core.validators import RegexValidator
class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mrn = models.CharField(
        max_length=6,
        unique=True,
        validators=[RegexValidator(regex=r'^\d{6}$', message='MRN must be exactly 6 digits')]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'patients'
        indexes = [
            models.Index(fields=['mrn']),
        ]
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.mrn})"
class Provider(models.Model):
    name = models.CharField(max_length=200)
    npi = models.CharField(
        max_length=10,
        unique=True,
        validators=[RegexValidator(regex=r'^\d{10}$', message='NPI must be exactly 10 digits')],
        help_text="National Provider Identifier - unique 10-digit number (one per provider)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'providers'
        indexes = [
            models.Index(fields=['npi']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['npi'], name='unique_provider_npi')
        ]
    def __str__(self):
        return f"{self.name} (NPI: {self.npi})"
    def save(self, *args, **kwargs):
        if len(self.npi) != 10:
            raise ValueError("NPI must be exactly 10 digits")
        super().save(*args, **kwargs)
class Order(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='orders')
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='orders')
    primary_diagnosis = models.CharField(max_length=20)
    additional_diagnoses = models.JSONField(default=list, blank=True)
    medication_name = models.CharField(max_length=200)
    medication_history = models.JSONField(default=list, blank=True)
    patient_records = models.TextField()
    care_plan = models.TextField(blank=True, null=True)
    care_plan_generated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
    def __str__(self):
        return f"Order {self.id} - {self.patient} - {self.medication_name}"