from sqlalchemy.orm.exc import NoResultFound

from atst.database import db
from atst.models import (
    EnvironmentRole,
    ApplicationRole,
    Environment,
    ApplicationRoleStatus,
)
from atst.domain.exceptions import NotFoundError
from uuid import UUID
from typing import List


class EnvironmentRoles(object):
    @classmethod
    def create(cls, application_role, environment, role):
        env_role = EnvironmentRole(
            application_role=application_role, environment=environment, role=role
        )
        return env_role

    @classmethod
    def get(cls, application_role_id, environment_id):
        existing_env_role = (
            db.session.query(EnvironmentRole)
            .filter(
                EnvironmentRole.application_role_id == application_role_id,
                EnvironmentRole.environment_id == environment_id,
                EnvironmentRole.deleted == False,
                EnvironmentRole.status != EnvironmentRole.Status.PENDING_DELETE,
            )
            .one_or_none()
        )
        return existing_env_role

    @classmethod
    def get_by_id(cls, id_) -> EnvironmentRole:
        try:
            return (
                db.session.query(EnvironmentRole).filter(EnvironmentRole.id == id_)
            ).one()
        except NoResultFound:
            raise NotFoundError(cls.resource_name)

    @classmethod
    def get_by_user_and_environment(cls, user_id, environment_id):
        existing_env_role = (
            db.session.query(EnvironmentRole)
            .join(ApplicationRole)
            .filter(
                ApplicationRole.user_id == user_id,
                EnvironmentRole.environment_id == environment_id,
                EnvironmentRole.deleted == False,
            )
            .one_or_none()
        )
        return existing_env_role

    @classmethod
    def _update_status(cls, environment_role, new_status):
        environment_role.status = new_status
        db.session.add(environment_role)
        db.session.commit()

        return environment_role

    @classmethod
    def delete(cls, application_role_id, environment_id):
        existing_env_role = EnvironmentRoles.get(application_role_id, environment_id)

        if existing_env_role:
            # TODO: Implement suspension
            existing_env_role.deleted = True
            cls._update_status(existing_env_role, EnvironmentRole.Status.PENDING_DELETE)
            db.session.add(existing_env_role)
            db.session.commit()
            return True
        else:
            return False

    @classmethod
    def get_for_application_member(cls, application_role_id):
        return (
            db.session.query(EnvironmentRole)
            .filter(EnvironmentRole.application_role_id == application_role_id)
            .filter(EnvironmentRole.deleted != True)
            .all()
        )

    @classmethod
    def get_environment_roles_pending_creation(cls) -> List[UUID]:
        results = (
            db.session.query(EnvironmentRole.id)
            .join(Environment)
            .join(ApplicationRole)
            .filter(Environment.deleted == False)
            .filter(Environment.baseline_info != None)
            .filter(EnvironmentRole.status == EnvironmentRole.Status.PENDING)
            .filter(ApplicationRole.status == ApplicationRoleStatus.ACTIVE)
            .all()
        )
        return [id_ for id_, in results]
