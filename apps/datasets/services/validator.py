from pathlib import Path

import pandas as pd


SUPPORTED_EXTENSIONS = {
    ".csv",
    ".xlsx",
    ".xls",
}


class DatasetValidationError(Exception):
    """Raised when a dataset cannot be read or validated."""


class DatasetValidator:
    """
    Reads a dataset file and calculates basic data-quality information.
    """

    def __init__(self, file_path):
        self.file_path = Path(file_path)

    def validate(self):
        dataframe = self._load_dataframe()

        row_count = len(dataframe)
        column_count = len(dataframe.columns)

        missing_cells = int(dataframe.isna().sum().sum())
        duplicate_rows = int(dataframe.duplicated().sum())

        total_cells = row_count * column_count

        if total_cells > 0:
            missing_percentage = (
                missing_cells / total_cells
            ) * 100
        else:
            missing_percentage = 100.0

        if row_count > 0:
            duplicate_percentage = (
                duplicate_rows / row_count
            ) * 100
        else:
            duplicate_percentage = 100.0

        quality_score = self._calculate_quality_score(
            missing_percentage=missing_percentage,
            duplicate_percentage=duplicate_percentage,
            row_count=row_count,
            column_count=column_count,
        )

        return {
            "row_count": row_count,
            "column_count": column_count,
            "columns": [
                {
                    "name": str(column),
                    "data_type": str(dataframe[column].dtype),
                    "missing_count": int(dataframe[column].isna().sum()),
                }
                for column in dataframe.columns
            ],
            "missing_cells": missing_cells,
            "missing_percentage": round(missing_percentage, 2),
            "duplicate_rows": duplicate_rows,
            "duplicate_percentage": round(duplicate_percentage, 2),
            "quality_score": quality_score,
        }

    def _load_dataframe(self):
        if not self.file_path.exists():
            raise DatasetValidationError(
                "The dataset file could not be found."
            )

        extension = self.file_path.suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            raise DatasetValidationError(
                "Unsupported dataset format. "
                "Please upload a CSV or Excel file."
            )

        try:
            if extension == ".csv":
                dataframe = pd.read_csv(self.file_path)

            elif extension in {".xlsx", ".xls"}:
                dataframe = pd.read_excel(self.file_path)

            else:
                raise DatasetValidationError(
                    "Unsupported dataset format."
                )

        except Exception as exc:
            raise DatasetValidationError(
                f"Unable to read the dataset: {exc}"
            ) from exc

        if dataframe.empty:
            raise DatasetValidationError(
                "The dataset contains no rows."
            )

        if len(dataframe.columns) == 0:
            raise DatasetValidationError(
                "The dataset contains no columns."
            )

        return dataframe

    @staticmethod
    def _calculate_quality_score(
        *,
        missing_percentage,
        duplicate_percentage,
        row_count,
        column_count,
    ):
        if row_count == 0 or column_count == 0:
            return 0.0

        missing_penalty = min(missing_percentage, 100)
        duplicate_penalty = min(duplicate_percentage, 100)

        score = (
            100
            - missing_penalty * 0.7
            - duplicate_penalty * 0.3
        )

        return round(max(0.0, min(100.0, score)), 2)