from django.apps import AppConfig


class AnomalyDetectionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.anomaly_detection"
    label = "anomaly_detection"
    verbose_name = "FlowMind Anomaly Detection"