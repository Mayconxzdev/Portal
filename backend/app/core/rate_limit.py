from time import monotonic

from fastapi import HTTPException, Request, status

from app.core.config import settings


class LoginRateLimiter:
    def __init__(self) -> None:
        self._failures: dict[str, list[float]] = {}

    def _key(self, request: Request, username: str) -> str:
        client_host = request.client.host if request.client else "unknown"
        return f"{client_host}:{username.lower().strip()}"

    def assert_allowed(self, request: Request, username: str) -> None:
        key = self._key(request, username)
        now = monotonic()
        window_start = now - settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
        failures = [entry for entry in self._failures.get(key, []) if entry >= window_start]
        self._failures[key] = failures

        if len(failures) >= settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas tentativas de login. Aguarde alguns minutos e tente novamente.",
            )

    def record_failure(self, request: Request, username: str) -> None:
        key = self._key(request, username)
        now = monotonic()
        window_start = now - settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
        failures = [entry for entry in self._failures.get(key, []) if entry >= window_start]
        failures.append(now)
        self._failures[key] = failures

    def clear(self, request: Request, username: str) -> None:
        self._failures.pop(self._key(request, username), None)


login_rate_limiter = LoginRateLimiter()
