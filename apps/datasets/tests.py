from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from django.test import SimpleTestCase

from .services.validator import (
    DatasetValidationError,
    DatasetValidator,
)


class DatasetValidatorTests(SimpleTestCase):

    def test_valid_csv_is_analyzed(self):
        dataframe = pd.DataFrame(
            [
                {
                    "order_id": "ORD-001",
                    "step_name": "Verification",
                    "duration_minutes": 12.5,
                    "status": "completed",
                },
                {
                    "order_id": "ORD-002",
                    "step_name": "Packing",
                    "duration_minutes": 8.0,
                    "status": "completed",
                },
                {
                    "order_id": "ORD-003",
                    "step_name": "Shipping",
                    "duration_minutes": 10.0,
                    "status": "completed",
                },
            ]
        )

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "orders.csv"

            dataframe.to_csv(
                file_path,
                index=False,
            )

            result = DatasetValidator(file_path).validate()

        self.assertEqual(result["row_count"], 3)
        self.assertEqual(result["column_count"], 4)
        self.assertEqual(result["missing_cells"], 0)
        self.assertEqual(result["duplicate_rows"], 0)
        self.assertEqual(result["quality_score"], 100.0)

    def test_missing_values_are_detected(self):
        dataframe = pd.DataFrame(
            [
                {
                    "order_id": "ORD-001",
                    "step_name": "Verification",
                    "duration_minutes": 12.5,
                },
                {
                    "order_id": "ORD-002",
                    "step_name": None,
                    "duration_minutes": 8.0,
                },
            ]
        )

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "orders.csv"

            dataframe.to_csv(
                file_path,
                index=False,
            )

            result = DatasetValidator(file_path).validate()

        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["column_count"], 3)
        self.assertEqual(result["missing_cells"], 1)
        self.assertLess(result["quality_score"], 100.0)

    def test_duplicate_rows_are_detected(self):
        dataframe = pd.DataFrame(
            [
                {
                    "order_id": "ORD-001",
                    "step_name": "Verification",
                    "duration_minutes": 12.5,
                },
                {
                    "order_id": "ORD-001",
                    "step_name": "Verification",
                    "duration_minutes": 12.5,
                },
            ]
        )

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "orders.csv"

            dataframe.to_csv(
                file_path,
                index=False,
            )

            result = DatasetValidator(file_path).validate()

        self.assertEqual(result["duplicate_rows"], 1)

    def test_unsupported_file_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "orders.txt"
            file_path.write_text("hello")

            with self.assertRaises(DatasetValidationError):
                DatasetValidator(file_path).validate()