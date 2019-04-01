from sqlalchemy import String, ForeignKey, Column, Date, Boolean, Table, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from atst.models import Base, types, mixins
from atst.models.permissions import Permissions


users_permission_sets = Table(
    "users_permission_sets",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id")),
    Column("permission_set_id", UUID(as_uuid=True), ForeignKey("permission_sets.id")),
)


class User(
    Base, mixins.TimestampsMixin, mixins.AuditableMixin, mixins.PermissionsMixin
):
    __tablename__ = "users"

    id = types.Id()
    username = Column(String)

    permission_sets = relationship("PermissionSet", secondary=users_permission_sets)

    portfolio_roles = relationship("PortfolioRole", backref="user")

    email = Column(String, unique=True)
    dod_id = Column(String, unique=True, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    phone_number = Column(String)
    phone_ext = Column(String)
    service_branch = Column(String)
    citizenship = Column(String)
    designation = Column(String)
    date_latest_training = Column(Date)
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)

    provisional = Column(Boolean)

    cloud_id = Column(String)

    REQUIRED_FIELDS = [
        "email",
        "dod_id",
        "first_name",
        "last_name",
        "phone_number",
        "service_branch",
        "citizenship",
        "designation",
        "date_latest_training",
    ]

    @property
    def profile_complete(self):
        return all(
            [
                getattr(self, field_name) is not None
                for field_name in self.REQUIRED_FIELDS
            ]
        )

    @property
    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name)

    @property
    def has_portfolios(self):
        return (Permissions.VIEW_PORTFOLIO in self.permissions) or self.portfolio_roles

    @property
    def displayname(self):
        return self.full_name

    def __repr__(self):
        return "<User(name='{}', dod_id='{}', email='{}', has_portfolios='{}', id='{}')>".format(
            self.full_name, self.dod_id, self.email, self.has_portfolios, self.id
        )

    def to_dictionary(self):
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
            if c.name not in ["id"]
        }
