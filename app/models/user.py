# Import the database extension
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import DateTime, distinct, extract, func, and_, or_
from flask_login import UserMixin
import uuid
import logging

from app.db import db

# Import centralized loggers
try:
    from app import activity_logger, access_logger, error_logger
except ImportError:
    activity_logger = logging.getLogger('activity')
    access_logger = logging.getLogger('access')
    error_logger = logging.getLogger('error')

# class User(UserMixin, db.Model):
#     __tablename__ = "users"
    
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(128))
#     email = db.Column(db.String(128), unique=True)
#     password = db.Column(db.String(128))
#     is_active = db.Column(db.Boolean, default=True)
#     is_admin = db.Column(db.Boolean, default=False)
#     registered_on = db.Column(db.DateTime, default=lambda: datetime.now(tz=ZoneInfo('Asia/Kolkata')))
#     uuid = db.Column(db.String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))

#     # Relationships
#     user_roles = db.relationship('UserInRole', back_populates='user', cascade="all, delete-orphan")



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
    activity_log = db.relationship('ActivityLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    password_reset_expiry = db.Column(DateTime(timezone=True), nullable=True)
    reset_token = db.Column(db.String(), nullable=True, unique=True, index=True)
    totp_secret = db.Column(db.String(64), nullable=True, unique=True, index=True)

    # added on 20 Aug 2025 to cater for block/district/state
    state_id = db.Column(db.ForeignKey('states.id'), nullable=False)
    district_id = db.Column(db.ForeignKey('districts.id'), nullable=False)
    block_id = db.Column(db.ForeignKey('blocks.id'), nullable=False)

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
            activity_logger.info(f"User initialized: {self.name} ({self.email}), uuid={self.uuid}")
        except Exception as ex:
            error_logger.error(f"Error initializing User: {ex}")

    def json(self):
        try:
            access_logger.info(f"Accessed user json for id={self.id}, email={self.email}")
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
        except Exception as ex:
            error_logger.error(f"Error in json() for User id={getattr(self, 'id', None)}: {ex}")
            return {}

    def get_structured_menus(self):
        """
        Return a hierarchical list of active menu items available to this user through roles.
        Filters for active menus and structures them into a parent-child tree.
        """
        from sqlalchemy.orm import joinedload
        from app.models import MenuItem, MenuInRole, Role, UserInRole
        # Load all active menu items associated with the user's roles
        # Use aliased for self-referential joins to avoid ambiguity
        # MenuItemAlias = aliased(MenuItem)

        all_user_menus_flat = (
            db.session.query(MenuItem)
            .join(MenuInRole)
            .join(Role)
            .join(UserInRole)
            .filter(
                UserInRole.user_id == self.id,
                MenuItem.is_active == True,
                Role.is_active == True # Ensure roles themselves are active
            )
            .options(joinedload(MenuItem.parent), joinedload(MenuItem.children)) # Eager load parents and children
            .order_by(MenuItem.order_index)
            .all()
        )

        # Build a dictionary for quick lookup by ID
        menu_dict = {menu.id: menu for menu in all_user_menus_flat}

        # Structure the menus hierarchically
        # Each menu object might have a `children` list if the relationship is set up correctly
        # We need to filter for top-level menus (parent_id is None)
        top_level_menus = []
        for menu in all_user_menus_flat:
            if menu.parent_id is None:
                top_level_menus.append(menu)
            # Ensure children loaded via `joinedload` are also from `menu_dict` to maintain consistency
            # if using explicit children management, not relying solely on backref in all_user_menus_flat.
            # However, with joinedload, SQLAlchemy usually handles this.
            
        # Sort top-level menus by order_index
        top_level_menus.sort(key=lambda m: m.order_index)

        return top_level_menus
    
    def get_menus(self):
        """Return all active menu items available to this user through roles."""
        from sqlalchemy.orm import joinedload
        from app.models import MenuItem, MenuInRole, Role, UserInRole

        menus = (
            MenuItem.query.join(MenuInRole)
            .join(Role)
            .join(UserInRole)
            .filter(UserInRole.user_id == self.id, MenuItem.is_active == True)
            .options(joinedload(MenuItem.children))  # load children for hierarchy
            .order_by(MenuItem.order_index)
            .all()
        )
        return menus
    
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
    def get_user_by_email(cls, email):
        return cls.query.filter_by(email=email).first()
        # try:
        #     # access_logger.info(f"Fetching user by email={_email}")
        #     query = cls.query.filter_by(email=_email).first()
        #     if query:
        #         # activity_logger.info(f"User found by email={_email}")
        #         return query.json()
        #     else:
        #         # activity_logger.info(f"No user found by email={_email}")
        #         return None
        # except Exception as ex:
        #     # error_logger.error(f"Error fetching user by email={_email}: {ex}")
        #     return None

    @classmethod
    def get_all(cls):
        return cls.query.order_by(cls.id.desc())
        # try:
        #     access_logger.info("Fetching all users")
        #     query = cls.query.order_by(cls.id.desc())
        #     activity_logger.info("All users queried")
        #     return query
        # except Exception as ex:
        #     # error_logger.error(f"Error fetching all users: {ex}")
        #     return []

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
            # activity_logger.info(f"User saved to DB: {self.name} ({self.email}), id={self.id}")
        except Exception as ex:
            db.session.rollback()
            # error_logger.error(f"Error saving user {self.name} ({self.email}) to DB: {ex}")

    @classmethod
    def delete(cls, _id):
        try:
            user = cls.query.filter_by(id=_id).first()
            if user:
                db.session.delete(user)
                db.session.commit()
                # activity_logger.info(f"User deleted from DB: id={_id}")
            else:
                # activity_logger.info(f"Attempted to delete non-existent user: id={_id}")
                pass
        except Exception as ex:
            db.session.rollback()
            # error_logger.error(f"Error deleting user id={_id} from DB: {ex}")

    @staticmethod
    def commit_db():
        try:
            db.session.commit()
            activity_logger.info("DB session committed (user).")
        except Exception as ex:
            db.session.rollback()
            error_logger.error(f"Error committing DB session (user): {ex}")

    @classmethod
    def update_db(cls, data, _id):
        try:
            user = cls.query.filter_by(id=_id).update(data)
            db.session.commit()
            activity_logger.info(f"User updated in DB: id={_id}, data={data}")
        except Exception as ex:
            db.session.rollback()
            error_logger.error(f"Error updating user id={_id} in DB: {ex}")