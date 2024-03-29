from flask import current_app as app
import pendulum

from atst.database import db
from atst.queue import celery
from atst.models import (
    EnvironmentJobFailure,
    EnvironmentRoleJobFailure,
    EnvironmentRole,
)
from atst.domain.csp.cloud import CloudProviderInterface, GeneralCSPException
from atst.domain.environments import Environments
from atst.domain.environment_roles import EnvironmentRoles
from atst.models.utils import claim_for_update
from atst.utils.localization import translate


class RecordEnvironmentFailure(celery.Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if "environment_id" in kwargs:
            failure = EnvironmentJobFailure(
                environment_id=kwargs["environment_id"], task_id=task_id
            )
            db.session.add(failure)
            db.session.commit()


class RecordEnvironmentRoleFailure(celery.Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if "environment_role_id" in kwargs:
            failure = EnvironmentRoleJobFailure(
                environment_role_id=kwargs["environment_role_id"], task_id=task_id
            )
            db.session.add(failure)
            db.session.commit()


@celery.task(ignore_result=True)
def send_mail(recipients, subject, body):
    app.mailer.send(recipients, subject, body)


@celery.task(ignore_result=True)
def send_notification_mail(recipients, subject, body):
    app.logger.info(
        "Sending a notification to these recipients: {}\n\nSubject: {}\n\n{}".format(
            recipients, subject, body
        )
    )
    app.mailer.send(recipients, subject, body)


def do_create_environment(csp: CloudProviderInterface, environment_id=None):
    environment = Environments.get(environment_id)

    with claim_for_update(environment) as environment:

        if environment.cloud_id is not None:
            # TODO: Return value for this?
            return

        user = environment.creator

        # we'll need to do some checking in this job for cases where it's retrying
        # when a failure occured after some successful steps
        # (e.g. if environment.cloud_id is not None, then we can skip first step)

        # credentials either from a given user or pulled from config?
        # if using global creds, do we need to log what user authorized action?
        atat_root_creds = csp.root_creds()

        # user is needed because baseline root account in the environment will
        # be assigned to the requesting user, open question how to handle duplicate
        # email addresses across new environments
        csp_environment_id = csp.create_environment(atat_root_creds, user, environment)
        environment.cloud_id = csp_environment_id
        db.session.add(environment)
        db.session.commit()


def do_create_atat_admin_user(csp: CloudProviderInterface, environment_id=None):
    environment = Environments.get(environment_id)

    with claim_for_update(environment) as environment:
        atat_root_creds = csp.root_creds()

        atat_remote_root_user = csp.create_atat_admin_user(
            atat_root_creds, environment.cloud_id
        )
        environment.root_user_info = atat_remote_root_user
        db.session.add(environment)
        db.session.commit()


def render_email(template_path, context):
    return app.jinja_env.get_template(template_path).render(context)


def do_create_environment_baseline(csp: CloudProviderInterface, environment_id=None):
    environment = Environments.get(environment_id)

    with claim_for_update(environment) as environment:
        # ASAP switch to use remote root user for provisioning
        atat_remote_root_creds = environment.root_user_info["credentials"]

        baseline_info = csp.create_environment_baseline(
            atat_remote_root_creds, environment.cloud_id
        )
        environment.baseline_info = baseline_info
        body = render_email(
            "emails/application/environment_ready.txt", {"environment": environment}
        )
        app.mailer.send(
            [environment.creator.email], translate("email.environment_ready"), body
        )
        db.session.add(environment)
        db.session.commit()


def do_provision_user(csp: CloudProviderInterface, environment_role_id=None):
    environment_role = EnvironmentRoles.get_by_id(environment_role_id)

    with claim_for_update(environment_role) as environment_role:
        credentials = environment_role.environment.csp_credentials

        csp_user_id = csp.create_or_update_user(
            credentials, environment_role, environment_role.role
        )
        environment_role.csp_user_id = csp_user_id
        environment_role.status = EnvironmentRole.Status.COMPLETED
        db.session.add(environment_role)
        db.session.commit()


def do_work(fn, task, csp, **kwargs):
    try:
        fn(csp, **kwargs)
    except GeneralCSPException as e:
        raise task.retry(exc=e)


@celery.task(bind=True, base=RecordEnvironmentFailure)
def create_environment(self, environment_id=None):
    do_work(do_create_environment, self, app.csp.cloud, environment_id=environment_id)


@celery.task(bind=True, base=RecordEnvironmentFailure)
def create_atat_admin_user(self, environment_id=None):
    do_work(
        do_create_atat_admin_user, self, app.csp.cloud, environment_id=environment_id
    )


@celery.task(bind=True, base=RecordEnvironmentFailure)
def create_environment_baseline(self, environment_id=None):
    do_work(
        do_create_environment_baseline,
        self,
        app.csp.cloud,
        environment_id=environment_id,
    )


@celery.task(bind=True)
def provision_user(self, environment_role_id=None):
    do_work(
        do_provision_user, self, app.csp.cloud, environment_role_id=environment_role_id
    )


@celery.task(bind=True)
def dispatch_create_environment(self):
    for environment_id in Environments.get_environments_pending_creation(
        pendulum.now()
    ):
        create_environment.delay(environment_id=environment_id)


@celery.task(bind=True)
def dispatch_create_atat_admin_user(self):
    for environment_id in Environments.get_environments_pending_atat_user_creation(
        pendulum.now()
    ):
        create_atat_admin_user.delay(environment_id=environment_id)


@celery.task(bind=True)
def dispatch_create_environment_baseline(self):
    for environment_id in Environments.get_environments_pending_baseline_creation(
        pendulum.now()
    ):
        create_environment_baseline.delay(environment_id=environment_id)


@celery.task(bind=True)
def dispatch_provision_user(self):
    for (
        environment_role_id
    ) in EnvironmentRoles.get_environment_roles_pending_creation():
        provision_user.delay(environment_role_id=environment_role_id)
