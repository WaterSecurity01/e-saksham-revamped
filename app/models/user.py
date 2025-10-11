# Import the database extension
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import DateTime, distinct, extract, func, and_, or_
from flask_login import UserMixin
import uuid
import logging

from app.db import db

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
        from sqlalchemy.orm import joinedload,aliased,contains_eager
        from app.models import MenuItem, MenuInRole, Role, UserInRole

        # menus = (
        #     MenuItem.query.join(MenuInRole)
        #     .join(Role)
        #     .join(UserInRole)
        #     .filter(UserInRole.user_id == self.id, MenuItem.is_active == True)
        #     .options(joinedload(MenuItem.children))  # load children for hierarchy
        #     .order_by(MenuItem.order_index)
        #     .all()
        # )
        Child = aliased(MenuItem)
        ChildRole = aliased(MenuInRole)
        ChildUserRole = aliased(UserInRole)
        ChildRoleTable = aliased(Role)

        menus = (
            MenuItem.query
                # Parent joins
                .join(MenuInRole, MenuItem.id == MenuInRole.menu_id)
                .join(Role, MenuInRole.role_id == Role.id)
                .join(UserInRole, Role.id == UserInRole.role_id)
                .filter(
                    UserInRole.user_id == self.id,
                    MenuItem.is_active == True,
                    MenuItem.parent_id == None   # load only top-level menus first
                )

                # Child joins (aliased!)
                .outerjoin(Child, Child.parent_id == MenuItem.id)

                # Child → role
                .outerjoin(ChildRole, Child.id == ChildRole.menu_id)
                .outerjoin(ChildRoleTable, ChildRole.role_id == ChildRoleTable.id)
                .outerjoin(ChildUserRole, ChildRoleTable.id == ChildUserRole.role_id)

                # Keep only children allowed for this user OR if no child
                .filter(
                    (Child.id == None) | (ChildUserRole.user_id == self.id)
                )

                # Tell SQLAlchemy: Child = children relationship
                .options(contains_eager(MenuItem.children, alias=Child))

                .order_by(MenuItem.order_index)
                .all()
        )
        return menus
    
    def get_anonymous_menu():
        from sqlalchemy.orm import joinedload
        from app.models import MenuItem, MenuInRole, Role, UserInRole

        from sqlalchemy.orm import contains_eager,aliased
        """
        menus = (
    MenuItem.query
        .join(MenuInRole)
        .filter(
            MenuInRole.role_id == 1,     # Anonymous users = 1
            MenuItem.is_active == True
        )
        .options(
            joinedload(MenuItem.children)   # Load children for hierarchy
        )
        .order_by(MenuItem.order_index)
        .all()
)
        """

        Child = aliased(MenuItem)
        ChildRole = aliased(MenuInRole)

        menus = (
            MenuItem.query

                # 1️⃣ Load only top-level menus assigned to role 1
                .join(MenuInRole, MenuItem.id == MenuInRole.menu_id)
                .filter(
                    MenuItem.parent_id == None,    # parent menu
                    MenuInRole.role_id == 1,
                    MenuItem.is_active == True
                )

                .outerjoin(Child, Child.parent_id == MenuItem.id)

                # 3️⃣ Outer join child's role mapping (aliased!)
                .outerjoin(ChildRole, Child.id == ChildRole.menu_id)

                # 4️⃣ Keep only children allowed for the same role
                .filter(
                    (Child.id == None) | (ChildRole.role_id == 1)
                )

                # 5️⃣ Eager load the children correctly
                .options(contains_eager(MenuItem.children, alias=Child))

                .order_by(MenuItem.order_index)
                .all()
        )
        return menus
    
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
