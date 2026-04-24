from dataclasses import dataclass


@dataclass
class RequestContext:
    tenant_code: str | None = None
    client_id: int | None = None
    request_id: str | None = None


def build_request_context(*, tenant_code: str | None = None, client_id: int | None = None, request_id: str | None = None) -> RequestContext:
    return RequestContext(
        tenant_code=tenant_code,
        client_id=client_id,
        request_id=request_id,
    )

