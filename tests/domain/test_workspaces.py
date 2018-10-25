import pytest
from uuid import uuid4

from atst.domain.exceptions import NotFoundError, UnauthorizedError
from atst.domain.workspaces import Workspaces
from atst.domain.workspace_users import WorkspaceUsers
from atst.domain.projects import Projects
from atst.domain.environments import Environments

from tests.factories import RequestFactory, UserFactory


@pytest.fixture(scope="function")
def workspace_owner():
    return UserFactory.create()


@pytest.fixture(scope="function")
def request_(workspace_owner):
    return RequestFactory.create(creator=workspace_owner)


@pytest.fixture(scope="function")
def workspace(request_):
    workspace = Workspaces.create(request_)
    return workspace


def test_can_create_workspace(request_):
    workspace = Workspaces.create(request_, name="frugal-whale")
    assert workspace.name == "frugal-whale"


def test_request_is_associated_with_workspace(workspace, request_):
    assert workspace.request == request_


def test_default_workspace_name_is_request_name(workspace, request_):
    assert workspace.name == str(request_.displayname)


def test_get_nonexistent_workspace_raises():
    with pytest.raises(NotFoundError):
        Workspaces.get(UserFactory.build(), uuid4())


def test_can_get_workspace_by_request(workspace):
    found = Workspaces.get_by_request(workspace.request)
    assert workspace == found


def test_creating_workspace_adds_owner(workspace, workspace_owner):
    assert workspace.roles[0].user == workspace_owner


def test_workspace_has_timestamps(workspace):
    assert workspace.time_created == workspace.time_updated


def test_workspaces_get_ensures_user_is_in_workspace(workspace, workspace_owner):
    outside_user = UserFactory.create()
    with pytest.raises(UnauthorizedError):
        Workspaces.get(outside_user, workspace.id)


def test_get_for_update_projects_allows_owner(workspace, workspace_owner):
    Workspaces.get_for_update_projects(workspace_owner, workspace.id)


def test_get_for_update_projects_blocks_developer(workspace):
    developer = UserFactory.create()
    WorkspaceUsers.add(developer, workspace.id, "developer")

    with pytest.raises(UnauthorizedError):
        Workspaces.get_for_update_projects(developer, workspace.id)


def test_can_create_workspace_user(workspace, workspace_owner):
    user_data = {
        "first_name": "New",
        "last_name": "User",
        "email": "new.user@mail.com",
        "workspace_role": "developer",
        "dod_id": "1234567890",
    }

    new_member = Workspaces.create_member(workspace_owner, workspace, user_data)
    assert new_member.workspace == workspace
    assert new_member.user.provisional


def test_can_add_existing_user_to_workspace(workspace, workspace_owner):
    user = UserFactory.create()
    user_data = {
        "first_name": "New",
        "last_name": "User",
        "email": "new.user@mail.com",
        "workspace_role": "developer",
        "dod_id": user.dod_id,
    }

    new_member = Workspaces.create_member(workspace_owner, workspace, user_data)
    assert new_member.workspace == workspace
    assert new_member.user.email == user.email
    assert not new_member.user.provisional


def test_need_permission_to_create_workspace_user(workspace, workspace_owner):
    random_user = UserFactory.create()

    user_data = {
        "first_name": "New",
        "last_name": "User",
        "email": "new.user@mail.com",
        "workspace_role": "developer",
        "dod_id": "1234567890",
    }

    with pytest.raises(UnauthorizedError):
        Workspaces.create_member(random_user, workspace, user_data)


def test_update_workspace_user_role(workspace, workspace_owner):
    user_data = {
        "first_name": "New",
        "last_name": "User",
        "email": "new.user@mail.com",
        "workspace_role": "developer",
        "dod_id": "1234567890",
    }
    member = Workspaces.create_member(workspace_owner, workspace, user_data)
    role_name = "admin"

    updated_member = Workspaces.update_member(
        workspace_owner, workspace, member, role_name
    )
    assert updated_member.workspace == workspace
    assert updated_member.role == role_name


def test_need_permission_to_update_workspace_user_role(workspace, workspace_owner):
    random_user = UserFactory.create()
    user_data = {
        "first_name": "New",
        "last_name": "User",
        "email": "new.user@mail.com",
        "workspace_role": "developer",
        "dod_id": "1234567890",
    }
    member = Workspaces.create_member(workspace_owner, workspace, user_data)
    role_name = "developer"

    with pytest.raises(UnauthorizedError):
        Workspaces.update_member(random_user, workspace, member, role_name)


def test_owner_can_view_workspace_members(workspace, workspace_owner):
    workspace_owner = UserFactory.create()
    workspace = Workspaces.create(RequestFactory.create(creator=workspace_owner))
    workspace = Workspaces.get_with_members(workspace_owner, workspace.id)

    assert workspace


def test_ccpo_can_view_workspace_members(workspace, workspace_owner):
    ccpo = UserFactory.from_atat_role("ccpo")
    assert Workspaces.get_with_members(ccpo, workspace.id)


def test_random_user_cannot_view_workspace_members(workspace):
    developer = UserFactory.from_atat_role("developer")

    with pytest.raises(UnauthorizedError):
        workspace = Workspaces.get_with_members(developer, workspace.id)


def test_scoped_workspace_only_returns_a_users_projects_and_environments(
    workspace, workspace_owner
):
    new_project = Projects.create(
        workspace_owner,
        workspace,
        "My Project",
        "My project",
        ["dev", "staging", "prod"],
    )
    Projects.create(
        workspace_owner,
        workspace,
        "My Project 2",
        "My project 2",
        ["dev", "staging", "prod"],
    )
    developer = UserFactory.from_atat_role("developer")
    dev_environment = Environments.add_member(
        new_project.environments[0], developer, "developer"
    )

    scoped_workspace = Workspaces.get(developer, workspace.id)

    # Should only return the project and environment in which the user has an
    # environment role.
    assert scoped_workspace.projects == [new_project]
    assert scoped_workspace.projects[0].environments == [dev_environment]


def test_scoped_workspace_returns_all_projects_for_workspace_admin(
    workspace, workspace_owner
):
    for _ in range(5):
        Projects.create(
            workspace_owner,
            workspace,
            "My Project",
            "My project",
            ["dev", "staging", "prod"],
        )

    admin = Workspaces.add_member(
        workspace, UserFactory.from_atat_role("default"), "admin"
    ).user
    scoped_workspace = Workspaces.get(admin, workspace.id)

    assert len(scoped_workspace.projects) == 5
    assert len(scoped_workspace.projects[0].environments) == 3


def test_scoped_workspace_returns_all_projects_for_workspace_owner(
    workspace, workspace_owner
):
    for _ in range(5):
        Projects.create(
            workspace_owner,
            workspace,
            "My Project",
            "My project",
            ["dev", "staging", "prod"],
        )

    scoped_workspace = Workspaces.get(workspace_owner, workspace.id)

    assert len(scoped_workspace.projects) == 5
    assert len(scoped_workspace.projects[0].environments) == 3


def test_for_user_returns_assigned_workspaces_for_user(workspace, workspace_owner):
    bob = UserFactory.from_atat_role("default")
    Workspaces.add_member(workspace, bob, "developer")
    Workspaces.create(RequestFactory.create())
    Workspaces.accept_workspace_role(bob, workspace)

    bobs_workspaces = Workspaces.for_user(bob)

    assert len(bobs_workspaces) == 1


def test_for_user_does_not_return_unaccepted_workspaces(workspace, workspace_owner):
    bob = UserFactory.from_atat_role("default")
    Workspaces.add_member(workspace, bob, "developer")
    Workspaces.create(RequestFactory.create())
    bobs_workspaces = Workspaces.for_user(bob)

    assert len(bobs_workspaces) == 0


def test_for_user_returns_all_workspaces_for_ccpo(workspace, workspace_owner):
    sam = UserFactory.from_atat_role("ccpo")
    Workspaces.create(RequestFactory.create())

    sams_workspaces = Workspaces.for_user(sam)
    assert len(sams_workspaces) == 2


def test_get_for_update_information():
    workspace_owner = UserFactory.create()
    workspace = Workspaces.create(RequestFactory.create(creator=workspace_owner))
    owner_ws = Workspaces.get_for_update_information(workspace_owner, workspace.id)
    assert workspace == owner_ws

    admin = UserFactory.create()
    Workspaces.add_member(workspace, admin, "admin")
    admin_ws = Workspaces.get_for_update_information(admin, workspace.id)
    assert workspace == admin_ws

    ccpo = UserFactory.from_atat_role("ccpo")
    with pytest.raises(UnauthorizedError):
        Workspaces.get_for_update_information(ccpo, workspace.id)


def test_can_create_workspaces_with_matching_names():
    workspace_name = "Great Workspace"
    Workspaces.create(RequestFactory.create(), name=workspace_name)
    Workspaces.create(RequestFactory.create(), name=workspace_name)
