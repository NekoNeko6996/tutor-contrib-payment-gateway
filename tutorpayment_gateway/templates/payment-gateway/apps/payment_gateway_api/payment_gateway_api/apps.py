from django.apps import AppConfig
from edx_django_utils.plugins import PluginURLs, PluginSettings
from openedx.core.djangoapps.plugins.constants import ProjectType

class PaymentGatewayAPIConfig(AppConfig):
    name = "payment_gateway_api"
    label = "payment_gateway_api"
    verbose_name = "Payment Gateway API"

    plugin_app = {
        # URLs cho LMS
        PluginURLs.CONFIG: {
            ProjectType.LMS: {
                PluginURLs.NAMESPACE: "payment_gateway_api",
                PluginURLs.REGEX: r"^payment-gateway/",
                PluginURLs.RELATIVE_PATH: "urls",
            }
        },
        # Nạp settings từ ENV_TOKENS → settings.PAYMENT_*
        PluginSettings.CONFIG: {
            ProjectType.LMS: {
                "common": {"relative_path": "settings/common.py"},
            },
        },
    }
