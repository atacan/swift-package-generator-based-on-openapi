"""Tests for op10_unique_operation_ids: make operationId values unique."""

from bootstrapper.transformers.op10_unique_operation_ids import ensure_unique_operation_ids


def test_duplicate_operation_id_is_replaced_with_path_based_id():
    spec = {
        "paths": {
            "/v1/projects/{project_id}/billing/fields": {
                "get": {"operationId": "listFields", "responses": {"200": {"description": "OK"}}}
            },
            "/v1/accounts": {
                "get": {"operationId": "listFields", "responses": {"200": {"description": "OK"}}}
            },
        }
    }

    result = ensure_unique_operation_ids(spec)

    assert (
        result["paths"]["/v1/projects/{project_id}/billing/fields"]["get"]["operationId"]
        == "projects_project_id_BillingFields"
    )
    assert result["paths"]["/v1/accounts"]["get"]["operationId"] == "accounts"


def test_unique_operation_ids_are_left_unchanged():
    spec = {
        "paths": {
            "/v1/projects": {"get": {"operationId": "listProjects"}},
            "/v1/accounts": {"get": {"operationId": "listAccounts"}},
        }
    }

    result = ensure_unique_operation_ids(spec)

    assert result["paths"]["/v1/projects"]["get"]["operationId"] == "listProjects"
    assert result["paths"]["/v1/accounts"]["get"]["operationId"] == "listAccounts"


def test_generated_operation_ids_get_suffix_when_paths_still_collide():
    spec = {
        "paths": {
            "/v1/projects/{project_id}": {"get": {"operationId": "getThing"}},
            "/v2/projects/{project_id}": {"get": {"operationId": "getThing"}},
        }
    }

    result = ensure_unique_operation_ids(spec)

    assert (
        result["paths"]["/v1/projects/{project_id}"]["get"]["operationId"] == "projects_project_id"
    )
    assert (
        result["paths"]["/v2/projects/{project_id}"]["get"]["operationId"]
        == "projects_project_id_2"
    )


def test_only_openapi_operations_are_considered():
    spec = {
        "paths": {
            "/v1/projects": {
                "parameters": [{"name": "trace_id", "in": "header"}],
                "get": {"operationId": "same"},
            },
            "/v1/accounts": {"post": {"operationId": "same"}},
        }
    }

    result = ensure_unique_operation_ids(spec)

    assert "operationId" not in result["paths"]["/v1/projects"]["parameters"][0]
    assert result["paths"]["/v1/projects"]["get"]["operationId"] == "projects"
    assert result["paths"]["/v1/accounts"]["post"]["operationId"] == "accounts"


def test_path_order_is_preserved_for_multiple_parameters():
    spec = {
        "paths": {
            "/v1/projects/{project_id}/items/{item_id}/history": {"get": {"operationId": "same"}},
            "/v1/accounts": {"get": {"operationId": "same"}},
        }
    }

    result = ensure_unique_operation_ids(spec)

    assert (
        result["paths"]["/v1/projects/{project_id}/items/{item_id}/history"]["get"]["operationId"]
        == "projects_project_id_Items_item_id_History"
    )
