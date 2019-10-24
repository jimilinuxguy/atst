from flask_wtf import FlaskForm
from wtforms.fields import FormField, FieldList, HiddenField, BooleanField
from wtforms import Form

from .member import NewForm as BaseNewMemberForm
from .data import ENV_ROLES, ENV_ROLE_NO_ACCESS as NO_ACCESS
from atst.forms.fields import SelectField
from atst.domain.permission_sets import PermissionSets
from atst.utils.localization import translate


class EnvironmentForm(Form):
    environment_id = HiddenField()
    environment_name = HiddenField()
    role = SelectField(
        environment_name,
        choices=ENV_ROLES,
        default=NO_ACCESS,
        filters=[lambda x: None if x == "None" else x],
    )
    deleted = BooleanField("Revoke Access", default=False)

    @property
    def data(self):
        _data = super().data
        if "role" in _data and _data["role"] == NO_ACCESS:
            _data["role"] = None
        return _data


class PermissionsForm(FlaskForm):
    perms_env_mgmt = BooleanField(
        translate("portfolios.applications.members.form.env_mgmt.label"),
        default=False,
        description=translate(
            "portfolios.applications.members.form.env_mgmt.description"
        ),
    )
    perms_team_mgmt = BooleanField(
        translate("portfolios.applications.members.form.team_mgmt.label"),
        default=False,
        description=translate(
            "portfolios.applications.members.form.team_mgmt.description"
        ),
    )
    perms_del_env = BooleanField(
        translate("portfolios.applications.members.form.del_env.label"),
        default=False,
        description=translate(
            "portfolios.applications.members.form.del_env.description"
        ),
    )

    @property
    def data(self):
        _data = super().data
        _data.pop("csrf_token", None)
        perm_sets = []

        if _data["perms_env_mgmt"]:
            perm_sets.append(PermissionSets.EDIT_APPLICATION_ENVIRONMENTS)

        if _data["perms_team_mgmt"]:
            perm_sets.append(PermissionSets.EDIT_APPLICATION_TEAM)

        if _data["perms_del_env"]:
            perm_sets.append(PermissionSets.DELETE_APPLICATION_ENVIRONMENTS)

        _data["permission_sets"] = perm_sets
        return _data


class NewForm(PermissionsForm):
    user_data = FormField(BaseNewMemberForm)
    environment_roles = FieldList(FormField(EnvironmentForm))


class UpdateMemberForm(PermissionsForm):
    environment_roles = FieldList(FormField(EnvironmentForm))
