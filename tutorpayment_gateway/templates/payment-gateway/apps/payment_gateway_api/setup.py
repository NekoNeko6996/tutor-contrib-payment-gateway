# payment_gateway_api/setup.py
from setuptools import setup, find_packages

setup(
    name="payment_gateway_api",
    version="0.1.0",
    description="API for payment gateway integration (Open edX)",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    entry_points={
        "lms.djangoapp": [
            "payment_gateway_api = payment_gateway_api.apps:PaymentGatewayAPIConfig",
        ],
        # Tùy chọn nếu muốn dùng ở CMS/Studio
        "cms.djangoapp": [
            "payment_gateway_api = payment_gateway_api.apps:PaymentGatewayAPIConfig",
        ],
    },
)
