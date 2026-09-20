import re

import pandas as pd


class PreprocessingError(Exception):
    """Raised when preprocessing cannot be completed."""


class DatasetPreprocessor:
    """
    Cleans a pandas DataFrame for downstream analytics.
    """

    def __init__(self, dataframe):
        if not isinstance(dataframe, pd.DataFrame):
            raise PreprocessingError(
                "Input must be a pandas DataFrame."
            )

        self.dataframe = dataframe.copy()

    def clean(self):
        dataframe = self.dataframe.copy()

        dataframe = self._normalize_column_names(dataframe)

        dataframe = self._remove_empty_rows(dataframe)

        dataframe = self._remove_duplicate_rows(dataframe)

        dataframe = self._clean_missing_values(dataframe)

        dataframe = self._clean_numeric_values(dataframe)

        dataframe = dataframe.reset_index(drop=True)

        return dataframe

    @staticmethod
    def _normalize_column_names(dataframe):
        dataframe = dataframe.copy()

        normalized_columns = []

        for column in dataframe.columns:
            column_name = str(column).strip().lower()

            column_name = re.sub(
                r"[^a-z0-9]+",
                "_",
                column_name,
            )

            column_name = column_name.strip("_")

            normalized_columns.append(column_name)

        dataframe.columns = normalized_columns

        return dataframe

    @staticmethod
    def _remove_empty_rows(dataframe):
        dataframe = dataframe.copy()

        dataframe = dataframe.dropna(
            how="all"
        )

        return dataframe

    @staticmethod
    def _remove_duplicate_rows(dataframe):
        dataframe = dataframe.copy()

        dataframe = dataframe.drop_duplicates()

        return dataframe

    @staticmethod
    def _clean_missing_values(dataframe):
        dataframe = dataframe.copy()

        for column in dataframe.columns:
            if pd.api.types.is_numeric_dtype(
                dataframe[column]
            ):
                median_value = dataframe[column].median()

                if pd.notna(median_value):
                    dataframe[column] = dataframe[column].fillna(
                        median_value
                    )

            else:
                dataframe[column] = dataframe[column].fillna(
                    "Unknown"
                )

        return dataframe

    @staticmethod
    def _clean_numeric_values(dataframe):
        dataframe = dataframe.copy()

        for column in dataframe.columns:
            if dataframe[column].dtype == "object":
                converted = pd.to_numeric(
                    dataframe[column],
                    errors="coerce",
                )

                non_null_original = dataframe[column].notna().sum()

                non_null_converted = converted.notna().sum()

                if (
                    non_null_original > 0
                    and non_null_converted
                    == non_null_original
                ):
                    dataframe[column] = converted

        return dataframe
    