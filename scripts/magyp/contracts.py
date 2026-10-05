"""Contratos reutilizables sin implementar adquisición SIO/MCBA."""
from dataclasses import asdict, dataclass
from typing import Protocol


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    classification: str
    record_count: int = 0
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class RawManifest:
    source: str
    requested_date: str
    captured_at_utc: str
    capture_id: str
    url: str
    origin_url: str
    method: str
    public_parameters: dict
    status: int | None
    content_type: str
    encoding: str
    size_bytes: int
    sha256: str
    parser_version: str
    schema_version: str
    response_file: str | None
    validation: ValidationResult
    calendar: dict

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class PublishResult:
    published: bool
    changed: bool
    record_count: int
    path: str
    reason: str


class SourceFetcher(Protocol):
    def fetch(self, requested_date: str) -> RawManifest: ...


class Normalizer(Protocol):
    def normalize(self) -> ValidationResult: ...
