from datetime import datetime, timezone

from sqlalchemy import func
from app.db import db
from app.models.role import Role
from app.models.user import User


# class UserInRole(db.Model):
#     __tablename__ = 'users_in_roles'
    
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
#     role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
#     created_on = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
#     # assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
#     # Relationships
#     user = db.relationship('User', foreign_keys=[user_id], back_populates='user_roles')
#     role = db.relationship('Role', back_populates='role_users')
#     # assigner = db.relationship('User', foreign_keys=[assigned_by])
    
#     # Composite unique constraint
#     __table_args__ = (db.UniqueConstraint('user_id', 'role_id', name='unique_user_role'),)

class UserInRole(db.Model):
    __tablename__ = 'users_in_roles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    created_on = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))

    # Relationships
    user = db.relationship("User", back_populates="user_roles")
    role = db.relationship("Role", back_populates="role_users")

    def __repr__(self):
        return f'<UserInRole user_id={self.user_id} role_id={self.role_id}>'
    
    @classmethod
    def get_all(cls):
        query = (
            db.session.query(
                User.id.label("user_id"),
                User.email.label('username'),
                func.array_agg(Role.name).label("roles")
            )
            .join(cls, User.id == cls.user_id)
            .join(Role, Role.id == cls.role_id)
            .group_by(User.id, User.name)
            .order_by(User.id)
        )

        results = query.all()

        output = [
            {
                "serial": idx + 1,
                "user_id": r.user_id,
                "username": r.username,
                "roles": r.roles
            }
            for idx, r in enumerate(results)
        ]
        return output
    
    @classmethod
    def get_user_role_by_id(cls, user_id):
        query = (
            db.session.query(
                User,
                func.array_agg(Role.name).label("roles")
            )
            .join(cls, User.id == cls.user_id)
            .join(Role, Role.id == cls.role_id)
            .filter(User.id==user_id)
            .group_by(User.id, User.name)
            .order_by(User.id)
        )

        results = query.all()

        # output = [
        #     {
        #         "serial": idx + 1,
        #         "user_id": r.user_id,
        #         "username": r.username,
        #         "roles": r.roles
        #     }
        #     for idx, r in enumerate(results)
        # ]
        return results
