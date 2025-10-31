from setuptools import setup, find_packages

setup(
    name="payment_gateway_api",
    version="0.1.0",
    description="API to expose course price/modes for payment gateway",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    entry_points={
        # Khai báo djangoapp cho LMS
        "lms.djangoapp": [
            "payment_gateway_api = payment_gateway_api.apps:PaymentGatewayAPIConfig",
        ],
    },
)
