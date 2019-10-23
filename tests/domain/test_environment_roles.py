import pytest

from atst.domain.environment_roles import EnvironmentRoles
from atst.models.environment_role import EnvironmentRole

from tests.factories import *


@pytest.fixture
def application_role():
    user = UserFactory.create()
    application = ApplicationFactory.create()
    return ApplicationRoleFactory.create(application=application, user=user)


@pytest.fixture
def environment(application_role):
    return EnvironmentFactory.create(application=application_role.application)


def test_create(application_role, environment, monkeypatch):

    environment_role = EnvironmentRoles.create(
        application_role, environment, "network admin"
    )
    assert environment_role.application_role == application_role
    assert environment_role.environment == environment
    assert environment_role.role == "network admin"


def test_get(application_role, environment):
    EnvironmentRoleFactory.create(
        application_role=application_role, environment=environment
    )

    environment_role = EnvironmentRoles.get(application_role.id, environment.id)
    assert environment_role
    assert environment_role.application_role == application_role
    assert environment_role.environment == environment


def test_get_by_user_and_environment(application_role, environment):
    expected_role = EnvironmentRoleFactory.create(
        application_role=application_role, environment=environment
    )
    actual_role = EnvironmentRoles.get_by_user_and_environment(
        application_role.user.id, environment.id
    )
    assert expected_role == actual_role


def test_delete(application_role, environment, monkeypatch):
    env_role = EnvironmentRoleFactory.create(
        application_role=application_role, environment=environment
    )
    assert EnvironmentRoles.delete(application_role.id, environment.id)
    assert env_role.status == EnvironmentRole.Status.PENDING_DELETE
    assert env_role.deleted
    assert not EnvironmentRoles.delete(application_role.id, environment.id)


def test_get_for_application_member(application_role, environment):
    EnvironmentRoleFactory.create(
        application_role=application_role, environment=environment
    )

    roles = EnvironmentRoles.get_for_application_member(application_role.id)
    assert len(roles) == 1
    assert roles[0].environment == environment
    assert roles[0].application_role == application_role


def test_get_for_application_member_does_not_return_deleted(
    application_role, environment
):
    EnvironmentRoleFactory.create(
        application_role=application_role, environment=environment, deleted=True
    )

    roles = EnvironmentRoles.get_for_application_member(application_role.id)
    assert len(roles) == 0
