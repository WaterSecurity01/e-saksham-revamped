from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func
from app.db import db  # this imports your SQLAlchemy() instance


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    scorm_version = db.Column(db.String)
    package_path = db.Column(db.String, nullable=False)
    manifest_path = db.Column(db.String, nullable=False)
    manifest_identifier = db.Column(db.String)
    manifest_title = db.Column(db.String)
    package_id = db.Column(db.String, nullable=False)
    launch_url = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    # created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(tz=ZoneInfo("Asia/Kolkata")))

    def __init__(self, name, description,scorm_version,package_path,manifest_path,manifest_identifier, manifest_title, package_id, launch_url):
        self.name = name
        self.description = description
        self.scorm_version = scorm_version
        self.package_path = package_path
        self.manifest_path = manifest_path
        self.manifest_identifier = manifest_identifier
        self.manifest_title = manifest_title
        self.package_id = package_id
        self.launch_url = launch_url
        self.created_at = datetime.now()
    
    def json(self):
        return {
            "name": self.name,
            "description": self.description,
            "scorm_version": self.scorm_version,
            "package_path": self.package_path,
            "manifest_path": self.manifest_path,
            "manifest_identifier": self.manifest_identifier,
            "manifest_title": self.manifest_title,
            "package_id": self.package_id,
            "launch_url": self.launch_url,
            "created_at": self.created_at
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
    def find_by_id(cls, course_id):
        """Find a course by primary key (id)."""
        return cls.query.get(course_id)

    @classmethod
    def find_all(cls):
        """Return all courses."""
        return cls.query.all()

    @classmethod
    def find_by_title(cls, title):
        """Find courses with a specific title (case-insensitive)."""
        return cls.query.filter(cls.title.ilike(f"%{title}%")).all()
    
    @classmethod
    def find_by_identifier(cls, manifest_identifier):
        return cls.query.filter(cls.manifest_identifier==manifest_identifier).first()

    def __repr__(self):
        return f"<Course id={self.id} title={self.title}>"
