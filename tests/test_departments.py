import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_department(client: AsyncClient) -> None:
    """POST /departments/ creates a root department."""
    response = await client.post(
        "/departments/",
        json={"name": "  Engineering  ", "parent_id": None},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Engineering"
    assert body["parent_id"] is None
    assert "id" in body


@pytest.mark.asyncio
async def test_cycle_forbidden(client: AsyncClient) -> None:
    """Moving a department under its descendant returns 409."""
    parent = await client.post("/departments/", json={"name": "Root", "parent_id": None})
    child = await client.post(
        "/departments/",
        json={"name": "Child", "parent_id": parent.json()["id"]},
    )
    grand = await client.post(
        "/departments/",
        json={"name": "Grand", "parent_id": child.json()["id"]},
    )

    response = await client.patch(
        f"/departments/{parent.json()['id']}",
        json={"parent_id": grand.json()["id"]},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Department cycle detected"


@pytest.mark.asyncio
async def test_get_department_tree(client: AsyncClient) -> None:
    """GET /departments/{id} returns nested children and employees."""
    root = await client.post("/departments/", json={"name": "Root", "parent_id": None})
    child = await client.post(
        "/departments/",
        json={"name": "Child", "parent_id": root.json()["id"]},
    )
    await client.post(
        f"/departments/{child.json()['id']}/employees/",
        json={
            "full_name": "Jane Doe",
            "position": "Engineer",
            "hired_at": "2024-06-01",
        },
    )

    response = await client.get(
        f"/departments/{root.json()['id']}",
        params={"depth": 2, "include_employees": True},
    )
    assert response.status_code == 200
    tree = response.json()
    assert tree["name"] == "Root"
    assert len(tree["children"]) == 1
    assert tree["children"][0]["name"] == "Child"
    assert len(tree["children"][0]["employees"]) == 1
    assert tree["children"][0]["employees"][0]["full_name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_cascade_delete(client: AsyncClient) -> None:
    """Cascade delete removes subtree and employees."""
    root = await client.post("/departments/", json={"name": "Root", "parent_id": None})
    child = await client.post(
        "/departments/",
        json={"name": "Child", "parent_id": root.json()["id"]},
    )
    await client.post(
        f"/departments/{child.json()['id']}/employees/",
        json={"full_name": "John", "position": "Dev", "hired_at": None},
    )
    response = await client.get(f"/departments/{root.json()['id']}")
    assert response.status_code == 200

    response = await client.delete(
        f"/departments/{root.json()['id']}",
        params={"mode": "cascade"},
    )
    assert response.status_code == 204
    response = await client.get(f"/departments/{root.json()['id']}")
    assert response.status_code == 404
