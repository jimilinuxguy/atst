from flask import url_for

from tests.factories import PortfolioFactory, ApplicationFactory, UserFactory
from unittest.mock import Mock
from atst.forms.data import ENV_ROLE_NO_ACCESS as NO_ACCESS
from atst.models.application_invitation import ApplicationInvitation


def test_get_name_and_description_form(client, user_session):
    portfolio = PortfolioFactory.create()
    user_session(portfolio.owner)
    response = client.get(
        url_for("applications.view_new_application_step_1", portfolio_id=portfolio.id)
    )
    assert response.status_code == 200


def test_get_name_and_description_form_for_update(client, user_session):
    name = "My Test Application"
    description = "This is the description of the test application."
    application = ApplicationFactory.create(name=name, description=description)
    user_session(application.portfolio.owner)
    response = client.get(
        url_for(
            "applications.view_new_application_step_1",
            portfolio_id=application.portfolio.id,
            application_id=application.id,
        )
    )
    assert response.status_code == 200
    assert name in response.data.decode()
    assert description in response.data.decode()


def test_post_name_and_description(client, user_session):
    portfolio = PortfolioFactory.create()
    user_session(portfolio.owner)
    response = client.post(
        url_for(
            "applications.create_new_application_step_1", portfolio_id=portfolio.id
        ),
        data={"name": "Test Application", "description": "This is only a test"},
    )
    assert response.status_code == 302
    assert len(portfolio.applications) == 1
    assert portfolio.applications[0].name == "Test Application"
    assert portfolio.applications[0].description == "This is only a test"


def test_post_name_and_description_for_update(client, session, user_session):
    application = ApplicationFactory.create()
    user_session(application.portfolio.owner)
    response = client.post(
        url_for(
            "applications.update_new_application_step_1",
            portfolio_id=application.portfolio.id,
            application_id=application.id,
        ),
        data={"name": "Test Application", "description": "This is only a test"},
    )
    assert response.status_code == 302

    session.refresh(application)
    assert application.name == "Test Application"
    assert application.description == "This is only a test"


def test_get_environments(client, user_session):
    application = ApplicationFactory.create()
    user_session(application.portfolio.owner)
    response = client.get(
        url_for(
            "applications.view_new_application_step_2",
            portfolio_id=application.portfolio.id,
            application_id=application.id,
        )
    )
    assert response.status_code == 200


def test_post_environments(client, session, user_session):
    application = ApplicationFactory.create(environments=[])
    user_session(application.portfolio.owner)
    response = client.post(
        url_for(
            "applications.update_new_application_step_2",
            portfolio_id=application.portfolio.id,
            application_id=application.id,
        ),
        data={
            "environment_names-0": "development",
            "environment_names-1": "staging",
            "environment_names-2": "production",
        },
    )
    assert response.status_code == 302
    session.refresh(application)
    assert len(application.environments) == 3


def test_get_members(client, session, user_session):
    application = ApplicationFactory.create()
    user_session(application.portfolio.owner)
    response = client.get(
        url_for(
            "applications.view_new_application_step_3", application_id=application.id
        )
    )
    assert response.status_code == 200


def test_post_member(monkeypatch, client, user_session, session):
    job_mock = Mock()
    monkeypatch.setattr("atst.jobs.send_mail.delay", job_mock)
    user = UserFactory.create()
    application = ApplicationFactory.create(
        environments=[{"name": "Naboo"}, {"name": "Endor"}]
    )
    (env, env_1) = application.environments

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
