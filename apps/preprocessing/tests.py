from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from apps.datasets.models import Dataset

from .services.cleaner import (
    DatasetPreprocessor,
    PreprocessingError,
)
from .services.dataset_preprocessing import (
    DatasetPreprocessingService,
)


class DatasetPreprocessorTests(SimpleTestCase):

    def test_column_names_are_normalized(self):
        dataframe = pd.DataFrame(
            {
                "Order ID": ["ORD-001"],
                "Step Name": ["Verification"],
                "Duration (Minutes)": [12.5],
            }
        )

        result = DatasetPreprocessor(
            dataframe
        ).clean()

        self.assertEqual(
            list(result.columns),
            [
                "order_id",
                "step_name",
                "duration_minutes",
            ],
        )

    def test_empty_rows_are_removed(self):
        dataframe = pd.DataFrame(
            [
                {
                    "order_id": "ORD-001",
                    "duration": 10,
                },
                {
                    "order_id": None,
                    "duration": None,
                },
            ]
        )

        result = DatasetPreprocessor(
            dataframe
        ).clean()

        self.assertEqual(
            len(result),
            1,
        )

    def test_duplicate_rows_are_removed(self):
        dataframe = pd.DataFrame(
            [
                {
                    "order_id": "ORD-001",
                    "duration": 10,
                },
                {
                    "order_id": "ORD-001",
                    "duration": 10,
                },
            ]
        )

        result = DatasetPreprocessor(
            dataframe
        ).clean()

        self.assertEqual(
            len(result),
            1,
        )

    def test_missing_values_are_handled(self):
        dataframe = pd.DataFrame(
            [
                {
                    "step": "Verification",
                    "duration": 10.0,
                },
                {
                    "step": None,
                    "duration": None,
                },
                {
                    "step": "Packing",
                    "duration": 20.0,
                },
            ]
        )

        result = DatasetPreprocessor(
            dataframe
        ).clean()

        self.assertFalse(
            result["step"].isna().any()
        )

        self.assertFalse(
            result["duration"].isna().any()
        )

    def test_numeric_strings_are_converted(self):
        dataframe = pd.DataFrame(
            {
                "duration": [
                    "10.5",
                    "12.0",
                    "15.5",
                ]
            }
        )

        result = DatasetPreprocessor(
            dataframe
        ).clean()

        self.assertTrue(
            pd.api.types.is_numeric_dtype(
                result["duration"]
            )
        )

    def test_invalid_input_is_rejected(self):
        with self.assertRaises(
            PreprocessingError
        ):
            DatasetPreprocessor(
                "not a dataframe"
            )


class DatasetPreprocessingServiceTests(SimpleTestCase):

    def test_dataset_csv_is_loaded_and_processed(self):
        csv_content = (
            "Order ID,Step Name,Duration (Minutes)\n"
            "ORD-001,Verification,12.5\n"
            "ORD-001,Verification,12.5\n"
            "ORD-002,Packing,8.0\n"
        )

        uploaded_file = SimpleUploadedFile(
            "orders.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        dataset = Dataset(
            name="Test Dataset",
            file=uploaded_file,
        )

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "orders.csv"

            file_path.write_bytes(
                csv_content.encode("utf-8")
            )

            with patch.object(
                type(dataset.file),
                "path",
                new_callable=lambda: property(
                    lambda self: str(file_path)
                ),
            ):
                result = DatasetPreprocessingService(
                    dataset
                ).process()

        self.assertEqual(
            result["original_rows"],
            3,
        )

        self.assertEqual(
            result["cleaned_rows"],
            2,
        )

        self.assertEqual(
            result["original_columns"],
            3,
        )

        self.assertEqual(
            result["cleaned_columns"],
            3,
        )

        self.assertEqual(
            result["rows_removed"],
            1,
        )

        self.assertEqual(
            list(result["dataframe"].columns),
            [
                "order_id",
                "step_name",
                "duration_minutes",
            ],
        )

    def test_unsupported_dataset_format_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "orders.txt",
            b"hello",
            content_type="text/plain",
        )

        dataset = Dataset(
            name="Invalid Dataset",
            file=uploaded_file,
        )

        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "orders.txt"

            file_path.write_text("hello")

            with patch.object(
                type(dataset.file),
                "path",
                new_callable=lambda: property(
                    lambda self: str(file_path)
                ),
            ):
                with self.assertRaises(
                    PreprocessingError
                ):
                    DatasetPreprocessingService(
                        dataset
                    ).process()