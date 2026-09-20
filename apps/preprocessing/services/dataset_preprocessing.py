from pathlib import Path

import pandas as pd

from apps.datasets.models import Dataset

from .cleaner import DatasetPreprocessor, PreprocessingError


class DatasetPreprocessingService:
    """
    Loads a FlowMind Dataset and applies preprocessing.
    """

    def __init__(self, dataset):
        if not isinstance(dataset, Dataset):
            raise PreprocessingError(
                "A valid Dataset instance is required."
            )

        self.dataset = dataset

    def process(self):
        if not self.dataset.file:
            raise PreprocessingError(
                "The dataset does not have an uploaded file."
            )

        file_path = Path(self.dataset.file.path)

        dataframe = self._load_dataframe(file_path)

        original_rows = len(dataframe)
        original_columns = len(dataframe.columns)

        cleaned_dataframe = DatasetPreprocessor(
            dataframe
        ).clean()

        return {
            "dataframe": cleaned_dataframe,
            "original_rows": original_rows,
            "cleaned_rows": len(cleaned_dataframe),
            "original_columns": original_columns,
            "cleaned_columns": len(cleaned_dataframe.columns),
            "rows_removed": (
                original_rows - len(cleaned_dataframe)
            ),
        }

    @staticmethod
    def _load_dataframe(file_path):
        extension = file_path.suffix.lower()

        try:
            if extension == ".csv":
                return pd.read_csv(file_path)

            if extension in {".xlsx", ".xls"}:
                return pd.read_excel(file_path)

        except Exception as exc:
            raise PreprocessingError(
                f"Unable to load dataset: {exc}"
            ) from exc

        raise PreprocessingError(
            "Unsupported dataset format."
        )