"""
Masjid Connect baseline FastAPI application.

A Security-First microservices baseline application demonstrating:
- Pydantic model validation for all inputs
- Structured JSON logging with correlation IDs
- Standardized error responses with no information leakage
- Middleware for cross-cutting concerns (correlation IDs, security headers)
- API versioning (/api/v1/)
- Full OpenAPI documentation

Constitutional Principles:
1. Security-First: All inputs validated, no sensitive data in errors
2. Microservices Architecture: Async design, correlation IDs for tracing
3. Full Documentation: Docstrings, OpenAPI, Architecture Decision Records (ADRs)
"""

__version__ = "1.0.0"
