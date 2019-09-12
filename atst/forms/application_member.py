from flask_wtf import FlaskForm
from wtforms.fields import FormField, FieldList, HiddenField, BooleanField

from .forms import BaseForm
from .member import NewForm as BaseNewMemberForm
from .data import ENV_ROLES, ENV_ROLE_NO_ACCESS as NO_ACCESS
from atst.domain.permission_sets import PermissionSets
from atst.forms.fields import SelectField
from atst.utils.localization import translate


class EnvironmentForm(FlaskForm):
    environment_id = HiddenField()
    environment_name = HiddenField()
    role = SelectField(
        environment_name,
        choices=ENV_ROLES,
        default=NO_ACCESS,
        filters=[lambda x: None if x == "None" else x],
    )

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
        false_values=(False, "False", 'false', ''),
    )
    perms_team_mgmt = BooleanField(
        translate("portfolios.applications.members.form.team_mgmt.label"),
        default=False,
        description=translate(
            "portfolios.applications.members.form.team_mgmt.description"
        ),
        false_values=(False, "False", 'false', ''),
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
        perm_sets = []

        if _data["perms_env_mgmt"]:
            perm_sets.append(PermissionSets.EDIT_APPLICATION_ENVIRONMENTS)

        if _data["perms_team_mgmt"]:
            perm_sets.append(PermissionSets.EDIT_APPLICATION_TEAM)

        if _data["perms_del_env"]:
            perm_sets.append(PermissionSets.DELETE_APPLICATION_ENVIRONMENTS)

        return perm_sets


class NewForm(BaseForm):
    user_data = FormField(BaseNewMemberForm)
    permission_sets = FormField(PermissionsForm)
    environment_roles = FieldList(FormField(EnvironmentForm))


class UpdateMemberForm(BaseForm):
    permission_sets = FormField(PermissionsForm)
    environment_roles = FieldList(FormField(EnvironmentForm))
