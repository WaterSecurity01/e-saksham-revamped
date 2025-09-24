from datetime import datetime
from zoneinfo import ZoneInfo
from app.db import db


class ScormData(db.Model):
    __tablename__ = "scorm_data"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    cmi_key = db.Column(db.String, nullable=False)
    cmi_value = db.Column(db.Text)
    updated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(tz=ZoneInfo("Asia/Kolkata")), onupdate=lambda: datetime.now(tz=ZoneInfo("Asia/Kolkata"))
    )

    # Unique constraint (user_id, course_id, cmi_key)
    __table_args__ = (
        db.UniqueConstraint("user_id", "course_id", "cmi_key", name="uq_user_course_cmi"),
        db.Index("idx_user_course", "user_id", "course_id"),
    )

    # Relationships
    user = db.relationship("User", backref=db.backref("scorm_data", lazy=True))
    course = db.relationship("Course", backref=db.backref("scorm_data", lazy=True))

    def __init__(self, user_id, course_id, cmi_key, cmi_value):
        self.user_id = user_id
        self.course_id = course_id
        self.cmi_key = cmi_key
        self.cmi_value = cmi_value
        self.updated_at = datetime.now(tz=ZoneInfo("Asia/Kolkata"))
    
    def json(self):
        return {
            "user_id": self.user_id,
            "course_id": self.course_id,
            "cmi_key": self.cmi_key,
            "cmi_value": self.cmi_value,
            "updated_at": self.updated_at
        }
    # ----------------------
    # Instance Methods
    # ----------------------
    def save(self):
        """Insert or update the record in the database."""
        db.session.add(self)
        db.session.commit()
        return self

    def update(self, **kwargs):
        """Update specific fields and commit."""
        for key, value in kwargs.items():
            setattr(self, key, value)
        db.session.commit()
        return self

    def delete(self):
        """Delete the record from the database."""
        db.session.delete(self)
        db.session.commit()

    # ----------------------
    # Class Methods
    # ----------------------
    @classmethod
    def get_by_id(cls, record_id):
        """Get a SCORM data record by primary key (id)."""
        return cls.query.get(record_id)

    @classmethod
    def get_all(cls):
        """Return all SCORM data records."""
        return cls.query.all()

    @classmethod
    def get_by_user_course(cls, user_id, course_id):
        """Get all SCORM data records for a given user and course."""
        return cls.query.filter_by(user_id=user_id, course_id=course_id).all()

    @classmethod
    def get_by_key(cls, user_id, course_id, cmi_key):
        """Get a specific SCORM data record by key."""
        return cls.query.filter_by(user_id=user_id, course_id=course_id, cmi_key=cmi_key).first()

    def __repr__(self):
        return f"<ScormData id={self.id} user_id={self.user_id} course_id={self.course_id} key={self.cmi_key}>"
