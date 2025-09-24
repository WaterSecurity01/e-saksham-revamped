from datetime import datetime, timezone
from app.db import db

# class MenuItem(db.Model):
#     __tablename__ = 'menu_items'
    
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(100), nullable=False)
#     url = db.Column(db.String(200), nullable=False)
#     icon = db.Column(db.String(50))  # CSS class for icon
#     parent_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=True)
#     order_index = db.Column(db.Integer, default=0)
#     is_active = db.Column(db.Boolean, default=True, nullable=False)
#     created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
#     updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
#     # Self-referential relationship for parent/child menus
#     children = db.relationship('MenuItem', backref=db.backref('parent', remote_side=[id]))
    
#     # Relationship with roles
#     menu_roles = db.relationship('MenuInRole', back_populates='menu', lazy='dynamic')

class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(200), nullable=False)
    icon = db.Column(db.String(50))  
    parent_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=True)
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Self-referential relationship for hierarchical menus
    children = db.relationship('MenuItem', backref=db.backref('parent', remote_side=[id]))

    # Role association
    menu_roles = db.relationship('MenuInRole', back_populates='menu', cascade="all, delete-orphan")


    def __init__(self, name, url, icon, parent_id, order_index, is_active=True, created_at = datetime.now(timezone.utc)):
        self.name = name
        self.url = url
        self.icon = icon
        self.parent_id = parent_id if parent_id > 0 else None
        self.order_index = order_index
        self.is_active = is_active
        self.created_at = created_at

    @classmethod
    def get_menuItem_by_name(cls, item):
        return cls.query.filter(cls.name==item).first()

    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def get_roles(self):
        """Get all roles that have access to this menu"""
        return [mr.role for mr in self.menu_roles]
    
    def __repr__(self):
        return f'<MenuItem {self.name}>'