def plugin_settings(settings):
    tokens = getattr(settings, "ENV_TOKENS", {})
    settings.PAYMENT_NODE_CREATE_URL = tokens.get(
        "PAYMENT_NODE_CREATE_URL", "http://localhost:3000/api/payments/create"
    )
    settings.PAYMENT_SHARED_SECRET = tokens.get("PAYMENT_SHARED_SECRET", "CHANGE_ME")
