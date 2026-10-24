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
    def write_spec(self, target_dir, **changes):
        import yaml

        spec = {
            "openapi": "3.1.0",
            "info": {"title": "Test", "version": "1"},
            "components": {
                "securitySchemes": {
                    "BearerAuth": {"type": "http", "scheme": "bearer"},
                    "Key": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
                    "OAuth": {"type": "oauth2", "flows": {}},
                }
            },
            "security": [{"BearerAuth": []}],
            "paths": {"/test": {"get": {"operationId": "getTest"}}},
        }
        spec.update(changes)
        (target_dir / "openapi.yaml").write_text(yaml.safe_dump(spec))
        return spec

    def metadata(self, target_dir):
        return (
            target_dir
            / "Sources/TestProject/Authentication/GeneratedSecurity/OperationSecurity.swift"
        ).read_text()

    def test_shared_authentication_is_in_client_module(self, tmp_path):
        self.write_spec(tmp_path)
        result = generate_authentication_middleware(tmp_path, "TestProject")
        assert result["generated"]
        assert result["unsupported_schemes"] == ["OAuth"]
        assert (
            tmp_path / "Sources/TestProject/Authentication/AuthenticationMiddleware.swift"
        ).exists()
        assert not (tmp_path / "Sources/TestProjectTypes").exists()
        metadata = self.metadata(tmp_path)
        assert '"BearerAuth": .bearer' in metadata
        assert '"Key": .apiKey(header: "x-api-key")' in metadata
        assert '"OAuth": .unsupported' in metadata

    def test_inheritance_overrides_and_alternatives(self, tmp_path):
        self.write_spec(
            tmp_path,
            paths={
                "/test": {
                    "get": {"operationId": "inherited"},
                    "put": {"operationId": "public", "security": []},
                    "post": {
                        "operationId": "combined",
                        "security": [{"BearerAuth": [], "Key": []}],
                    },
                    "delete": {
                        "operationId": "alternative",
                        "security": [{"OAuth": []}, {"Key": []}, {}],
                    },
                }
            },
        )
        generate_authentication_middleware(tmp_path, "TestProject")
        content = self.metadata(tmp_path)
        assert '"inherited": [["BearerAuth"]]' in content
        assert '"public": []' in content
        assert '"combined": [["BearerAuth", "Key"]]' in content
        assert '"alternative": [["OAuth"], ["Key"], []]' in content

    def test_refreshes_metadata_and_preserves_user_code(self, tmp_path):
        self.write_spec(tmp_path)
        generate_authentication_middleware(tmp_path, "TestProject")
        middleware = tmp_path / "Sources/TestProject/Authentication/AuthenticationMiddleware.swift"
        middleware.write_text("// user middleware\n")
        self.write_spec(tmp_path, security=[{"Key": []}])
        result = generate_authentication_middleware(tmp_path, "TestProject")
        assert not result["generated"]
        assert result["metadata_updated"]
        assert middleware.read_text() == "// user middleware\n"
        assert '"getTest": [["Key"]]' in self.metadata(tmp_path)
        assert not generate_authentication_middleware(tmp_path, "TestProject")["metadata_updated"]

    def test_no_security_still_supports_convenience_factories(self, tmp_path):
        self.write_spec(tmp_path, components={}, security=[])
        generate_authentication_middleware(tmp_path, "TestProject")
        assert "defaultRequirements: [[String]] = []" in self.metadata(tmp_path)
        assert (tmp_path / "Sources/TestProject/Authentication/Authentication.swift").exists()

    def test_missing_spec(self, tmp_path):
        result = generate_authentication_middleware(tmp_path, "TestProject")
        assert not result["generated"]
        assert "not found" in result["reason"]
        assert not (tmp_path / "Sources").exists()

    def test_local_references_and_escaped_names(self, tmp_path):
        spec = self.write_spec(tmp_path)
        spec["components"]["securitySchemes"]["Alias"] = {
            "$ref": "#/components/securitySchemes/BearerAuth"
        }
        spec["paths"] = {"/test": {"$ref": "#/components/pathItems/Test"}}
        spec["components"]["pathItems"] = {"Test": {"get": {"operationId": 'quote"\\(literal)'}}}
        import yaml

        (tmp_path / "custom.yaml").write_text(yaml.safe_dump(spec))
        generate_authentication_middleware(tmp_path, "TestProject", "custom.yaml")
        assert '"Alias": .bearer' in self.metadata(tmp_path)
        from bootstrapper.generators.security import swift_string

        assert swift_string('quote"\\(literal)') in self.metadata(tmp_path)

    def test_unresolved_reference_does_not_disable_authentication(self, tmp_path):
        import pytest

        self.write_spec(tmp_path, paths={"/test": {"$ref": "remote.yaml#/paths/test"}})
        with pytest.raises(ValueError, match="Unsupported"):
            generate_authentication_middleware(tmp_path, "TestProject")

    def test_missing_operation_id_uses_generator_fallback(self, tmp_path):
        self.write_spec(
            tmp_path,
            paths={
                "/public/{id}": {"get": {"security": []}},
                "/key": {"post": {"security": [{"Key": []}]}},
            },
        )
        generate_authentication_middleware(tmp_path, "TestProject")
        assert '"get/public/{id}": []' in self.metadata(tmp_path)
        assert '"post/key": [["Key"]]' in self.metadata(tmp_path)

    def test_case_insensitive_bearer_and_percent_encoded_reference(self, tmp_path):
        self.write_spec(
            tmp_path,
            components={
                "securitySchemes": {
                    "Token Auth": {"type": "http", "scheme": "Bearer"},
                    "Alias": {"$ref": "#/components/securitySchemes/Token%20Auth"},
                }
            },
        )
        generate_authentication_middleware(tmp_path, "TestProject")
        assert '"Token Auth": .bearer' in self.metadata(tmp_path)
        assert '"Alias": .bearer' in self.metadata(tmp_path)
