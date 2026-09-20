from django.apps import AppConfig


class BottleneckDetectionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bottleneck_detection"
    label = "bottleneck_detection"
    verbose_name = "FlowMind Bottleneck Detection"