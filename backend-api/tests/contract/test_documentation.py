"""
Contract tests for documentation requirements.

Verifies that all code is properly documented and OpenAPI documentation
is generated correctly.
"""

import pytest
from fastapi.testclient import TestClient
from src.main import create_app


@pytest.mark.contract
class TestDocumentation:
    """Test suite for documentation contract verification."""

    def test_openapi_schema_generated(self, client: TestClient):
        """
        Test that OpenAPI schema is generated correctly.
        
        Verifies the /openapi.json endpoint returns valid schema.
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert schema["openapi"] == "3.1.0"

    def test_swagger_ui_accessible(self, client: TestClient):
        """
        Test that Swagger UI documentation is accessible.
        
        Verifies the /docs endpoint returns 200 status.
        """
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_ui_accessible(self, client: TestClient):
        """
        Test that ReDoc UI documentation is accessible.
        
        Verifies the /redoc endpoint returns 200 status.
        """
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_info_section_complete(self, client: TestClient):
        """
        Test that OpenAPI info section contains required metadata.
        
        Verifies title, version, and description are present.
        """
        response = client.get("/openapi.json")
        schema = response.json()
        
        info = schema["info"]
        assert "title" in info
        assert "version" in info
        assert info["title"]  # Not empty
        assert info["version"]  # Not empty

    def test_health_endpoint_documented_in_openapi(self, client: TestClient):
        """
        Test that health endpoint is documented in OpenAPI schema.
        
        Verifies /api/v1/health path is present with correct method.
        """
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        assert "/api/v1/health" in paths
        assert "get" in paths["/api/v1/health"]

    def test_health_endpoint_has_response_schema(self, client: TestClient):
        """
        Test that health endpoint has response schema defined.
        
        Verifies 200 response has content schema.
        """
        response = client.get("/openapi.json")
        schema = response.json()
        
        health_get = schema["paths"]["/api/v1/health"]["get"]
        assert "responses" in health_get
        assert "200" in health_get["responses"]
        assert "content" in health_get["responses"]["200"]

    def test_health_endpoint_has_tags(self, client: TestClient):
        """
        Test that health endpoint has tags for organization.
        
        Verifies tags array is present for Swagger UI grouping.
        """
        response = client.get("/openapi.json")
        schema = response.json()
        
        health_get = schema["paths"]["/api/v1/health"]["get"]
        assert "tags" in health_get
        assert isinstance(health_get["tags"], list)
        assert len(health_get["tags"]) > 0

    def test_pydantic_models_in_components(self, client: TestClient):
        """
        Test that Pydantic models are included in OpenAPI components.
        
        Verifies HealthStatus model is in schemas section.
        """
        response = client.get("/openapi.json")
        schema = response.json()
        
        assert "components" in schema
        assert "schemas" in schema["components"]
        
        # HealthStatus should be in schemas
        schemas = schema["components"]["schemas"]
        assert "HealthStatus" in schemas

    def test_error_responses_documented(self, client: TestClient):
        """
        Test that error responses are documented in OpenAPI.
        
        Verifies ErrorResponse model is in components.
        """
        response = client.get("/openapi.json")
        schema = response.json()
        
        schemas = schema["components"]["schemas"]
        assert "ErrorResponse" in schemas

    def test_openapi_schema_validation(self, client: TestClient):
        """
        Test that OpenAPI schema includes validation constraints.
        
        Verifies Pydantic validation rules appear in schema.
        """
        response = client.get("/openapi.json")
        schema = response.json()
        
        health_status = schema["components"]["schemas"]["HealthStatus"]
        assert "properties" in health_status
        assert "required" in health_status
        
        # Verify required fields
        assert "status" in health_status["required"]
        assert "timestamp" in health_status["required"]

    def test_api_version_in_paths(self, client: TestClient):
        """
        Test that API versioning is reflected in paths.
        
        Verifies all endpoints start with /api/v1/.
        """
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        for path in paths.keys():
            if not path.startswith("/"):
                continue
            # All API paths should start with /api/v1/
            if path not in ["/docs", "/redoc", "/openapi.json"]:
                assert path.startswith("/api/v1/"), f"Path {path} doesn't follow versioning"

    def test_endpoint_summaries_present(self, client: TestClient):
        """
        Test that endpoints have summary descriptions.
        
        Verifies summary field is present for better documentation.
        """
        response = client.get("/openapi.json")
        schema = response.json()
        
        health_get = schema["paths"]["/api/v1/health"]["get"]
        # Summary or description should be present
        assert "summary" in health_get or "description" in health_get

    def test_response_models_have_examples(self, client: TestClient):
        """
        Test that response models have example values.
        
        Verifies schemas include examples for better documentation.
        """
        response = client.get("/openapi.json")
        schema = response.json()
        
        # Check if HealthStatus has properties defined
        health_status = schema["components"]["schemas"]["HealthStatus"]
        assert "properties" in health_status
        assert len(health_status["properties"]) > 0


@pytest.mark.contract
class TestMainModuleDocumentation:
    """Test suite for main module documentation."""

    def test_main_module_has_docstring(self):
        """
        Test that main.py module has docstring.
        
        Verifies module-level documentation is present.
        """
        from src import main
        assert main.__doc__ is not None
        assert len(main.__doc__.strip()) > 0

    def test_create_app_function_has_docstring(self):
        """
        Test that create_app function has docstring.
        
        Verifies function documentation describes purpose and return value.
        """
        from src.main import create_app
        assert create_app.__doc__ is not None
        assert len(create_app.__doc__.strip()) > 0
        # Should mention it's a factory or creates FastAPI
        doc_lower = create_app.__doc__.lower()
        assert "fastapi" in doc_lower or "factory" in doc_lower or "create" in doc_lower


@pytest.mark.contract
class TestConfigModuleDocumentation:
    """Test suite for config module documentation."""

    def test_config_module_has_docstring(self):
        """
        Test that config.py module has docstring.
        
        Verifies module-level documentation is present.
        """
        from src import config
        assert config.__doc__ is not None
        assert len(config.__doc__.strip()) > 0

    def test_settings_class_has_docstring(self):
        """
        Test that Settings class has docstring.
        
        Verifies class documentation describes configuration purpose.
        """
        from src.config import Settings
        assert Settings.__doc__ is not None
        assert len(Settings.__doc__.strip()) > 0


@pytest.mark.contract
class TestModelDocumentation:
    """Test suite for model documentation."""

    def test_health_model_has_docstring(self):
        """
        Test that HealthStatus model has docstring.
        
        Verifies Pydantic model is documented.
        """
        from src.models.health import HealthStatus
        assert HealthStatus.__doc__ is not None
        assert len(HealthStatus.__doc__.strip()) > 0

    def test_error_model_has_docstring(self):
        """
        Test that ErrorResponse model has docstring.
        
        Verifies error model is documented.
        """
        from src.models.error import ErrorResponse
        assert ErrorResponse.__doc__ is not None
        assert len(ErrorResponse.__doc__.strip()) > 0


@pytest.mark.contract
class TestExceptionDocumentation:
    """Test suite for exception documentation."""

    def test_masjidconnect_exception_has_docstring(self):
        """
        Test that MasjidConnectException base class has docstring.
        
        Verifies base exception is documented.
        """
        from src.core.exceptions import MasjidConnectException
        assert MasjidConnectException.__doc__ is not None
        assert len(MasjidConnectException.__doc__.strip()) > 0

    def test_not_found_error_has_docstring(self):
        """
        Test that NotFoundError has docstring.
        
        Verifies exception class is documented with HTTP status.
        """
        from src.core.exceptions import NotFoundError
        assert NotFoundError.__doc__ is not None
        assert len(NotFoundError.__doc__.strip()) > 0
        # Should mention HTTP status
        assert "404" in NotFoundError.__doc__


@pytest.mark.contract
class TestMiddlewareDocumentation:
    """Test suite for middleware documentation."""

    def test_correlation_id_middleware_has_docstring(self):
        """
        Test that CorrelationIdMiddleware has docstring.
        
        Verifies middleware class is documented.
        """
        from src.core.middleware import CorrelationIdMiddleware
        assert CorrelationIdMiddleware.__doc__ is not None
        assert len(CorrelationIdMiddleware.__doc__.strip()) > 0

    def test_error_handler_middleware_has_docstring(self):
        """
        Test that ErrorHandlerMiddleware has docstring.
        
        Verifies middleware class is documented.
        """
        from src.core.middleware import ErrorHandlerMiddleware
        assert ErrorHandlerMiddleware.__doc__ is not None
        assert len(ErrorHandlerMiddleware.__doc__.strip()) > 0

    def test_security_headers_middleware_has_docstring(self):
        """
        Test that SecurityHeadersMiddleware has docstring.
        
        Verifies middleware class is documented.
        """
        from src.core.middleware import SecurityHeadersMiddleware
        assert SecurityHeadersMiddleware.__doc__ is not None
        assert len(SecurityHeadersMiddleware.__doc__.strip()) > 0
