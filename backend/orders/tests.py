from django.test import TestCase, Client
from django.utils import timezone
from datetime import datetime, timedelta
import json
from .models import Patient, Provider, Order
from .duplicate_checker import DuplicateChecker, DuplicateWarning
from .export import export_to_csv, export_to_excel, get_orders_for_export, get_export_filename


class PatientModelTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456"
        )

    def test_patient_creation(self):
        self.assertEqual(self.patient.first_name, "John")
        self.assertEqual(self.patient.last_name, "Doe")
        self.assertEqual(self.patient.mrn, "123456")

    def test_patient_str(self):
        self.assertEqual(str(self.patient), "John Doe (123456)")

    def test_patient_mrn_unique(self):
        with self.assertRaises(Exception):
            Patient.objects.create(
                first_name="Jane",
                last_name="Doe",
                mrn="123456"
            )

    def test_patient_mrn_validation(self):
        from django.core.exceptions import ValidationError
        patient = Patient(
            first_name="Jane",
            last_name="Doe",
            mrn="12345"
        )
        try:
            patient.full_clean()
            self.fail("ValidationError should have been raised")
        except ValidationError as e:
            self.assertIn('mrn', e.message_dict)


class ProviderModelTest(TestCase):
    def setUp(self):
        self.provider = Provider.objects.create(
            name="Dr. Alice Johnson",
            npi="1234567890"
        )

    def test_provider_creation(self):
        self.assertEqual(self.provider.name, "Dr. Alice Johnson")
        self.assertEqual(self.provider.npi, "1234567890")

    def test_provider_str(self):
        self.assertEqual(str(self.provider), "Dr. Alice Johnson (NPI: 1234567890)")

    def test_provider_npi_unique(self):
        with self.assertRaises(Exception):
            Provider.objects.create(
                name="Dr. Bob Smith",
                npi="1234567890"
            )

    def test_provider_npi_validation(self):
        with self.assertRaises(ValueError):
            provider = Provider(npi="123456789")
            provider.save()


class OrderModelTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456"
        )
        self.provider = Provider.objects.create(
            name="Dr. Alice Johnson",
            npi="1234567890"
        )
        self.order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="G70.00",
            additional_diagnoses=["I10", "K21.9"],
            medication_name="IVIG (Privigen)",
            medication_history=["Lisinopril", "Metformin"],
            patient_records="Test patient records",
            care_plan="Test care plan"
        )

    def test_order_creation(self):
        self.assertEqual(self.order.patient, self.patient)
        self.assertEqual(self.order.provider, self.provider)
        self.assertEqual(self.order.primary_diagnosis, "G70.00")
        self.assertEqual(self.order.medication_name, "IVIG (Privigen)")

    def test_order_str(self):
        self.assertIn("Order", str(self.order))
        self.assertIn("IVIG", str(self.order))

    def test_order_cascade_delete(self):
        self.patient.delete()
        self.assertEqual(Order.objects.count(), 0)


class DuplicateCheckerTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456"
        )
        self.provider = Provider.objects.create(
            name="Dr. Alice Johnson",
            npi="1234567890"
        )
        self.order = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="G70.00",
            medication_name="IVIG (Privigen)",
            patient_records="Test records"
        )

    def test_check_duplicate_patient_same_name(self):
        warning = DuplicateChecker.check_duplicate_patient("123456", "John", "Doe")
        self.assertIsNotNone(warning)
        self.assertEqual(warning.warning_type, "duplicate_patient")
        self.assertEqual(warning.severity, "warning")

    def test_check_duplicate_patient_different_name(self):
        warning = DuplicateChecker.check_duplicate_patient("123456", "Jane", "Smith")
        self.assertIsNotNone(warning)
        self.assertEqual(warning.warning_type, "duplicate_patient_name_mismatch")
        self.assertEqual(warning.severity, "error")

    def test_check_duplicate_patient_not_exists(self):
        warning = DuplicateChecker.check_duplicate_patient("999999", "New", "Patient")
        self.assertIsNone(warning)

    def test_check_duplicate_provider_same_npi_different_name(self):
        warning = DuplicateChecker.check_duplicate_provider("Dr. Different Name", "1234567890")
        self.assertIsNotNone(warning)
        self.assertEqual(warning.warning_type, "duplicate_provider_npi_name_mismatch")
        self.assertEqual(warning.severity, "error")

    def test_check_duplicate_provider_same_name_different_npi(self):
        warning = DuplicateChecker.check_duplicate_provider("Dr. Alice Johnson", "9999999999")
        self.assertIsNotNone(warning)
        self.assertEqual(warning.warning_type, "duplicate_provider_npi_mismatch")
        self.assertEqual(warning.severity, "error")

    def test_check_duplicate_provider_not_exists(self):
        warning = DuplicateChecker.check_duplicate_provider("Dr. New Provider", "9999999999")
        self.assertIsNone(warning)

    def test_check_duplicate_order_within_24h(self):
        warning = DuplicateChecker.check_duplicate_order("123456", "IVIG (Privigen)")
        self.assertIsNotNone(warning)
        self.assertEqual(warning.warning_type, "potential_duplicate_order")
        self.assertEqual(warning.severity, "warning")

    def test_check_duplicate_order_outside_24h(self):
        self.order.created_at = timezone.now() - timedelta(days=2)
        self.order.save()
        warning = DuplicateChecker.check_duplicate_order("123456", "IVIG (Privigen)")
        self.assertIsNone(warning)

    def test_check_duplicate_order_different_medication(self):
        warning = DuplicateChecker.check_duplicate_order("123456", "Different Medication")
        self.assertIsNone(warning)

    def test_validate_order_no_duplicates(self):
        result = DuplicateChecker.validate_order(
            "Jane", "Smith", "999999",
            "Dr. New Provider", "9999999999",
            "New Medication"
        )
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["errors"]), 0)
        self.assertEqual(len(result["warnings"]), 0)

    def test_validate_order_with_warnings(self):
        result = DuplicateChecker.validate_order(
            "John", "Doe", "123456",
            "Dr. Alice Johnson", "1234567890",
            "IVIG (Privigen)"
        )
        self.assertTrue(result["valid"])
        self.assertGreater(len(result["warnings"]), 0)

    def test_validate_order_with_errors(self):
        result = DuplicateChecker.validate_order(
            "Jane", "Smith", "123456",
            "Dr. Different Name", "1234567890",
            "Test Medication"
        )
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["errors"]), 0)


class ExportTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456"
        )
        self.provider = Provider.objects.create(
            name="Dr. Alice Johnson",
            npi="1234567890"
        )
        self.order1 = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="G70.00",
            medication_name="IVIG (Privigen)",
            patient_records="Test records",
            care_plan="Test care plan"
        )
        self.order2 = Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="I10",
            medication_name="Lisinopril",
            patient_records="Test records"
        )

    def test_get_orders_for_export_all(self):
        orders = get_orders_for_export()
        self.assertEqual(len(orders), 2)

    def test_get_orders_for_export_with_date_filter(self):
        start_date = timezone.now() - timedelta(days=1)
        end_date = timezone.now() + timedelta(days=1)
        orders = get_orders_for_export(start_date=start_date, end_date=end_date)
        self.assertEqual(len(orders), 2)

    def test_get_orders_for_export_with_provider_filter(self):
        orders = get_orders_for_export(provider_npi="1234567890")
        self.assertEqual(len(orders), 2)

    def test_get_orders_for_export_with_diagnosis_filter(self):
        orders = get_orders_for_export(diagnosis="G70.00")
        self.assertGreaterEqual(len(orders), 1)
        self.assertTrue(any(order.primary_diagnosis == "G70.00" or "G70.00" in (order.additional_diagnoses or []) for order in orders))

    def test_export_to_csv(self):
        csv_content = export_to_csv()
        self.assertIn("Order ID", csv_content)
        self.assertIn("123456", csv_content)
        self.assertIn("John", csv_content)
        self.assertIn("Doe", csv_content)

    def test_export_to_csv_with_care_plan(self):
        csv_content = export_to_csv()
        self.assertIn("Yes", csv_content)
        self.assertIn("No", csv_content)

    def test_export_to_excel(self):
        excel_content = export_to_excel()
        self.assertIsInstance(excel_content, bytes)
        self.assertGreater(len(excel_content), 0)

    def test_get_export_filename_no_dates(self):
        filename = get_export_filename("csv")
        self.assertIn("care_plans_export", filename)
        self.assertTrue(filename.endswith(".csv"))

    def test_get_export_filename_with_dates(self):
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 31)
        filename = get_export_filename("csv", start_date, end_date)
        self.assertIn("20250101_to_20250131", filename)
        self.assertTrue(filename.endswith(".csv"))

    def test_get_export_filename_excel(self):
        filename = get_export_filename("xlsx")
        self.assertTrue(filename.endswith(".xlsx"))


class ViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456"
        )
        self.provider = Provider.objects.create(
            name="Dr. Alice Johnson",
            npi="1234567890"
        )

    def test_validate_order_endpoint_success(self):
        data = {
            "patient_first_name": "Jane",
            "patient_last_name": "Smith",
            "patient_mrn": "999999",
            "provider_name": "Dr. New Provider",
            "provider_npi": "9999999999",
            "primary_diagnosis": "G70.00",
            "medication_name": "Test Medication",
            "patient_records": "Test records"
        }
        response = self.client.post(
            '/api/orders/validate',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['valid'])

    def test_validate_order_endpoint_with_duplicates(self):
        data = {
            "patient_first_name": "John",
            "patient_last_name": "Doe",
            "patient_mrn": "123456",
            "provider_name": "Dr. Alice Johnson",
            "provider_npi": "1234567890",
            "primary_diagnosis": "G70.00",
            "medication_name": "Test Medication",
            "patient_records": "Test records"
        }
        response = self.client.post(
            '/api/orders/validate',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertGreater(len(response_data['warnings']), 0)

    def test_validate_order_endpoint_invalid_data(self):
        data = {
            "patient_first_name": "",
            "patient_mrn": "12345"
        }
        response = self.client.post(
            '/api/orders/validate',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_export_orders_csv(self):
        Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="G70.00",
            medication_name="Test Medication",
            patient_records="Test records"
        )
        response = self.client.get('/api/orders/export?format=csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_export_orders_excel(self):
        Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="G70.00",
            medication_name="Test Medication",
            patient_records="Test records"
        )
        response = self.client.get('/api/orders/export?format=xlsx')
        self.assertEqual(response.status_code, 200)
        self.assertIn('spreadsheetml.sheet', response['Content-Type'])
        self.assertIn('attachment', response['Content-Disposition'])

    def test_export_orders_invalid_format(self):
        response = self.client.get('/api/orders/export?format=invalid')
        self.assertEqual(response.status_code, 400)

    def test_export_orders_with_date_filter(self):
        Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="G70.00",
            medication_name="Test Medication",
            patient_records="Test records"
        )
        start_date = (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        response = self.client.get(f'/api/orders/export?format=csv&start_date={start_date}&end_date={end_date}')
        self.assertEqual(response.status_code, 200)

    def test_export_orders_invalid_date_format(self):
        response = self.client.get('/api/orders/export?format=csv&start_date=invalid')
        self.assertEqual(response.status_code, 400)

    def test_export_stats(self):
        Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="G70.00",
            medication_name="Test Medication",
            patient_records="Test records",
            care_plan="Test care plan"
        )
        response = self.client.get('/api/orders/export/stats')
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['total_orders'], 1)
        self.assertEqual(response_data['care_plans_generated'], 1)

    def test_export_stats_with_filters(self):
        Order.objects.create(
            patient=self.patient,
            provider=self.provider,
            primary_diagnosis="G70.00",
            medication_name="Test Medication",
            patient_records="Test records"
        )
        start_date = (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        response = self.client.get(f'/api/orders/export/stats?start_date={start_date}')
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['total_orders'], 1)
