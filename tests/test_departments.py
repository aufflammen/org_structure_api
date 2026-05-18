from datetime import datetime

import pytest
from httpx import AsyncClient

from .helpers import (
    post_department,
    get_department,
    patch_department,
    delete_department,
    post_employee,
)


@pytest.mark.asyncio
async def test_create_department(client: AsyncClient) -> None:
    """POST /departments/ creates a root department."""
    response = await post_department(
        client,
        name="  Engineering  ",
        parent_id=None,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Engineering"
    assert body["parent_id"] is None
    assert isinstance(body["id"], int)
    assert isinstance(datetime.fromisoformat(body["created_at"]), datetime)


@pytest.mark.asyncio
async def test_create_department_parent_not_found(client: AsyncClient) -> None:
    """Unknown parent_id returns 404."""
    response = await post_department(
        client,
        name="Orphan",
        parent_id=42,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Parent department not found"


@pytest.mark.asyncio
async def test_create_duplicate_name_same_parent(client: AsyncClient) -> None:
    """Duplicate names under the same parent are rejected."""
    root = await post_department(client, name="Root")
    root_same = await post_department(client, name="Root")

    child = await post_department(
        client,
        name="Child",
        parent_id=root.json()["id"],
    )
    child_same = await post_department(
        client,
        name="Child",
        parent_id=root.json()["id"],
    )

    assert root.status_code == 201
    assert root_same.status_code == 409
    assert root_same.json()["detail"] == (
        "Duplicate: department name already exists under this parent"
    )

    assert child.status_code == 201
    assert child_same.status_code == 409
    assert child_same.json()["detail"] == (
        "Duplicate: department name already exists under this parent"
    )


@pytest.mark.asyncio
async def test_update_department_name(client: AsyncClient) -> None:
    """Root department name can be updated (parent_id is null)."""
    root = await post_department(client, name="Root")
    root_id = root.json()["id"]

    child = await post_department(client, name="Child", parent_id=root_id)
    child_id = child.json()["id"]

    renamed_root = await patch_department(
        client,
        department_id=root_id,
        name="  Renamed Root "
    )
    assert renamed_root.status_code == 200
    assert renamed_root.json()["name"] == "Renamed Root"
    assert renamed_root.json()["parent_id"] is None

    renamed_child = await patch_department(
        client,
        department_id=child_id,
        name=" Renamed Child  ",
    )
    assert renamed_child.status_code == 200
    assert renamed_child.json()["name"] == "Renamed Child"
    assert renamed_child.json()["parent_id"] == root_id


@pytest.mark.asyncio
async def test_update_department_parent_id(client: AsyncClient) -> None:
    """Root department parent_id can be updated (name is null)."""
    root1 = await post_department(client, name="Root1")
    root2 = await post_department(client, name="Root2")
    child = await post_department(
        client,
        name="Child",
        parent_id=root1.json()["id"],
    )

    reparent_child = await patch_department(
        client,
        department_id=child.json()["id"],
        parent_id=root2.json()["id"]
    )
    assert reparent_child.status_code == 200
    assert reparent_child.json()["name"] == "Child"
    assert reparent_child.json()["parent_id"] == root2.json()["id"]


# @pytest.mark.asyncio
# async def test_move_department_to_root(client: AsyncClient) -> None:
#     """PATCH with parent_id=null moves department to root level."""
#     root = await post_department(client, name="Root")
#     child = await post_department(client, name="Child", parent_id=root.json()["id"])
#
#     response = await patch_department(
#         client,
#         department_id=child.json()["id"],
#         parent_id=None,
#     )
#
#     assert response.status_code == 200
#     assert response.json()["parent_id"] is None


@pytest.mark.asyncio
async def test_cycle_forbidden(client: AsyncClient) -> None:
    """Moving a department under its descendant returns 409."""
    root = await post_department(client, name="Root")
    child = await post_department(client, name="Child", parent_id=root.json()["id"])
    grand = await post_department(client, name="Grand", parent_id=child.json()["id"])

    response = await patch_department(
        client,
        department_id=root.json()["id"],
        parent_id=grand.json()["id"],
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Department cycle detected"


@pytest.mark.asyncio
async def test_cannot_be_own_parent(client: AsyncClient) -> None:
    """Department cannot reference itself as parent."""
    dept = await post_department(client, name="Solo")
    dept_id = dept.json()["id"]

    response = await patch_department(client, dept_id, parent_id=dept_id)

    assert response.status_code == 409
    assert response.json()["detail"] == "Department cannot be its own parent"


@pytest.mark.asyncio
async def test_get_department_tree(client: AsyncClient) -> None:
    """GET /departments/{id} returns nested children and employees."""
    root = await post_department(client, name="Root")
    child = await post_department(client, name="Child", parent_id=root.json()["id"])
    await post_employee(
        client,
        child.json()["id"],
        full_name="John Doe",
        position="Engineer",
        hired_at="2020-01-02",
    )

    response = await get_department(
        client,
        department_id=root.json()["id"],
        depth=2,
        include_employees=True,
    )

    assert response.status_code == 200
    tree = response.json()
    assert tree["name"] == "Root"
    assert len(tree["children"]) == 1
    assert tree["children"][0]["name"] == "Child"
    assert len(tree["children"][0]["employees"]) == 1
    assert tree["children"][0]["employees"][0]["full_name"] == "John Doe"


@pytest.mark.asyncio
async def test_get_department_not_found(client: AsyncClient) -> None:
    """Missing department returns 404."""
    response = await get_department(client, department_id=9999)

    assert response.status_code == 404
    assert response.json()["detail"] == "Department not found"


@pytest.mark.asyncio
async def test_tree_depth_limits_children(client: AsyncClient) -> None:
    """depth=1 returns only direct children."""
    root = await post_department(client, name="Root")
    child = await post_department(client, name="Child", parent_id=root.json()["id"])
    await post_department(client, name="Grand", parent_id=child.json()["id"])

    response = await get_department(
        client,
        root.json()["id"],
        depth=1,
        include_employees=False
    )

    assert response.status_code == 200
    assert len(response.json()["children"]) == 1
    assert len(response.json()["children"][0]["children"]) == 0


@pytest.mark.asyncio
async def test_tree_depth_validation(client: AsyncClient) -> None:
    """depth must be between 1 and 5."""
    root = await post_department(client, name="Root")

    response1 = await get_department(client, root.json()["id"], depth=0)
    response2 = await get_department(client, root.json()["id"], depth=10)

    assert response1.status_code == 422
    assert "Input should be greater than or equal to 1" in str(response1.json()["detail"])

    assert response2.status_code == 422
    assert "Input should be less than or equal to 5" in str(response2.json()["detail"])


@pytest.mark.asyncio
async def test_cascade_delete(client: AsyncClient) -> None:
    """Cascade delete removes subtree and employees."""
    root = await post_department(client, name="Root")
    child = await post_department(client, name="Child", parent_id=root.json()["id"])
    await post_employee(
        client,
        department_id=child.json()["id"],
        full_name="John",
        position="Dev"
    )

    response = await delete_department(client, root.json()["id"], mode="cascade")
    assert response.status_code == 204

    response = await get_department(client, root.json()["id"])
    assert response.status_code == 404

    response = await get_department(client, child.json()["id"])
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reassign_delete_reparents_children(client: AsyncClient) -> None:
    """Reassign mode moves employees and promotes children to deleted node's parent."""
    root = await post_department(client, name="Root")
    middle = await post_department(client, name="Middle", parent_id=root.json()["id"])
    leaf = await post_department(client, name="Leaf", parent_id=middle.json()["id"])
    target = await post_department(client, name="Target")
    employee = await post_employee(client, middle.json()["id"], full_name="Mover", position="dev")

    response = await delete_department(
        client,
        middle.json()["id"],
        mode="reassign",
        reassign_to_department_id=target.json()["id"]
    )
    assert response.status_code == 204

    leaf_response = await get_department(client, leaf.json()["id"])
    assert leaf_response.status_code == 200
    assert leaf_response.json()["name"] == "Leaf"

    root_tree = await get_department(
        client,
        root.json()["id"],
        depth=2,
        include_employees=True,
    )
    child_names = [c["name"] for c in root_tree.json()["children"]]
    assert "Leaf" in child_names

    target_tree = await get_department(
        client,
        target.json()["id"],
        depth=1,
        include_employees=True,
    )
    employee_names = [e["full_name"] for e in target_tree.json()["employees"]]
    assert "Mover" in employee_names
    assert len(employee_names) == 1


@pytest.mark.asyncio
async def test_reassign_requires_target(client: AsyncClient) -> None:
    """Reassign without reassign_to_department_id returns 400."""
    dept = await post_department(client, name="ToDelete")

    response = await delete_department(
        client,
        dept.json()["id"],
        mode="reassign",
        reassign_to_department_id=None,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "reassign_to_department_id is required for mode=reassign"
    )


@pytest.mark.asyncio
async def test_reassign_same_department_forbidden(client: AsyncClient) -> None:
    """reassign_to_department_id cannot equal the deleted department id."""
    dept = await post_department(client, name="ToDelete")

    response = await delete_department(
        client,
        dept.json()["id"],
        mode="reassign",
        reassign_to_department_id=dept.json()["id"]
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "reassign_to_department_id cannot be equal to deleted department id"
    )


@pytest.mark.asyncio
async def test_reassign_to_child_department_allowed(client: AsyncClient) -> None:
    """Employees may be reassigned to a child department of the deleted node."""
    root = await post_department(client, name="HQ")
    sales = await post_department(client, name="Sales", parent_id=root.json()["id"])
    east = await post_department(client, name="East", parent_id=sales.json()["id"])
    await post_employee(client, sales.json()["id"], full_name="Seller", position="Sell")

    response = await delete_department(
        client,
        sales.json()["id"],
        mode="reassign",
        reassign_to_department_id=east.json()["id"],
    )
    assert response.status_code == 204

    east_tree = await get_department(
        client,
        east.json()["id"],
        depth=1,
        include_employees=True,
    )

    assert east_tree.status_code == 200
    assert any(e["full_name"] == "Seller" for e in east_tree.json()["employees"])

    root_tree = await get_department(
        client,
        root.json()["id"],
        depth=2,
        include_employees=False,
    )

    child_names = [c["name"] for c in root_tree.json()["children"]]
    assert "East" in child_names


@pytest.mark.asyncio
async def test_reassign_keeps_child_department_employees(client: AsyncClient) -> None:
    """Only employees of the deleted department are moved, not subtree employees."""
    root = await post_department(client, name="Root")
    middle = await post_department(client, name="Middle", parent_id=root.json()["id"])
    leaf = await post_department(client, name="Leaf", parent_id=middle.json()["id"])
    target = await post_department(client, name="Target")
    await post_employee(client, middle.json()["id"], full_name="Middle Worker", position="Dev")
    await post_employee(client, leaf.json()["id"], full_name="Leaf Worker", position="Dev")

    response = await delete_department(
        client,
        middle.json()["id"],
        mode="reassign",
        reassign_to_department_id=target.json()["id"],
    )
    assert response.status_code == 204

    target_tree = await get_department(
        client,
        target.json()["id"],
        depth=1,
        include_employees=True,
    )
    target_names = {e["full_name"] for e in target_tree.json()["employees"]}
    assert "Middle Worker" in target_names
    assert "Leaf Worker" not in target_names

    leaf_tree = await get_department(
        client,
        leaf.json()["id"],
        depth=1,
        include_employees=True,
    )
    leaf_names = {e["full_name"] for e in leaf_tree.json()["employees"]}
    assert "Leaf Worker" in leaf_names


@pytest.mark.asyncio
async def test_delete_department_not_found(client: AsyncClient) -> None:
    """Missing department returns 404."""
    response = await delete_department(client, 99999, mode="cascade")

    assert response.status_code == 404
    assert response.json()["detail"] == "Department not found"


@pytest.mark.asyncio
async def test_reassign_target_department_not_found(client: AsyncClient) -> None:
    """Unknown reassign_to_department_id returns 404."""
    dept = await post_department(client, name="ToDelete")

    response = await delete_department(
        client,
        dept.json()["id"],
        mode="reassign",
        reassign_to_department_id=99999,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Department not found"
