# Import the database extension
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import DateTime, distinct, extract, func, and_, or_
from flask_login import UserMixin
import uuid
import logging

from app.db import db
from app.services import menu_cache

# Import centralized loggers


class User(UserMixin, db.Model):
    def get_uuid():
        return str(uuid.uuid4())
    
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    email = db.Column(db.String(128), unique=True)
    password = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    registered_on = db.Column(db.DateTime, default=lambda: datetime.now(tz=ZoneInfo('Asia/Kolkata')))
    uuid = db.Column(db.String(36), unique=True, index=True, default=get_uuid)
    password_reset_expiry = db.Column(DateTime(timezone=True), nullable=True)
    reset_token = db.Column(db.String(), nullable=True, unique=True, index=True)
    totp_secret = db.Column(db.String(64), nullable=True, unique=True, index=True)

    # added on 20 Aug 2025 to cater for block/district/state
    state_id = db.Column(db.ForeignKey('states.id'), nullable=True)
    district_id = db.Column(db.ForeignKey('districts.id'), nullable=True)
    block_id = db.Column(db.ForeignKey('blocks.id'), nullable=True)

    #added on 29 Aug 2025
    supervisor_id = db.Column(db.Integer, default=0)

    state = db.relationship('State_UT', back_populates='users')
    district = db.relationship('District', back_populates='users')
    block = db.relationship('Block', back_populates='users')
    user_roles = db.relationship('UserInRole', back_populates='user')
    

    def __init__(self, name, email, password, state_id=None, district_id=None, block_id=None, is_active=True, is_admin=False, _uuid=None, registered_on=None, password_reset_expiry=None,reset_token=None,totp_secret=None):
        try:
            if _uuid is None:
                _uuid = str(uuid.uuid4())
            if registered_on is None:
                registered_on = datetime.now(tz=ZoneInfo('Asia/Kolkata'))
            self.is_active = is_active
            self.is_admin = is_admin
            self.registered_on = registered_on
            self.uuid = _uuid
            self.password = password
            self.name = name
            self.email = email
            self.password_reset_expiry = password_reset_expiry
            self.reset_token = reset_token
            self.totp_secret = totp_secret
            self.state_id = state_id
            self.district_id = district_id
            self.block_id = block_id
        except Exception as ex:
            pass

    def json(self):
            return {
                'id': self.id,
                'name': self.name,
                'email': self.email,
                'password': self.password,
                'uuid': self.uuid,
                'registered_on': self.registered_on,
                'is_active': self.is_active,
                'is_admin': self.is_admin,
                'password_reset_expiry': self.password_reset_expiry,
                'reset_token': self.reset_token,
                'totp_secret': self.totp_secret,
                'state_id': self.state_id,
                'district_id': self.district_id,
                'block_id': self.block_id
            }


    # Menu related functions
    def get_structured_menus(self):
        """
        Return a hierarchical list of active menu items available to this user through roles.
        Filters for active menus and structures them into a parent-child tree.
        """
        menu_cache.ensure_menu_cache()
        role_ids = menu_cache.get_role_ids_for_user(
            self.id,
            email=self.email,
            is_admin=self.is_admin,
        )
        return menu_cache.get_menu_tree_for_roles(role_ids)
    
    def get_menus(self):
        """Return all active menu items available to this user through roles."""
        menu_cache.ensure_menu_cache()
        role_ids = menu_cache.get_role_ids_for_user(
            self.id,
            email=self.email,
            is_admin=self.is_admin,
        )
        return menu_cache.get_flat_menu_for_roles(role_ids)
    
    def get_anonymous_menu():
        menu_cache.ensure_menu_cache()
        anonymous_role = menu_cache.get_anonymous_role_id()
        if anonymous_role is None:
            return []
        return menu_cache.get_menu_tree_for_roles({anonymous_role})
    
    # Charts Dashboard methods
    @classmethod
    def get_total_users(cls,state_id=None, district_id=None, block_id=None):
        try:
            query = cls.query
            
            if state_id:
                query = query.filter_by(state_id=state_id)
            if district_id:
                query = query.filter_by(district_id=district_id)
            if block_id:
                query = query.filter_by(block_id=block_id)
            
            total = query.count()
            return total
        except Exception as ex:
            print(f"Error fetching filtered user count: {ex}")
            return 0

    @classmethod
    def get_user_by_id(cls, _id):
        return cls.query.filter_by(id=_id).first()
            # access_logger.info(f"Fetching user by id={_id}")
            
            # if query:
            #     # activity_logger.info(f"User found by id={_id}")
            #     return query.json()
            # else:
            #     # activity_logger.info(f"No user found by id={_id}")
            #     return None
        # except Exception as ex:
        #     # error_logger.error(f"Error fetching user by id={_id}: {ex}")
        #     return None
    
    @classmethod
    def get_user_by_uuid(cls, uuid):
        return cls.query.filter_by(uuid=uuid).first()

    @classmethod
    def get_user_by_email(cls, email):
        return cls.query.filter_by(email=email).first()
        # try:
        #     # access_logger.info(f"Fetching user by email={_email}")
        #     query = cls.query.filter_by(email=_email).first()
        #     if query:
        #         # activity_logger.info(f"User found by email={_email}")
        #         return query.json()
        #     else:
        #         return None
        # except Exception as ex:
        #     return None

    @classmethod
    def get_all(cls):
        return cls.query.order_by(cls.id.desc())
        # try:
        #     query = cls.query.order_by(cls.id.desc())
        #     return query
        # except Exception as ex:
        #     return []

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as ex:
            db.session.rollback()

    @classmethod
    def delete(cls, _id):
        try:
            user = cls.query.filter_by(id=_id).first()
            if user:
                db.session.delete(user)
                db.session.commit()
            else:
                pass
        except Exception as ex:
            db.session.rollback()

    @staticmethod
    def commit_db():
        try:
            db.session.commit()
        except Exception as ex:
            db.session.rollback()

    @classmethod
    def update_db(cls, data, _id):
        try:
            user = cls.query.filter_by(id=_id).update(data)
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
