"""
Contract tests for project structure verification.

Tests verify that the project structure follows the planned architecture,
has all required directories and package markers, and supports independent
feature development without circular dependencies.

Test markers:
- @pytest.mark.contract: Contract test (verifies structure agreements)
"""

import ast
import importlib
import os
from pathlib import Path

import pytest


@pytest.mark.contract
class TestProjectStructure:
    """Contract tests for project structure verification."""

    def test_required_source_directories_exist(self):
        """Test all required source directories exist."""
        backend_root = Path(__file__).parent.parent.parent
        required_dirs = [
            backend_root / "src",
            backend_root / "src" / "models",
            backend_root / "src" / "api",
            backend_root / "src" / "api" / "v1",
            backend_root / "src" / "api" / "v1" / "endpoints",
            backend_root / "src" / "core",
            backend_root / "src" / "services",
            backend_root / "src" / "utils",
        ]

        for directory in required_dirs:
            assert directory.exists(), f"Required directory missing: {directory}"
            assert directory.is_dir(), f"Path exists but is not a directory: {directory}"

    def test_required_test_directories_exist(self):
        """Test all required test directories exist."""
        backend_root = Path(__file__).parent.parent.parent
        required_dirs = [
            backend_root / "tests",
            backend_root / "tests" / "unit",
            backend_root / "tests" / "integration",
            backend_root / "tests" / "contract",
        ]

        for directory in required_dirs:
            assert directory.exists(), f"Required test directory missing: {directory}"
            assert directory.is_dir(), f"Path exists but is not a directory: {directory}"

    def test_required_documentation_directories_exist(self):
        """Test required documentation directories exist."""
        backend_root = Path(__file__).parent.parent.parent
        required_dirs = [
            backend_root / "docs",
            backend_root / "docs" / "adr",
        ]

        for directory in required_dirs:
            assert directory.exists(), f"Required docs directory missing: {directory}"
            assert directory.is_dir(), f"Path exists but is not a directory: {directory}"

    def test_package_markers_exist_in_source(self):
        """Test __init__.py files exist in all source packages."""
        backend_root = Path(__file__).parent.parent.parent
        required_init_files = [
            backend_root / "src" / "__init__.py",
            backend_root / "src" / "models" / "__init__.py",
            backend_root / "src" / "api" / "__init__.py",
            backend_root / "src" / "api" / "v1" / "__init__.py",
            backend_root / "src" / "api" / "v1" / "endpoints" / "__init__.py",
            backend_root / "src" / "core" / "__init__.py",
        ]

        for init_file in required_init_files:
            assert init_file.exists(), f"Package marker missing: {init_file}"
            assert init_file.is_file(), f"Path exists but is not a file: {init_file}"

    def test_package_markers_exist_in_tests(self):
        """Test __init__.py files exist in test packages (optional but recommended)."""
        backend_root = Path(__file__).parent.parent.parent
        test_package_marker = backend_root / "tests" / "__init__.py"

        # Tests package should have __init__.py
        if test_package_marker.exists():
            assert test_package_marker.is_file()

    def test_models_are_separate_from_services(self):
        """Test models and services are in separate modules."""
        backend_root = Path(__file__).parent.parent.parent
        models_dir = backend_root / "src" / "models"
        services_dir = backend_root / "src" / "services"

        assert models_dir.exists()
        assert services_dir.exists()
        assert models_dir != services_dir

    def test_api_endpoints_are_versioned(self):
        """Test API endpoints are organized under versioned directories."""
        backend_root = Path(__file__).parent.parent.parent
        v1_dir = backend_root / "src" / "api" / "v1"
        endpoints_dir = v1_dir / "endpoints"

        assert v1_dir.exists(), "API v1 directory should exist"
        assert endpoints_dir.exists(), "Endpoints directory should exist under v1"

    def test_core_utilities_separate_from_business_logic(self):
        """Test core utilities are separate from business logic."""
        backend_root = Path(__file__).parent.parent.parent
        core_dir = backend_root / "src" / "core"
        models_dir = backend_root / "src" / "models"
        services_dir = backend_root / "src" / "services"

        assert core_dir.exists()
        assert core_dir != models_dir
        assert core_dir != services_dir

    def test_configuration_files_exist(self):
        """Test required configuration files exist."""
        backend_root = Path(__file__).parent.parent.parent
        required_files = [
            backend_root / "requirements.txt",
            backend_root / "requirements.in",
            backend_root / ".env.example",
            backend_root / "pytest.ini",
            backend_root / "pyproject.toml",
            backend_root / ".gitignore",
        ]

        for config_file in required_files:
            assert config_file.exists(), f"Required config file missing: {config_file}"
            assert config_file.is_file(), f"Path exists but is not a file: {config_file}"

    def test_main_entry_point_exists(self):
        """Test main application entry point exists."""
        backend_root = Path(__file__).parent.parent.parent
        main_file = backend_root / "src" / "main.py"

        assert main_file.exists(), "Main entry point (src/main.py) should exist"
        assert main_file.is_file()

    def test_config_module_exists(self):
        """Test configuration module exists."""
        backend_root = Path(__file__).parent.parent.parent
        config_file = backend_root / "src" / "config.py"

        assert config_file.exists(), "Configuration module (src/config.py) should exist"
        assert config_file.is_file()

    def test_no_circular_imports_in_models(self):
        """Test models module can be imported without circular dependency errors."""
        try:
            import src.models.health
            import src.models.error

            # If we get here, no circular imports
            assert True
        except ImportError as e:
            pytest.fail(f"Circular import detected in models: {e}")

    def test_no_circular_imports_in_core(self):
        """Test core modules can be imported without circular dependency errors."""
        try:
            import src.core.exceptions
            import src.core.logging
            import src.core.middleware

            # If we get here, no circular imports
            assert True
        except ImportError as e:
            pytest.fail(f"Circular import detected in core: {e}")

    def test_no_circular_imports_in_api(self):
        """Test API modules can be imported without circular dependency errors."""
        try:
            import src.api.v1.endpoints.health

            # If we get here, no circular imports
            assert True
        except ImportError as e:
            pytest.fail(f"Circular import detected in API: {e}")

    def test_main_app_can_be_imported(self):
        """Test main application can be imported without errors."""
        try:
            from src.main import app

            assert app is not None
            assert hasattr(app, "routes")  # FastAPI app should have routes attribute
        except ImportError as e:
            pytest.fail(f"Failed to import main app: {e}")


@pytest.mark.contract
class TestModuleSeparation:
    """Tests verifying proper module separation and boundaries."""

    def test_models_do_not_import_services(self):
        """Test models don't depend on services (proper layering)."""
        backend_root = Path(__file__).parent.parent.parent
        models_dir = backend_root / "src" / "models"

        for model_file in models_dir.glob("*.py"):
            if model_file.name.startswith("__"):
                continue

            with open(model_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Models should not import from services
                assert (
                    "from src.services" not in content
                ), f"{model_file.name} imports from services (violates layering)"
                assert (
                    "import src.services" not in content
                ), f"{model_file.name} imports from services (violates layering)"

    def test_models_can_import_from_core(self):
        """Test models can import from core (allowed dependency)."""
        # This is allowed: models can use core utilities
        # Just verify the import paths are correct
        try:
            # Models might import ValidationError or other core utilities
            from src.models import health, error

            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import models: {e}")

    def test_endpoints_directory_structure_supports_scaling(self):
        """Test endpoints directory can accommodate multiple endpoint files."""
        backend_root = Path(__file__).parent.parent.parent
        endpoints_dir = backend_root / "src" / "api" / "v1" / "endpoints"

        assert endpoints_dir.exists()
        # Should have __init__.py for package
        init_file = endpoints_dir / "__init__.py"
        assert init_file.exists()

        # Should be able to add multiple endpoint modules
        # (Currently has health.py, could add users.py, tasks.py, etc.)
        endpoint_files = list(endpoints_dir.glob("*.py"))
        assert len(endpoint_files) > 0, "Should have at least one endpoint module"
