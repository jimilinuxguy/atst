from typing import Dict
from uuid import uuid4

from atst.models.environment_role import CSPRole
from atst.models.user import User
from atst.models.environment import Environment
from atst.models.environment_role import EnvironmentRole


class GeneralCSPException(Exception):
    pass


class OperationInProgressException(GeneralCSPException):
    """Throw this for instances when the CSP reports that the current entity is already
    being operated on/created/deleted/etc
    """

    def __init__(self, operation_desc):
        self.operation_desc = operation_desc

    @property
    def message(self):
        return "An operation for this entity is already in progress: {}".format(
            self.operation_desc
        )


class AuthenticationException(GeneralCSPException):
    """Throw this for instances when there is a problem with the auth credentials:
    * Missing credentials
    * Incorrect credentials
    * Other credential problems
    """

    def __init__(self, auth_error):
        self.auth_error = auth_error

    @property
    def message(self):
        return "An error occurred with authentication: {}".format(self.auth_error)


class AuthorizationException(GeneralCSPException):
    """Throw this for instances when the current credentials are not authorized
    for the current action.
    """

    def __init__(self, auth_error):
        self.auth_error = auth_error

    @property
    def message(self):
        return "An error occurred with authorization: {}".format(self.auth_error)


class ConnectionException(GeneralCSPException):
    """A general problem with the connection, timeouts or unresolved endpoints
    """

    def __init__(self, connection_error):
        self.connection_error = connection_error

    @property
    def message(self):
        return "Could not connect to cloud provider: {}".format(self.connection_error)


class UnknownServerException(GeneralCSPException):
    """An error occured on the CSP side (5xx) and we don't know why
    """

    def __init__(self, server_error):
        self.server_error = server_error

    @property
    def message(self):
        return "A server error occured: {}".format(self.server_error)


class EnvironmentCreationException(GeneralCSPException):
    """If there was an error in creating the environment
    """

    def __init__(self, env_identifier, reason):
        self.env_identifier = env_identifier
        self.reason = reason

    @property
    def message(self):
        return "The envionment {} couldn't be created: {}".format(
            self.env_identifier, self.reason
        )


class UserProvisioningException(GeneralCSPException):
    """Failed to provision a user
    """

    def __init__(self, env_identifier, user_identifier, reason):
        self.env_identifier = env_identifier
        self.user_identifier = user_identifier
        self.reason = reason

    @property
    def message(self):
        return "Failed to create user {} for environment {}: {}".format(
            self.user_identifier, self.env_identifier, self.reason
        )


class UserRemovalException(GeneralCSPException):
    """Failed to remove a user
    """

    def __init__(self, user_csp_id, reason):
        self.user_csp_id = user_csp_id
        self.reason = reason

    @property
    def message(self):
        return "Failed to suspend or delete user {}: {}".format(
            self.user_csp_id, self.reason
        )


class BaselineProvisionException(GeneralCSPException):
    """If there's any issues standing up whatever is required
    for an environment baseline
    """

    def __init__(self, env_identifier, reason):
        self.env_identifier = env_identifier
        self.reason = reason

    @property
    def message(self):
        return "Could not complete baseline provisioning for environment ({}): {}".format(
            self.env_identifier, self.reason
        )


class CloudProviderInterface:
    def root_creds() -> Dict:
        raise NotImplementedError()

    def create_environment(
        self, auth_credentials: Dict, user: User, environment: Environment
    ) -> str:
        """Create a new environment in the CSP.

        Arguments:
            auth_credentials -- Object containing CSP account credentials
            user -- ATAT user authorizing the environment creation
            environment -- ATAT Environment model

        Returns:
            string: ID of created environment

        Raises:
            AuthenticationException: Problem with the credentials
            AuthorizationException: Credentials not authorized for current action(s)
            ConnectionException: Issue with the CSP API connection
            UnknownServerException: Unknown issue on the CSP side
            EnvironmentExistsException: Environment already exists and has been created
        """
        raise NotImplementedError()

    def create_atat_admin_user(
        self, auth_credentials: Dict, csp_environment_id: str
    ) -> Dict:
        """Creates a new, programmatic user in the CSP. Grants this user full permissions to administer
        the CSP.

        Arguments:
            auth_credentials -- Object containing CSP account credentials
            csp_environment_id -- ID of the CSP Environment the admin user should be created in

        Returns:
            object: Object representing new remote admin user, including credentials
            Something like:
            {
                "user_id": string,
                "credentials": dict, # structure TBD based on csp
            }

        Raises:
            AuthenticationException: Problem with the credentials
            AuthorizationException: Credentials not authorized for current action(s)
            ConnectionException: Issue with the CSP API connection
            UnknownServerException: Unknown issue on the CSP side
            UserProvisioningException: Problem creating the root user
        """
        raise NotImplementedError()

    def create_environment_baseline(
        self, auth_credentials: Dict, csp_environment_id: str
    ) -> Dict:
        """Provision the necessary baseline entities (such as roles) in the given environment

        Arguments:
            auth_credentials -- Object containing CSP account credentials
            csp_environment_id -- ID of the CSP Environment to provision roles against.

        Returns:
            dict: Returns dict that associates the resource identities with their ATAT representations.
        Raises:
            AuthenticationException: Problem with the credentials
            AuthorizationException: Credentials not authorized for current action(s)
            ConnectionException: Issue with the CSP API connection
            UnknownServerException: Unknown issue on the CSP side
            BaselineProvisionException: Specific issue occurred with some aspect of baseline setup
        """
        raise NotImplementedError()

    def create_or_update_user(
        self, auth_credentials: Dict, user_info: EnvironmentRole, csp_role_id: str
    ) -> str:
        """Creates a user or updates an existing user's role.

        Arguments:
            auth_credentials -- Object containing CSP account credentials
            user_info -- instance of EnvironmentRole containing user data
                         if it has a csp_user_id it will try to update that user
            csp_role_id -- The id of the role the user should be given in the CSP

        Returns:
            string: Returns the interal csp_user_id of the created/updated user account

        Raises:
            AuthenticationException: Problem with the credentials
            AuthorizationException: Credentials not authorized for current action(s)
            ConnectionException: Issue with the CSP API connection
            UnknownServerException: Unknown issue on the CSP side
            UserProvisioningException: User couldn't be created or modified
        """
        raise NotImplementedError()

    def suspend_user(self, auth_credentials: Dict, csp_user_id: str) -> bool:
        """Revoke all privileges for a user. Used to prevent user access while a full
        delete is being processed.

        Arguments:
            auth_credentials -- Object containing CSP account credentials
            csp_user_id -- CSP internal user identifier

        Returns:
            bool -- True on success

        Raises:
            AuthenticationException: Problem with the credentials
            AuthorizationException: Credentials not authorized for current action(s)
            ConnectionException: Issue with the CSP API connection
            UnknownServerException: Unknown issue on the CSP side
            UserRemovalException: User couldn't be suspended
        """
        raise NotImplementedError()

    def delete_user(self, auth_credentials: Dict, csp_user_id: str) -> bool:
        """Given the csp-internal id for a user, initiate user deletion.

        Arguments:
            auth_credentials -- Object containing CSP account credentials
            csp_user_id -- CSP internal user identifier

        Returns:
            bool -- True on success

        Raises:
            AuthenticationException: Problem with the credentials
            AuthorizationException: Credentials not authorized for current action(s)
            ConnectionException: Issue with the CSP API connection
            UnknownServerException: Unknown issue on the CSP side
            UserRemovalException: User couldn't be removed
        """
        raise NotImplementedError()

    def get_calculator_url(self) -> str:
        """Returns the calculator url for the CSP.
        This will likely be a static property elsewhere once a CSP is chosen.
        """
        raise NotImplementedError()

    def get_environment_login_url(self, environment) -> str:
        """Returns the login url for a given environment
        This may move to be a computed property on the Environment domain object
        """
        raise NotImplementedError()


class MockCloudProvider(CloudProviderInterface):

    # TODO: All of these constants
    AUTHENTICATION_EXCEPTION = AuthenticationException("Authentication failure.")
    AUTHORIZATION_EXCEPTION = AuthorizationException("Not authorized.")
    NETWORK_EXCEPTION = ConnectionException("Network failure.")
    SERVER_EXCEPTION = UnknownServerException("Not our fault.")

    SERVER_FAILURE_PCT = 1
    NETWORK_FAILURE_PCT = 7
    ENV_CREATE_FAILURE_PCT = 12
    ATAT_ADMIN_CREATE_FAILURE_PCT = 12
    UNAUTHORIZED_RATE = 2

    def __init__(self, config, with_delay=True, with_failure=True):
        from time import sleep
        import random

        self._with_delay = with_delay
        self._with_failure = with_failure
        self._sleep = sleep
        self._random = random

    def root_creds(self):
        return self._auth_credentials

    def create_environment(self, auth_credentials, user, environment):
        self._authorize(auth_credentials)

        self._delay(1, 5)
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(
            self.ENV_CREATE_FAILURE_PCT,
            EnvironmentCreationException(
                environment.id, "Could not create environment."
            ),
        )
        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)

        return self._id()

    def create_atat_admin_user(self, auth_credentials, csp_environment_id):
        self._authorize(auth_credentials)

        self._delay(1, 5)
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(
            self.ATAT_ADMIN_CREATE_FAILURE_PCT,
            UserProvisioningException(
                csp_environment_id, "atat_admin", "Could not create admin user."
            ),
        )

        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)

        return {"id": self._id(), "credentials": self._auth_credentials}

    def create_environment_baseline(self, auth_credentials, csp_environment_id):
        self._authorize(auth_credentials)

        self._delay(1, 5)
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(
            self.ATAT_ADMIN_CREATE_FAILURE_PCT,
            BaselineProvisionException(
                csp_environment_id, "Could not create environment baseline."
            ),
        )

        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)
        return {
            CSPRole.BASIC_ACCESS.value: self._id(),
            CSPRole.NETWORK_ADMIN.value: self._id(),
            CSPRole.BUSINESS_READ.value: self._id(),
            CSPRole.TECHNICAL_READ.value: self._id(),
        }

    def create_or_update_user(self, auth_credentials, user_info, csp_role_id):
        self._authorize(auth_credentials)

        self._delay(1, 5)
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)
        self._maybe_raise(
            self.ATAT_ADMIN_CREATE_FAILURE_PCT,
            UserProvisioningException(
                user_info.environment.id,
                user_info.application_role.user_id,
                "Could not create user.",
            ),
        )

        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)
        return self._id()

    def suspend_user(self, auth_credentials, csp_user_id):
        self._authorize(auth_credentials)
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)

        self._maybe_raise(
            self.ATAT_ADMIN_CREATE_FAILURE_PCT,
            UserRemovalException(csp_user_id, "Could not suspend user."),
        )

        return self._maybe(12)

    def delete_user(self, auth_credentials, csp_user_id):
        self._authorize(auth_credentials)
        self._maybe_raise(self.NETWORK_FAILURE_PCT, self.NETWORK_EXCEPTION)
        self._maybe_raise(self.SERVER_FAILURE_PCT, self.SERVER_EXCEPTION)

        self._maybe_raise(
            self.ATAT_ADMIN_CREATE_FAILURE_PCT,
            UserRemovalException(csp_user_id, "Could not delete user."),
        )

        self._maybe_raise(self.UNAUTHORIZED_RATE, self.AUTHORIZATION_EXCEPTION)
        return self._maybe(12)

    def get_calculator_url(self):
        return "https://www.rackspace.com/en-us/calculator"

    def get_environment_login_url(self, environment):
        """Returns the login url for a given environment
        """
        return "https://www.mycloud.com/my-env-login"

    def _id(self):
        return uuid4().hex

    def _delay(self, min_secs, max_secs):
        if self._with_delay:
            duration = self._random.randrange(min_secs, max_secs)
            self._sleep(duration)

    def _maybe(self, pct):
        return not self._with_failure or self._random.randrange(0, 100) < pct

    def _maybe_raise(self, pct, exc):
        if self._with_failure and self._maybe(pct):
            raise exc

    @property
    def _auth_credentials(self):
        return {"username": "mock-cloud", "pass": "shh"}

    def _authorize(self, credentials):
        self._delay(1, 5)
        if credentials != self._auth_credentials:
            raise self.AUTHENTICATION_EXCEPTION


# Suspect this would change if rewarded
AZURE_ENVIRONMENT = "AZURE_PUBLIC_CLOUD"
SUBSCRIPTION_ID_REGEX = re.compile(
    "subscriptions\/([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})",
    re.I,
)


class AzureCloudProvider(CloudProviderInterface):
    def __init__(self, config):
        self.config = config

        self.client_id = config["AZURE_CLIENT_ID"]
        self.secret_key = config["AZURE_SECRET_KEY"]
        self.tenant_id = config["AZURE_TENANT_ID"]

        import azure.mgmt as mgmt
        import azure.common.credentials as credentials

        self.azure_mgmt = mgmt
        self.azure_credentials = credentials

    def root_creds(self):
        return {
            "client_id": self.client_id,
            "secret_key": self.secret_key,
            "tenant_id": self.tenant_id,
        }

    def create_environment(
        self, auth_credentials: Dict, user: User, environment: Environment
    ):
        credentials = self.get_client(self.root_creds())
        sub_client = self.azure_mgmt.subscription.SubscriptionClient(credentials)

        display_name = (
            f"{environment.application.name}_{environment.name}_{environment.id}"
        )  # proposed format

        billing_profile_id = "?"  # something chained from environment?
        sku_id = "?"  # probably a static sku specific to ATAT/JEDI
        body = self.azure_mgmt.subscription.models.ModernSubscriptionCreationParameters(
            display_name, billing_profile_id, sku_id
        )

        billing_account_name = "?"  # something chained from environment?
        invoice_section_name = "?"  # something chained from environment?
        sub_creation_operation = sub_client.subscription_factory.create_subscription(
            billing_account_name, invoice_section_name, body
        )

        # the resulting object from this process is a link to the new subscription
        # not a subscription model, so we'll have to unpack the ID
        new_sub = sub_creation_operation.result()

        sub_id_match = SUBSCRIPTION_ID_REGEX.match(new_sub.subscription_link)

        if sub_id_match:
            return sub_id_match.group(1)
        else:
            # troublesome error, subscription shoudl exist at this point, but we just don't have a valid ID
            pass

    def _get_client(self, creds):
        return self.azure_credentials.ServicePrincipalCredentials(
            client_id=creds.get("client_id"),
            secret=creds.get("secret_key"),
            tenant=creds.get("tenant_id"),
            cloud_environment=AZURE_ENVIRONMENT,
        )

