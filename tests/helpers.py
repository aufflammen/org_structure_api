from typing import Literal

from httpx import AsyncClient, Response


async def post_department(
    client: AsyncClient,
    *,
    name: str,
    parent_id: int | None = None,
) -> Response:
    """Helper: create department and return response."""
    response = await client.post(
        "/departments/",
        json={"name": name, "parent_id": parent_id},
    )
    return response


async def get_department(
    client: AsyncClient,
    department_id: int,
    *,
    depth: int = 1,
    include_employees: bool = True,
) -> Response:
    """Helper: get department and return response."""
    response = await client.get(
        f"/departments/{department_id}",
        params={"depth": depth, "include_employees": include_employees},
    )
    return response


async def patch_department(
    client: AsyncClient,
    department_id: int,
    *,
    name: str | None = None,
    parent_id: int | None = None,
) -> Response:
    """Helper: patch department and return response."""
    response = await client.patch(
        f"/departments/{department_id}",
        json={"name": name, "parent_id": parent_id},
    )
    return response


async def delete_department(
    client: AsyncClient,
    department_id: int,
    *,
    mode: Literal["cascade", "reassign"],
    reassign_to_department_id: int | None = None,
) -> Response:
    """Helper: delete department and return response."""

    params = {
        "mode": mode,
        "reassign_to_department_id": reassign_to_department_id,
    }
    params = {k: v for k, v in params.items() if v is not None}

    response = await client.delete(
        f"/departments/{department_id}",
        params=params,
    )
    return response


async def post_employee(
    client: AsyncClient,
    department_id: int,
    *,
    full_name: str,
    position: str,
    hired_at: str | None = None,
) -> Response:
    """Helper: create employee and return response."""
    response = await client.post(
        f"/departments/{department_id}/employees/",
        json={
            "full_name": full_name,
            "position": position,
            "hired_at": hired_at,
        },
    )
    return response
