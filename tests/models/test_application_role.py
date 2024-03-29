import pytest

from atst.domain.permission_sets import PermissionSets
from atst.domain.environment_roles import EnvironmentRoles
from atst.models.audit_event import AuditEvent

from tests.factories import *


@pytest.mark.audit_log
def test_has_application_role_history(session):
    owner = UserFactory.create()
    user = UserFactory.create()

    PortfolioFactory.create(
        owner=owner,
        applications=[
            {
                "name": "starkiller",
                "environments": [
                    {
                        "name": "bridge",
                        "members": [{"user": user, "role_name": "developer"}],
                    }
                ],
            }
        ],
    )

    app_role = user.application_roles[0]
    app_role.permission_sets = [
        PermissionSets.get(PermissionSets.EDIT_APPLICATION_TEAM)
    ]
    session.add(app_role)
    session.commit()

    changed_event = (
        session.query(AuditEvent)
        .filter(AuditEvent.resource_id == app_role.id, AuditEvent.action == "update")
        .one()
    )
    old_state, new_state = changed_event.changed_state["permission_sets"]
    assert old_state == [PermissionSets.VIEW_APPLICATION]
    assert new_state == [PermissionSets.EDIT_APPLICATION_TEAM]


def test_environment_roles():
    application = ApplicationFactory.create()
    environment1 = EnvironmentFactory.create(application=application)
    environment2 = EnvironmentFactory.create(application=application)
    user = UserFactory.create()
    application_role = ApplicationRoleFactory.create(application=application, user=user)
    environment_role1 = EnvironmentRoleFactory.create(
        environment=environment1, application_role=application_role
    )
    EnvironmentRoleFactory.create(
        environment=environment2, application_role=application_role, deleted=True
    )

    assert not EnvironmentRoles.get_by_user_and_environment(user.id, environment2.id)
