from datetime import datetime, timezone
from app.db import db

# class Role(db.Model):
#     __tablename__ = 'roles'
    
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(50), unique=True, nullable=False, index=True)
#     description = db.Column(db.Text)
#     is_active = db.Column(db.Boolean, default=True, nullable=False)
#     created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
#     updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
#     # Relationships
#     role_users = db.relationship('UserInRole', back_populates='role', lazy='dynamic')
#     role_menus = db.relationship('MenuInRole', back_populates='role', lazy='dynamic')

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    role_users = db.relationship('UserInRole', back_populates='role', cascade="all, delete-orphan")
    role_menus = db.relationship('MenuInRole', back_populates='role', cascade="all, delete-orphan")


    def __init__(self, name, description, is_active=True, created_at=datetime.now(timezone.utc)):
        self.name = name
        self.description = description
        self.is_active = is_active
        self.created_at = self.created_at

    @classmethod
    def get_role_by_name(cls, role_name):
        return cls.query.filter(cls.name==role_name).first()
    
    def get_users(self):
        """Get all users assigned to this role"""
        return [ru.user for ru in self.role_users]
    
    def get_menus(self):
        """Get all menu items accessible by this role"""
        return [rm.menu for rm in self.role_menus]
    
    @classmethod
    def get_all(cls):
        return cls.query.all()
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def __repr__(self):
        return f'<Role {self.name}>'
