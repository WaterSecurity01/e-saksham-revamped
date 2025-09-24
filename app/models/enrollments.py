from datetime import datetime
from zoneinfo import ZoneInfo
from app.db import db


class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    enrolled_at = db.Column(
        db.DateTime, default=lambda: datetime.now(tz=ZoneInfo("Asia/Kolkata"))
    )

    # Relationships
    user = db.relationship("User", backref=db.backref("enrollments", lazy=True))
    course = db.relationship("Course", backref=db.backref("enrollments", lazy=True))

    def __init__(self, user_id, course_id):
        self.user_id = user_id
        self.course_id = course_id

    def json(self):
        return {
            "user_id": self.user_id,
            "course_id": self.course_id,
            "enrolled_at": self.enrolled_at
        }
    # ----------------------
    # Instance Methods
    # ----------------------
    def save(self):
        """Insert or update the record in the database."""
        db.session.add(self)
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
    def find_by_id(cls, user_id, course_id):
        """Find an enrollment by primary key (id)."""
        return cls.query.filter_by(user_id=user_id, course_id=course_id).first()

    @classmethod
    def find_all(cls):
        """Return all enrollments."""
        return cls.query.all()

    @classmethod
    def find_by_user(cls, user_id):
        """Find all enrollments for a specific user."""
        return cls.query.filter_by(user_id=user_id).all()

    @classmethod
    def find_by_course(cls, course_id):
        """Find all enrollments for a specific course."""
        return cls.query.filter_by(course_id=course_id).all()

    def __repr__(self):
        return f"<Enrollment id={self.id} user_id={self.user_id} course_id={self.course_id}>"
