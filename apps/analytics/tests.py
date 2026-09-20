from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from apps.datasets.models import Dataset

from .services.duration import (
    AnalyticsError,
    DurationAnalytics,
)
from .services.pipeline import AnalyticsPipeline


class DurationAnalyticsTests(SimpleTestCase):

    def test_duration_statistics_are_calculated(self):
        dataframe = pd.DataFrame(
            [
                {
                    "step_name": "Verification",
                    "duration_minutes": 10,
                },
                {
                    "step_name": "Verification",
                    "duration_minutes": 20,
                },
                {
                    "step_name": "Packing",
                    "duration_minutes": 8,
                },
                {
                    "step_name": "Packing",
                    "duration_minutes": 12,
                },
            ]
        )

        result = DurationAnalytics(
            dataframe
        ).calculate()

        verification = result[
            result["step_name"] == "Verification"
        ].iloc[0]

        self.assertEqual(
            verification["event_count"],
            2,
        )

        self.assertEqual(
            verification["average_duration"],
            15.0,
        )

        self.assertEqual(
            verification["median_duration"],
            15.0,
        )

        self.assertEqual(
            verification["minimum_duration"],
            10.0,
        )

        self.assertEqual(
            verification["maximum_duration"],
            20.0,
        )

        self.assertEqual(
            verification["total_duration"],
            30.0,
        )

    def test_steps_are_sorted_by_average_duration(self):
        dataframe = pd.DataFrame(
            [
                {
                    "step_name": "Packing",
                    "duration_minutes": 5,
                },
                {
                    "step_name": "Verification",
                    "duration_minutes": 15,
                },
                {
                    "step_name": "Shipping",
                    "duration_minutes": 10,
                },
            ]
        )

        result = DurationAnalytics(
            dataframe
        ).calculate()

        self.assertEqual(
            result.iloc[0]["step_name"],
            "Verification",
        )

        self.assertEqual(
            result.iloc[1]["step_name"],
            "Shipping",
        )

        self.assertEqual(
            result.iloc[2]["step_name"],
            "Packing",
        )

    def test_missing_columns_are_rejected(self):
        dataframe = pd.DataFrame(
            {
                "step_name": [
                    "Verification",
                ],
            }
        )

        with self.assertRaises(
            AnalyticsError
        ):
            DurationAnalytics(
                dataframe
            ).calculate()

    def test_negative_durations_are_removed(self):
        dataframe = pd.DataFrame(
            [
                {
                    "step_name": "Verification",
                    "duration_minutes": -5,
                },
                {
                    "step_name": "Verification",
                    "duration_minutes": 10,
                },
            ]
        )

        result = DurationAnalytics(
            dataframe
        ).calculate()

        self.assertEqual(
            result.iloc[0]["average_duration"],
            10.0,
        )

    def test_invalid_dataframe_is_rejected(self):
        with self.assertRaises(
            AnalyticsError
        ):
            DurationAnalytics(
                "not a dataframe"
            ).calculate()


class AnalyticsPipelineTests(SimpleTestCase):

    def test_dataset_runs_through_complete_pipeline(self):
        csv_content = (
            "Order ID,Step Name,Duration (Minutes),Status\n"
            "ORD-001,Verification,10,completed\n"
            "ORD-001,Verification,20,completed\n"
            "ORD-001,Packing,8,completed\n"
            "ORD-002,Packing,12,completed\n"
        )

        uploaded_file = SimpleUploadedFile(
            "orders.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        dataset = Dataset(
            name="Pipeline Test Dataset",
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
                result = AnalyticsPipeline(
                    dataset
                ).run()

        preprocessing = result[
            "preprocessing"
        ]

        analytics = result[
            "duration_analytics"
        ]

        self.assertEqual(
            preprocessing["original_rows"],
            4,
        )

        self.assertEqual(
            preprocessing["cleaned_rows"],
            4,
        )

        self.assertEqual(
            len(analytics),
            2,
        )

        verification = analytics[
            analytics["step_name"] == "Verification"
        ].iloc[0]

        self.assertEqual(
            verification["average_duration"],
            15.0,
        )

        self.assertEqual(
            verification["event_count"],
            2,
        )

        packing = analytics[
            analytics["step_name"] == "Packing"
        ].iloc[0]

        self.assertEqual(
            packing["average_duration"],
            10.0,
        )

        self.assertEqual(
            packing["event_count"],
            2,
        )