from datetime import datetime, timezone

from sqlalchemy import func
from app.db import db
from app.models.menu_item import MenuItem
from app.models.role import Role


# class MenuInRole(db.Model):
#     __tablename__ = 'menu_in_roles'
    
#     id = db.Column(db.Integer, primary_key=True)
#     role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
#     menu_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
#     # can_read = db.Column(db.Boolean, default=True, nullable=False)
#     # can_write = db.Column(db.Boolean, default=False, nullable=False)
#     # can_delete = db.Column(db.Boolean, default=False, nullable=False)
#     created_on = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
#     # assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
#     # Relationships
#     role = db.relationship('Role', back_populates='role_menus')
#     menu = db.relationship('MenuItem', back_populates='menu_roles')
    
#     # assigner = db.relationship('User')
    
#     # Composite unique constraint
#     __table_args__ = (db.UniqueConstraint('role_id', 'menu_id', name='unique_role_menu'),)

class MenuInRole(db.Model):
    __tablename__ = 'menu_in_roles'
    
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    menu_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    created_on = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))

    # Relationships
    role = db.relationship('Role', back_populates='role_menus')
    menu = db.relationship('MenuItem', back_populates='menu_roles')

    __table_args__ = (db.UniqueConstraint('role_id', 'menu_id', name='unique_role_menu'),)
    
    def __repr__(self):
        return f'<MenuInRole role_id={self.role_id} menu_id={self.menu_id}>'
    
    @classmethod
    def get_all(cls):
        query = (
            db.session.query(
                MenuItem.id.label("menu_item_id"),
                MenuItem.name.label("menu_item"),
                func.array_agg(Role.name).label("roles")
            )
            .join(cls, MenuItem.id == cls.menu_id)
            .join(Role, Role.id == cls.role_id)
            .group_by(MenuItem.id, MenuItem.name)
            .order_by(MenuItem.id)
        )

        results = query.all()

        output = [
            {
                "serial": idx + 1,
                "menu_item_id": r.menu_item_id,
                "menu_item": r.menu_item,
                "roles": r.roles
            }
            for idx, r in enumerate(results)
        ]
        return output
 
    
    