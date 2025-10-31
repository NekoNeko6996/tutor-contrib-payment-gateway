# payment_gateway_api/payment_gateway_api/apps.py
from django.apps import AppConfig
from edx_django_utils.plugins import PluginURLs
from openedx.core.djangoapps.plugins.constants import ProjectType

class PaymentGatewayAPIConfig(AppConfig):
    name = "payment_gateway_api"
    label = "payment_gateway_api"
    verbose_name = "Payment Gateway API"

    plugin_app = {
        PluginURLs.CONFIG: {
            ProjectType.LMS: {
                PluginURLs.NAMESPACE: "payment_gateway_api",
                PluginURLs.REGEX: r"^payment-gateway/",
                PluginURLs.RELATIVE_PATH: "urls",
            }
        }
    }
