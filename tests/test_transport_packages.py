"""Verify generated product isolation and actual transport/authentication behavior."""

import json
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml
from jinja2 import Template

from bootstrapper.generators.security import generate_authentication_middleware
from bootstrapper.generators.swift import (
    create_client_helpers,
    ensure_package_structure,
    run_openapi_generator,
)
from bootstrapper.generators.templates import generate_config_files


def test_four_products_and_isolated_core_dependencies(tmp_path):
    ensure_package_structure(tmp_path, "TestProject")
    manifest = (tmp_path / "Package.swift").read_text()
    # Inspect target blocks separately so transport dependencies cannot leak into core.
    core = manifest.split('name: "TestProject",\n            dependencies: [')[1].split(
        "// Transport conveniences", 1
    )[0]
    assert "OpenAPIURLSession" not in core
    assert "OpenAPIAsyncHTTPClient" not in core
    for suffix in ("", "Types", "URLSession", "AsyncHTTPClient"):
        assert (tmp_path / "Sources" / f"TestProject{suffix}").is_dir()
        assert (tmp_path / "Tests" / f"TestProject{suffix}Tests").is_dir()
        assert f'targets: ["TestProject{suffix}"]' in manifest
    assert "UsefulThings" not in manifest


def test_factories_are_added_after_generation_and_preserve_edits(tmp_path):
    ensure_package_structure(tmp_path, "TestProject")
    factory = tmp_path / "Sources/TestProjectURLSession/Client+URLSession.swift"
    assert not factory.exists()  # Scaffolding builds even before Client exists.
    create_client_helpers(tmp_path, "TestProject")
    assert "public static func urlSession" in factory.read_text()
    factory.write_text("// custom factory\n")
    create_client_helpers(tmp_path, "TestProject")
    assert factory.read_text() == "// custom factory\n"


def transport_spec():
    response = {
        "description": "Echo request headers",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        name: {"type": "string"} for name in ("authorization", "apiKey", "marker")
                    },
                    "required": ["authorization", "apiKey", "marker"],
                }
            }
        },
    }
    operations = {
        "bearer": None,
        "publicEndpoint": [],
        "key": [{"Key": []}],
        "combined": [{"BearerAuth": [], "Key": []}],
        "alternative": [{"OAuth": []}, {"Key": []}],
        "optionalAuth": [{"BearerAuth": []}, {}],
        "unsupported": [{"OAuth": []}],
    }
    spec = {
        "openapi": "3.1.0",
        "info": {"title": "Transport test", "version": "1.0.0"},
        "security": [{"BearerAuth": []}],
        "components": {
            "securitySchemes": {
                "BearerAuth": {"type": "http", "scheme": "bearer"},
                "Key": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
                "OAuth": {
                    "type": "oauth2",
                    "flows": {
                        "clientCredentials": {
                            "tokenUrl": "https://example.com/token",
                            "scopes": {},
                        }
                    },
                },
            }
        },
        "paths": {
            f"/{name}": {
                "get": {
                    "operationId": name,
                    "responses": {"200": response},
                    **({"security": security} if security is not None else {}),
                }
            }
            for name, security in operations.items()
        },
    }

    spec["paths"]["/publicWithoutID"] = {"get": {"security": [], "responses": {"200": response}}}
    return spec


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("swift") is None, reason="Swift toolchain not available")
def test_generated_package_builds_and_both_transports_authenticate(tmp_path):
    ensure_package_structure(tmp_path, "TestProject")
    generate_config_files(tmp_path, "TestProject")
    (tmp_path / "openapi.yaml").write_text(yaml.safe_dump(transport_spec()))
    generate_authentication_middleware(tmp_path, "TestProject")
    result = run_openapi_generator(tmp_path, "TestProject")
    assert all(result.values()), f"Swift OpenAPI generation failed in {tmp_path}"

    class EchoHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps(
                {
                    "authorization": self.headers.get("Authorization", "<none>"),
                    "apiKey": self.headers.get("X-API-Key", "<none>"),
                    "marker": self.headers.get("X-Marker", "<none>"),
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    fixtures = Path(__file__).parent / "fixtures"
    (tmp_path / "Tests/TestProjectTests/AuthenticationTests.swift").write_text(
        (fixtures / "AuthenticationTests.swift").read_text()
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), EchoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for suffix, module, method, configuration in (
            (
                "URLSession",
                "OpenAPIURLSession",
                "urlSession",
                ".init(session: URLSession(configuration: .ephemeral))",
            ),
            (
                "AsyncHTTPClient",
                "OpenAPIAsyncHTTPClient",
                "asyncHTTPClient",
                ".init(client: .shared, timeout: .seconds(10))",
            ),
        ):
            template = Template((fixtures / "TransportTests.swift.j2").read_text())
            content = template.render(
                suffix=suffix,
                module=module,
                method=method,
                configuration=configuration,
                server_url=f"http://127.0.0.1:{server.server_port}",
            )
            (tmp_path / f"Tests/TestProject{suffix}Tests/TransportTests.swift").write_text(content)
        result = subprocess.run(
            ["swift", "test"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_existing_manifest_gets_migration_notice_without_overwriting(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from bootstrapper.main import app

    manifest = 'import PackageDescription\nlet package = Package(name: "TestProject")\n'
    (tmp_path / "Package.swift").write_text(manifest)
    (tmp_path / "original_openapi.yaml").write_text(yaml.safe_dump(transport_spec()))
    monkeypatch.setattr(
        "bootstrapper.main.run_openapi_generator",
        lambda *_args, **_kwargs: {"types_generated": True, "client_generated": True},
    )
    result = CliRunner().invoke(app, [str(tmp_path), "--name", "TestProject"])
    assert result.exit_code == 0, result.stdout
    assert "manual update" in result.stdout
    assert (tmp_path / "Package.swift").read_text() == manifest
