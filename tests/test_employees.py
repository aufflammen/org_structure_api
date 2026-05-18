import pytest
from httpx import AsyncClient

from .helpers import post_department, post_employee


@pytest.mark.asyncio
async def test_create_employee_in_department(client: AsyncClient) -> None:
    """POST /departments/{id}/employees/ creates an employee."""
    dept = await post_department(client, name="HR")

    response = await post_employee(
        client,
        dept.json()["id"],
        full_name="  Ada Lovelace  ",
        position="  Developer  ",
        hired_at="2024-06-15",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["full_name"] == "Ada Lovelace"
    assert body["position"] == "Developer"
    assert body["department_id"] == dept.json()["id"]
    assert body["hired_at"] == "2024-06-15"


@pytest.mark.asyncio
async def test_create_employee_unknown_department(client: AsyncClient) -> None:
    """Creating employee in missing department returns 404."""
    response = await post_employee(
        client,
        99999,
        full_name="Ghost",
        position="Dev",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Department not found"


@pytest.mark.asyncio
async def test_create_employee_invalid_payload(client: AsyncClient) -> None:
    """Empty names are rejected by validation."""
    dept = await post_department(client, name="Ops")

    response = await post_employee(
        client,
        dept.json()["id"],
        full_name="    ",
        position="HR",
    )
    assert response.status_code == 422
    assert "String should have at least 1 character" in str(response.json())
