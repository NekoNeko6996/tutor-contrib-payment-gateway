from setuptools import setup, find_packages

setup(
    name="payment_gateway_api",
    version="0.1.1",
    description="API for payment gateway integration (Open edX)",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    entry_points={
        # Dùng plugin API mới
        "openedx.plugin.app": [
            "payment_gateway_api = payment_gateway_api.apps:PaymentGatewayAPIConfig",
        ],
    },
)
