"""Tests for OpenAPI security scheme extraction and classification module."""

import tempfile
from pathlib import Path

from bootstrapper.generators.security import (
    SecurityScheme,
    SecuritySchemeType,
    classify_security_scheme,
    extract_security_schemes,
    generate_authentication_middleware,
    get_primary_security_scheme,
)


class TestExtractSecuritySchemes:
    """Tests for extract_security_schemes function."""

    def test_no_security_schemes(self):
        """Test that empty dict is returned when no security schemes exist."""
        spec = {
            "openapi": "3.1.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }

        result = extract_security_schemes(spec)

        assert result == {}

    def test_no_components_section(self):
        """Test that empty dict is returned when components section is missing."""
        spec = {
            "openapi": "3.1.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }

        result = extract_security_schemes(spec)

        assert result == {}

    def test_extract_bearer_scheme(self):
        """Test correct extraction of Bearer token definition."""
        spec = {
            "openapi": "3.1.0",
            "components": {
                "securitySchemes": {
                    "BearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    }
                }
            },
        }

        result = extract_security_schemes(spec)

        assert "BearerAuth" in result
        assert result["BearerAuth"]["type"] == "http"
        assert result["BearerAuth"]["scheme"] == "bearer"

    def test_extract_api_key_scheme(self):
        """Test correct extraction of API Key with name field."""
        spec = {
            "openapi": "3.1.0",
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
                }
            },
        }

        result = extract_security_schemes(spec)

        assert "ApiKeyAuth" in result
        assert result["ApiKeyAuth"]["type"] == "apiKey"
        assert result["ApiKeyAuth"]["in"] == "header"
        assert result["ApiKeyAuth"]["name"] == "X-API-Key"

    def test_extract_multiple_schemes(self):
        """Test that all schemes are returned (dict with multiple entries)."""
        spec = {
            "openapi": "3.1.0",
            "components": {
                "securitySchemes": {
                    "BearerAuth": {"type": "http", "scheme": "bearer"},
                    "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
                    "OAuth2": {
                        "type": "oauth2",
                        "flows": {
                            "authorizationCode": {
                                "authorizationUrl": "https://example.com/oauth/authorize",
                                "tokenUrl": "https://example.com/oauth/token",
                                "scopes": {"read": "Read access"},
                            }
                        },
                    },
                }
            },
        }

        result = extract_security_schemes(spec)

        assert len(result) == 3
        assert "BearerAuth" in result
        assert "ApiKeyAuth" in result
        assert "OAuth2" in result


class TestClassifySecurityScheme:
    """Tests for classify_security_scheme function."""

    def test_classify_bearer_token(self):
        """Test type='http', scheme='bearer' returns HTTP_BEARER."""
        scheme_def = {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}

        result = classify_security_scheme("BearerAuth", scheme_def)

        assert result is not None
        assert isinstance(result, SecurityScheme)
        assert result.name == "BearerAuth"
        assert result.scheme_type == SecuritySchemeType.HTTP_BEARER
        assert result.header_name is None

    def test_classify_api_key_header(self):
        """Test type='apiKey', in='header' returns API_KEY_HEADER with header name."""
        scheme_def = {"type": "apiKey", "in": "header", "name": "X-Custom-Key"}

        result = classify_security_scheme("ApiKeyAuth", scheme_def)

        assert result is not None
        assert isinstance(result, SecurityScheme)
        assert result.name == "ApiKeyAuth"
        assert result.scheme_type == SecuritySchemeType.API_KEY_HEADER
        assert result.header_name == "X-Custom-Key"

    def test_classify_api_key_query_unsupported(self):
        """Test type='apiKey', in='query' returns None (UNSUPPORTED)."""
        scheme_def = {"type": "apiKey", "in": "query", "name": "api_key"}

        result = classify_security_scheme("QueryKeyAuth", scheme_def)

        assert result is None

    def test_classify_oauth2_unsupported(self):
        """Test type='oauth2' returns None (UNSUPPORTED)."""
        scheme_def = {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "https://example.com/oauth/authorize",
                    "tokenUrl": "https://example.com/oauth/token",
                    "scopes": {"read": "Read access"},
                }
            },
        }

        result = classify_security_scheme("OAuth2Auth", scheme_def)

        assert result is None

    def test_classify_http_basic_unsupported(self):
        """Test type='http', scheme='basic' returns None (UNSUPPORTED)."""
        scheme_def = {"type": "http", "scheme": "basic"}

        result = classify_security_scheme("BasicAuth", scheme_def)

        assert result is None

    def test_classify_openid_unsupported(self):
        """Test type='openIdConnect' returns None (UNSUPPORTED)."""
        scheme_def = {
            "type": "openIdConnect",
            "openIdConnectUrl": "https://example.com/.well-known/openid-configuration",
        }

        result = classify_security_scheme("OpenIDAuth", scheme_def)

        assert result is None

    def test_classify_api_key_cookie_unsupported(self):
        """Test type='apiKey', in='cookie' returns None (UNSUPPORTED)."""
        scheme_def = {"type": "apiKey", "in": "cookie", "name": "session_token"}

        result = classify_security_scheme("CookieAuth", scheme_def)

        assert result is None

    def test_classify_api_key_missing_name(self):
        """Test API key without name field returns None."""
        scheme_def = {"type": "apiKey", "in": "header"}

        result = classify_security_scheme("MalformedApiKey", scheme_def)

        assert result is None


class TestGetPrimarySecurityScheme:
    """Tests for get_primary_security_scheme function with real YAML files."""

    def test_no_security_schemes_returns_none(self):
        """Test that None is returned when spec has no security schemes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            openapi_file = target_dir / "openapi.yaml"

            openapi_file.write_text(
                """
openapi: 3.1.0
info:
  title: Test API
  version: 1.0.0
paths: {}
            """.strip(),
                encoding="utf-8",
            )

            result = get_primary_security_scheme(openapi_file)

            assert result is None

    def test_bearer_scheme_returned(self):
        """Test that Bearer scheme is returned as SecurityScheme object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            openapi_file = target_dir / "openapi.yaml"

            openapi_file.write_text(
                """
openapi: 3.1.0
info:
  title: Test API
  version: 1.0.0
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
paths: {}
            """.strip(),
                encoding="utf-8",
            )

            result = get_primary_security_scheme(openapi_file)

            assert result is not None
            assert isinstance(result, SecurityScheme)
            assert result.name == "BearerAuth"
            assert result.scheme_type == SecuritySchemeType.HTTP_BEARER
            assert result.header_name is None

    def test_api_key_scheme_returned(self):
        """Test that API Key scheme is returned with header_name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            openapi_file = target_dir / "openapi.yaml"

            openapi_file.write_text(
                """
openapi: 3.1.0
info:
  title: Test API
  version: 1.0.0
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Custom-Key
paths: {}
            """.strip(),
                encoding="utf-8",
            )

            result = get_primary_security_scheme(openapi_file)

            assert result is not None
            assert isinstance(result, SecurityScheme)
            assert result.name == "ApiKeyAuth"
            assert result.scheme_type == SecuritySchemeType.API_KEY_HEADER
            assert result.header_name == "X-Custom-Key"

    def test_first_scheme_selected_from_multiple(self):
        """Test that first supported scheme is returned when multiple exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            openapi_file = target_dir / "openapi.yaml"

            # Note: YAML preserves order, BearerAuth should be first
            openapi_file.write_text(
                """
openapi: 3.1.0
info:
  title: Test API
  version: 1.0.0
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
paths: {}
            """.strip(),
                encoding="utf-8",
            )

            result = get_primary_security_scheme(openapi_file)

            assert result is not None
            assert result.name == "BearerAuth"
            assert result.scheme_type == SecuritySchemeType.HTTP_BEARER

    def test_unsupported_scheme_returns_none(self):
        """Test that None is returned when only unsupported schemes exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            openapi_file = target_dir / "openapi.yaml"

            openapi_file.write_text(
                """
openapi: 3.1.0
info:
  title: Test API
  version: 1.0.0
components:
  securitySchemes:
    OAuth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://example.com/oauth/authorize
          tokenUrl: https://example.com/oauth/token
          scopes:
            read: Read access
paths: {}
            """.strip(),
                encoding="utf-8",
            )

            result = get_primary_security_scheme(openapi_file)

            assert result is None

    def test_invalid_file_returns_none(self):
        """Test that None is returned when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            nonexistent_file = target_dir / "nonexistent.yaml"

            result = get_primary_security_scheme(nonexistent_file)

            assert result is None

    def test_malformed_yaml_returns_none(self):
        """Test that None is returned for malformed YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            openapi_file = target_dir / "openapi.yaml"

            # Invalid YAML syntax
            openapi_file.write_text(
                """
this is not: valid: yaml: syntax
  - broken
    indentation
            """.strip(),
                encoding="utf-8",
            )

            result = get_primary_security_scheme(openapi_file)

            assert result is None

    def test_first_supported_scheme_from_mixed_list(self):
        """Test that first supported scheme is selected, skipping unsupported ones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)
            openapi_file = target_dir / "openapi.yaml"

            # OAuth2 is first but unsupported, BearerAuth should be selected
            openapi_file.write_text(
                """
openapi: 3.1.0
info:
  title: Test API
  version: 1.0.0
components:
  securitySchemes:
    OAuth2:
      type: oauth2
      flows:
        implicit:
          authorizationUrl: https://example.com/oauth
          scopes: {}
    BearerAuth:
      type: http
      scheme: bearer
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
paths: {}
            """.strip(),
                encoding="utf-8",
            )

            result = get_primary_security_scheme(openapi_file)

            assert result is not None
            assert result.name == "BearerAuth"
            assert result.scheme_type == SecuritySchemeType.HTTP_BEARER


class TestGenerateAuthenticationMiddleware:
    """Tests for generate_authentication_middleware function."""

    def test_generate_bearer_middleware(self):
        """Test generation of middleware for Bearer authentication."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            # Create OpenAPI spec with Bearer auth
            (target_dir / "openapi.yaml").write_text(
                """
openapi: 3.1.0
info:
  title: Test API
  version: 1.0.0
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
paths: {}
            """.strip(),
                encoding="utf-8",
            )

            # Create Client directory
            client_dir = target_dir / "Sources" / "TestProject"
            client_dir.mkdir(parents=True)

            # Generate middleware
            result = generate_authentication_middleware(target_dir, "TestProject")

            # Verify return status
            assert result["generated"] is True
            assert "http bearer" in result["reason"].lower()
            assert result["scheme_name"] == "BearerAuth"
            assert result["scheme_type"] == "http_bearer"

            # Verify file created
            auth_file = client_dir / "AuthenticationMiddleware.swift"
            assert auth_file.exists()

            # Verify content
            content = auth_file.read_text(encoding="utf-8")
            assert "Bearer" in content
            assert ".authorization" in content

    def test_generate_api_key_middleware(self):
        """Test generation of middleware for API Key authentication."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            # Create OpenAPI spec with API Key auth
            (target_dir / "openapi.yaml").write_text(
                """
openapi: 3.1.0
info:
  title: Test API
  version: 1.0.0
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-Custom-Key
paths: {}
            """.strip(),
                encoding="utf-8",
            )

            # Create Client directory
            client_dir = target_dir / "Sources" / "TestProject"
            client_dir.mkdir(parents=True)

            # Generate middleware
            result = generate_authentication_middleware(target_dir, "TestProject")

            # Verify return status
            assert result["generated"] is True
            assert "api key header" in result["reason"].lower()
            assert result["scheme_name"] == "ApiKeyAuth"
            assert result["scheme_type"] == "api_key_header"

            # Verify file created
            auth_file = client_dir / "AuthenticationMiddleware.swift"
            assert auth_file.exists()

            # Verify content (header name should be lowercased)
            content = auth_file.read_text(encoding="utf-8")
            assert "x-custom-key" in content
            assert "HTTPField.Name" in content

    def test_no_security_no_file_generated(self):
        """Test that no file is created when OpenAPI has no security schemes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            # Create OpenAPI spec without security
            (target_dir / "openapi.yaml").write_text(
                """
openapi: 3.1.0
info:
  title: Test API
  version: 1.0.0
paths: {}
            """.strip(),
                encoding="utf-8",
            )

            # Create Client directory
            client_dir = target_dir / "Sources" / "TestProject"
            client_dir.mkdir(parents=True)

            # Try to generate middleware
            result = generate_authentication_middleware(target_dir, "TestProject")

            # Verify no file created
            auth_file = client_dir / "AuthenticationMiddleware.swift"
            assert not auth_file.exists()

            # Verify return status
            assert result["generated"] is False
            assert "no supported" in result["reason"].lower()
            assert result["scheme_name"] is None
            assert result["scheme_type"] is None

    def test_preserve_existing_file(self):
        """Test that existing middleware file is preserved (user edits protected)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            # Create OpenAPI spec
            (target_dir / "openapi.yaml").write_text(
                """
openapi: 3.1.0
info:
  title: Test API
  version: 1.0.0
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
paths: {}
            """.strip(),
                encoding="utf-8",
            )

            # Create Client directory
            client_dir = target_dir / "Sources" / "TestProject"
            client_dir.mkdir(parents=True)

            # Create existing file with custom content
            auth_file = client_dir / "AuthenticationMiddleware.swift"
            custom_content = "// Custom user modifications\nstruct MyCustomAuth {}"
            auth_file.write_text(custom_content, encoding="utf-8")

            # Try to generate middleware
            result = generate_authentication_middleware(target_dir, "TestProject")

            # Verify file content is preserved
            assert auth_file.read_text(encoding="utf-8") == custom_content

            # Verify return status
            assert result["generated"] is False
            assert "already exists" in result["reason"].lower()
            assert result["scheme_name"] == "BearerAuth"
            assert result["scheme_type"] == "http_bearer"

    def test_openapi_file_not_found(self):
        """Test handling when OpenAPI file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            # Don't create OpenAPI file
            # Create Client directory anyway
            client_dir = target_dir / "Sources" / "TestProject"
            client_dir.mkdir(parents=True)

            # Try to generate middleware
            result = generate_authentication_middleware(target_dir, "TestProject")

            # Verify no file created
            auth_file = client_dir / "AuthenticationMiddleware.swift"
            assert not auth_file.exists()

            # Verify return status
            assert result["generated"] is False
            assert "not found" in result["reason"].lower()
            assert result["scheme_name"] is None
            assert result["scheme_type"] is None

    def test_unsupported_scheme_no_generation(self):
        """Test that unsupported schemes don't generate middleware."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            # Create OpenAPI spec with OAuth2 (unsupported)
            (target_dir / "openapi.yaml").write_text(
                """
openapi: 3.1.0
info:
  title: Test API
  version: 1.0.0
components:
  securitySchemes:
    OAuth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://example.com/oauth/authorize
          tokenUrl: https://example.com/oauth/token
          scopes:
            read: Read access
paths: {}
            """.strip(),
                encoding="utf-8",
            )

            # Create Client directory
            client_dir = target_dir / "Sources" / "TestProject"
            client_dir.mkdir(parents=True)

            # Try to generate middleware
            result = generate_authentication_middleware(target_dir, "TestProject")

            # Verify no file created
            auth_file = client_dir / "AuthenticationMiddleware.swift"
            assert not auth_file.exists()

            # Verify return status
            assert result["generated"] is False
            assert "no supported" in result["reason"].lower()

    def test_json_openapi_file(self):
        """Test that JSON OpenAPI files are supported."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            # Create OpenAPI spec as JSON
            (target_dir / "openapi.json").write_text(
                """{
  "openapi": "3.1.0",
  "info": {
    "title": "Test API",
    "version": "1.0.0"
  },
  "components": {
    "securitySchemes": {
      "BearerAuth": {
        "type": "http",
        "scheme": "bearer"
      }
    }
  },
  "paths": {}
}""",
                encoding="utf-8",
            )

            # Create Client directory
            client_dir = target_dir / "Sources" / "TestProject"
            client_dir.mkdir(parents=True)

            # Generate middleware with JSON file
            result = generate_authentication_middleware(
                target_dir, "TestProject", openapi_file="openapi.json"
            )

            # Verify success
            assert result["generated"] is True
            auth_file = client_dir / "AuthenticationMiddleware.swift"
            assert auth_file.exists()

    def test_custom_openapi_filename(self):
        """Test that custom OpenAPI filename is supported."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_dir = Path(tmpdir)

            # Create OpenAPI spec with custom name
            (target_dir / "custom-api.yaml").write_text(
                """
openapi: 3.1.0
info:
  title: Test API
  version: 1.0.0
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
paths: {}
            """.strip(),
                encoding="utf-8",
            )

            # Create Client directory
            client_dir = target_dir / "Sources" / "TestProject"
            client_dir.mkdir(parents=True)

            # Generate middleware with custom filename
            result = generate_authentication_middleware(
                target_dir, "TestProject", openapi_file="custom-api.yaml"
            )

            # Verify success
            assert result["generated"] is True
            auth_file = client_dir / "AuthenticationMiddleware.swift"
            assert auth_file.exists()
