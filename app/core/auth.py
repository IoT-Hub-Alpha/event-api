from iot_auth.django import JWTAuthMiddleware


class PublicPathJWTAuthMiddleware:
    PUBLIC_PATH_PREFIXES = (
        "/health/",
        "/ready/",
        "/admin/",
        "/static/",
        "/favicon.ico",
    )

    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_middleware = JWTAuthMiddleware(get_response)

    def __call__(self, request):
        if request.path.startswith(self.PUBLIC_PATH_PREFIXES):
            request.auth = None  # type: ignore[attr-defined]
            request._is_internal_request = False  # type: ignore[attr-defined]
            return self.get_response(request)

        return self.jwt_middleware(request)
