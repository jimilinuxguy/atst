import uuid
from flask import url_for, get_flashed_messages
from unittest.mock import Mock
import datetime

from tests.factories import *

from atst.domain.applications import Applications
from atst.domain.application_roles import ApplicationRoles
from atst.domain.environment_roles import EnvironmentRoles
from atst.domain.common import Paginator
from atst.domain.permission_sets import PermissionSets
from atst.models.application_role import Status as ApplicationRoleStatus
from atst.models.environment_role import CSPRole
from atst.models.permissions import Permissions
from atst.forms.application import EditEnvironmentForm
from atst.forms.application_member import UpdateMemberForm
from atst.forms.data import ENV_ROLE_NO_ACCESS as NO_ACCESS
from atst.routes.applications.settings import filter_env_roles_form_data

from tests.utils import captured_templates


def test_updating_application_environments_success(client, user_session):
    portfolio = PortfolioFactory.create()
    application = ApplicationFactory.create(portfolio=portfolio)
    environment = EnvironmentFactory.create(application=application)

    user_session(portfolio.owner)

    form_data = {"name": "new name a"}

    response = client.post(
        url_for("applications.update_environment", environment_id=environment.id),
        data=form_data,
    )

    assert response.status_code == 302
    assert response.location == url_for(
        "applications.settings",
        application_id=application.id,
        _external=True,
        fragment="application-environments",
        _anchor="application-environments",
        active_toggler=environment.id,
        active_toggler_section="edit",
    )
    assert environment.name == "new name a"


def test_update_environment_failure(client, user_session):
    portfolio = PortfolioFactory.create()
    application = ApplicationFactory.create(portfolio=portfolio)
    environment = EnvironmentFactory.create(
        application=application, name="original name"
    )

    user_session(portfolio.owner)

    form_data = {"name": ""}

    response = client.post(
        url_for("applications.update_environment", environment_id=environment.id),
        data=form_data,
    )

    assert response.status_code == 400
    assert environment.name == "original name"


def test_application_settings(client, user_session):
    portfolio = PortfolioFactory.create()
    application = Applications.create(
        portfolio.owner,
        portfolio,
        "Snazzy Application",
        "A new application for me and my friends",
        {"env1", "env2"},
    )
    user_session(portfolio.owner)
    response = client.get(
        url_for("applications.settings", application_id=application.id)
    )
    assert response.status_code == 200
    # the assertion below is a quick check to prevent regressions -- this ensures that
    # the correct URL for creating a member for an application is _somewhere_ in
    # the settings page.
    assert (
        url_for("applications.create_member", application_id=application.id)
        in response.data.decode()
    )


def test_edit_application_environments_obj(app, client, user_session):
    portfolio = PortfolioFactory.create()
    application = Applications.create(
        portfolio.owner,
        portfolio,
        "Snazzy Application",
        "A new application for me and my friends",
        {"env"},
    )
    env = application.environments[0]
    app_role1 = ApplicationRoleFactory.create(application=application)
    env_role1 = EnvironmentRoleFactory.create(
        application_role=app_role1, environment=env, role=CSPRole.BASIC_ACCESS.value
    )
    app_role2 = ApplicationRoleFactory.create(application=application, user=None)
    invite = ApplicationInvitationFactory.create(role=app_role2)
    env_role2 = EnvironmentRoleFactory.create(
        application_role=app_role2, environment=env, role=CSPRole.NETWORK_ADMIN.value
    )

    user_session(portfolio.owner)

    with captured_templates(app) as templates:
        response = app.test_client().get(
            url_for("applications.settings", application_id=application.id)
        )

        assert response.status_code == 200
        _, context = templates[-1]

        env_obj = context["environments_obj"][0]
        assert env_obj["name"] == env.name
        assert env_obj["id"] == env.id
        assert isinstance(env_obj["edit_form"], EditEnvironmentForm)
        assert (
            env_obj["members"].sort()
            == [app_role1.user_name, app_role2.user_name].sort()
        )
        assert isinstance(context["audit_events"], Paginator)


def test_get_members_data(app, client, user_session):
    user = UserFactory.create()
    application = ApplicationFactory.create(
        environments=[
            {
                "name": "testing",
                "members": [{"user": user, "role_name": CSPRole.BASIC_ACCESS.value}],
            }
        ]
    )
    environment = application.environments[0]
    app_role = ApplicationRoles.get(user_id=user.id, application_id=application.id)
    env_role = EnvironmentRoles.get(
        application_role_id=app_role.id, environment_id=environment.id
    )

    user_session(application.portfolio.owner)

    with captured_templates(app) as templates:
        response = app.test_client().get(
            url_for("applications.settings", application_id=application.id)
        )

        assert response.status_code == 200
        _, context = templates[-1]

        member = context["members"][0]
        assert member["role_id"] == app_role.id
        assert member["user_name"] == user.full_name
        assert member["permission_sets"] == {
            "perms_team_mgmt": False,
            "perms_env_mgmt": False,
            "perms_del_env": False,
        }
        assert member["environment_roles"] == [
            {
                "environment_id": str(environment.id),
                "environment_name": environment.name,
                "role": env_role.role,
            }
        ]
        assert member["role_status"]
        assert isinstance(member["form"], UpdateMemberForm)


def test_user_with_permission_can_update_application(client, user_session):
    owner = UserFactory.create()
    portfolio = PortfolioFactory.create(
        owner=owner,
        applications=[
            {
                "name": "Awesome Application",
                "description": "It's really awesome!",
                "environments": [{"name": "dev"}, {"name": "prod"}],
            }
        ],
    )
    application = portfolio.applications[0]
    user_session(owner)
    response = client.post(
        url_for("applications.update", application_id=application.id),
        data={
            "name": "Really Cool Application",
            "description": "A very cool application.",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert application.name == "Really Cool Application"
    assert application.description == "A very cool application."


def test_user_without_permission_cannot_update_application(client, user_session):
    dev = UserFactory.create()
    owner = UserFactory.create()
    portfolio = PortfolioFactory.create(
        owner=owner,
        members=[{"user": dev, "role_name": "developer"}],
        applications=[
            {
                "name": "Great Application",
                "description": "Cool stuff happening here!",
                "environments": [{"name": "dev"}, {"name": "prod"}],
            }
        ],
    )
    application = portfolio.applications[0]
    user_session(dev)
    response = client.post(
        url_for("applications.update", application_id=application.id),
        data={"name": "New Name", "description": "A new description."},
        follow_redirects=True,
    )

    assert response.status_code == 404
    assert application.name == "Great Application"
    assert application.description == "Cool stuff happening here!"


def test_user_can_only_access_apps_in_their_portfolio(client, user_session):
    portfolio = PortfolioFactory.create()
    other_portfolio = PortfolioFactory.create(
        applications=[
            {
                "name": "Awesome Application",
                "description": "More cool stuff happening here!",
                "environments": [{"name": "dev"}],
            }
        ]
    )
    other_application = other_portfolio.applications[0]
    user_session(portfolio.owner)

    # user can't view application edit form
    response = client.get(
        url_for("applications.settings", application_id=other_application.id)
    )
    assert response.status_code == 404

    # user can't post update application form
    time_updated = other_application.time_updated
    response = client.post(
        url_for("applications.update", application_id=other_application.id),
        data={"name": "New Name", "description": "A new description."},
    )
    assert response.status_code == 404
    assert time_updated == other_application.time_updated


def test_delete_application(client, user_session):
    user = UserFactory.create()
    port = PortfolioFactory.create(
        owner=user,
        applications=[
            {
                "name": "mos eisley",
                "environments": [
                    {"name": "bar"},
                    {"name": "booth"},
                    {"name": "band stage"},
                ],
            }
        ],
    )
    application = port.applications[0]
    user_session(user)

    response = client.post(
        url_for("applications.delete", application_id=application.id)
    )
    # appropriate response and redirect
    assert response.status_code == 302
    assert response.location == url_for(
        "applications.portfolio_applications", portfolio_id=port.id, _external=True
    )
    # appropriate flash message
    message = get_flashed_messages()[0]
    assert "deleted" in message["message"]
    assert application.name in message["message"]
    # app and envs are soft deleted
    assert len(port.applications) == 0
    assert len(application.environments) == 0


def test_new_environment(client, user_session):
    user = UserFactory.create()
    portfolio = PortfolioFactory(owner=user)
    application = ApplicationFactory.create(portfolio=portfolio)
    num_envs = len(application.environments)

    user_session(user)
    response = client.post(
        url_for("applications.new_environment", application_id=application.id),
        data={"name": "dabea"},
    )

    assert response.status_code == 302
    assert len(application.environments) == num_envs + 1


def test_new_environment_with_bad_data(client, user_session):
    user = UserFactory.create()
    portfolio = PortfolioFactory(owner=user)
    application = ApplicationFactory.create(portfolio=portfolio)
    num_envs = len(application.environments)

    user_session(user)
    response = client.post(
        url_for("applications.new_environment", application_id=application.id),
        data={"name": None},
    )

    assert response.status_code == 400
    assert len(application.environments) == num_envs


def test_delete_environment(client, user_session):
    user = UserFactory.create()
    portfolio = PortfolioFactory(owner=user)
    application = ApplicationFactory.create(portfolio=portfolio)
    environment = EnvironmentFactory.create(application=application)

    user_session(user)

    response = client.post(
        url_for("applications.delete_environment", environment_id=environment.id)
    )

    # appropriate response and redirect
    assert response.status_code == 302
    assert response.location == url_for(
        "applications.settings",
        application_id=application.id,
        _anchor="application-environments",
        _external=True,
        fragment="application-environments",
    )
    # appropriate flash message
    message = get_flashed_messages()[0]
    assert "deleted" in message["message"]
    assert environment.name in message["message"]
    # deletes environment
    assert len(application.environments) == 0


def test_create_member(monkeypatch, client, user_session, session):
    job_mock = Mock()
    monkeypatch.setattr("atst.jobs.send_mail.delay", job_mock)
    user = UserFactory.create()
    application = ApplicationFactory.create(
        environments=[{"name": "Naboo"}, {"name": "Endor"}]
    )
    env = application.environments[0]
    env_1 = application.environments[1]

    user_session(application.portfolio.owner)

    response = client.post(
        url_for("applications.create_member", application_id=application.id),
        data={
            "user_data-first_name": user.first_name,
            "user_data-last_name": user.last_name,
            "user_data-dod_id": user.dod_id,
            "user_data-email": user.email,
            "environment_roles-0-environment_id": env.id,
            "environment_roles-0-role": "Basic Access",
            "environment_roles-0-environment_name": env.name,
            "environment_roles-1-environment_id": env_1.id,
            "environment_roles-1-role": NO_ACCESS,
            "environment_roles-1-environment_name": env_1.name,
            "perms_env_mgmt": True,
            "perms_team_mgmt": True,
            "perms_del_env": True,
        },
    )

    assert response.status_code == 302
    expected_url = url_for(
        "applications.settings",
        application_id=application.id,
        fragment="application-members",
        _anchor="application-members",
        _external=True,
    )
    assert response.location == expected_url
    assert len(application.roles) == 1
    environment_roles = application.roles[0].environment_roles
    assert len(environment_roles) == 1
    assert environment_roles[0].environment == env

    invitation = (
        session.query(ApplicationInvitation).filter_by(dod_id=user.dod_id).one()
    )
    assert invitation.role.application == application

    assert job_mock.called


def test_remove_member_success(client, user_session):
    user = UserFactory.create()
    application = ApplicationFactory.create()
    application_role = ApplicationRoleFactory.create(application=application, user=user)

    user_session(application.portfolio.owner)

    response = client.post(
        url_for(
            "applications.remove_member",
            application_id=application.id,
            application_role_id=application_role.id,
        )
    )

    assert response.status_code == 302
    assert response.location == url_for(
        "applications.settings",
        _anchor="application-members",
        _external=True,
        application_id=application.id,
        fragment="application-members",
    )


def test_remove_new_member_success(client, user_session):
    application = ApplicationFactory.create()
    application_role = ApplicationRoleFactory.create(application=application, user=None)

    user_session(application.portfolio.owner)

    response = client.post(
        url_for(
            "applications.remove_member",
            application_id=application.id,
            application_role_id=application_role.id,
        )
    )

    assert response.status_code == 302
    assert response.location == url_for(
        "applications.settings",
        _anchor="application-members",
        _external=True,
        application_id=application.id,
        fragment="application-members",
    )


def test_remove_member_failure(client, user_session):
    user = UserFactory.create()
    application = ApplicationFactory.create()

    user_session(application.portfolio.owner)

    response = client.post(
        url_for(
            "applications.remove_member",
            application_id=application.id,
            application_role_id=uuid.uuid4(),
        )
    )

    assert response.status_code == 404


def test_update_member(client, user_session, session):
    role = PermissionSets.get(PermissionSets.EDIT_APPLICATION_TEAM)
    # create an app role with only edit team perms
    app_role = ApplicationRoleFactory.create(permission_sets=[role])
    application = app_role.application
    env = EnvironmentFactory.create(application=application)
    env_1 = EnvironmentFactory.create(application=application)
    env_2 = EnvironmentFactory.create(application=application)
    # add user to two of the environments: env and env_1
    EnvironmentRoleFactory.create(
        environment=env, application_role=app_role, role=CSPRole.BASIC_ACCESS.value
    )
    suspended_role = EnvironmentRoleFactory.create(
        environment=env_1, application_role=app_role, role=CSPRole.BASIC_ACCESS.value
    )

    user_session(application.portfolio.owner)
    # update the user's app permissions to have edit team and env perms
    # update user's role in env, remove user from env_1, and add user to env_2
    response = client.post(
        url_for(
            "applications.update_member",
            application_id=application.id,
            application_role_id=app_role.id,
        ),
        data={
            "environment_roles-0-environment_id": env.id,
            "environment_roles-0-role": CSPRole.TECHNICAL_READ.value,
            "environment_roles-0-environment_name": env.name,
            "environment_roles-1-environment_id": env_1.id,
            "environment_roles-1-environment_name": env_1.name,
            "environment_roles-1-deleted": "True",
            "environment_roles-2-environment_id": env_2.id,
            "environment_roles-2-role": CSPRole.NETWORK_ADMIN.value,
            "environment_roles-2-environment_name": env_2.name,
            "perms_env_mgmt": True,
            "perms_team_mgmt": True,
            "perms_del_env": True,
        },
    )

    assert response.status_code == 302
    expected_url = url_for(
        "applications.settings",
        application_id=application.id,
        fragment="application-members",
        _anchor="application-members",
        _external=True,
    )
    assert response.location == expected_url
    # make sure new application role was not created
    assert len(application.roles) == 1
    # check that new app perms were added
    assert bool(app_role.has_permission_set(PermissionSets.EDIT_APPLICATION_TEAM))
    assert bool(
        app_role.has_permission_set(PermissionSets.EDIT_APPLICATION_ENVIRONMENTS)
    )
    assert bool(
        app_role.has_permission_set(PermissionSets.DELETE_APPLICATION_ENVIRONMENTS)
    )

    environment_roles = application.roles[0].environment_roles
    # make sure that old env role was deleted and there are only 2 env roles
    assert len(environment_roles) == 2
    # check that the user has roles in the correct envs
    assert environment_roles[0].environment in [env, env_2]
    assert environment_roles[1].environment in [env, env_2]
    assert suspended_role.status == EnvironmentRole.Status.PENDING_DELETE
    assert suspended_role.deleted


def test_revoke_invite(client, user_session):
    invite = ApplicationInvitationFactory.create()
    app_role = invite.role
    application = app_role.application

    user_session(application.portfolio.owner)
    response = client.post(
        url_for(
            "applications.revoke_invite",
            application_id=application.id,
            application_role_id=app_role.id,
        )
    )

    assert invite.is_revoked
    assert app_role.status == ApplicationRoleStatus.DISABLED
    assert app_role.deleted


def test_filter_environment_roles():
    application_role = ApplicationRoleFactory.create(user=None)
    application_role2 = ApplicationRoleFactory.create(
        user=None, application=application_role.application
    )
    application_role3 = ApplicationRoleFactory.create(
        user=None, application=application_role.application
    )

    environment = EnvironmentFactory.create(application=application_role.application)

    EnvironmentRoleFactory.create(
        environment=environment, application_role=application_role
    )
    EnvironmentRoleFactory.create(
        environment=environment, application_role=application_role2
    )

    environment_data = filter_env_roles_form_data(application_role, [environment])
    assert environment_data[0]["role"] != "No Access"

    environment_data = filter_env_roles_form_data(application_role3, [environment])
    assert environment_data[0]["role"] == "No Access"

    def test_resend_invite(client, user_session, session):
        user = UserFactory.create()
        # need to set the time created to yesterday, otherwise the original invite and resent
        # invite have the same time_created and then we can't rely on time to order the invites
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        invite = ApplicationInvitationFactory.create(
            user=user, time_created=yesterday, email="original@example.com"
        )
        app_role = invite.role
        application = app_role.application

        user_session(application.portfolio.owner)
        response = client.post(
            url_for(
                "applications.resend_invite",
                application_id=application.id,
                application_role_id=app_role.id,
            ),
            data={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "dod_id": user.dod_id,
                "email": "an_email@example.com",
            },
        )

        session.refresh(app_role)
        assert response.status_code == 302
        assert invite.is_revoked
        assert app_role.status == ApplicationRoleStatus.PENDING
        assert app_role.latest_invitation.email == "an_email@example.com"
