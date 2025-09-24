from app.db import db


class Cluster(db.Model):
    __tablename__ = "clusters"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class Ridge(db.Model):
    __tablename__ = "ridges"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class Beneficiary(db.Model):
    __tablename__ = "beneficiaries"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    


class ActivityType(db.Model):
    __tablename__ = "activity_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    short_name = db. Column(db.String, nullable=True)

class WorkType(db.Model):
    __tablename__ = "work_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class Slope(db.Model):
    __tablename__ = "slopes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    ridge_id = db.Column(db.Integer, db.ForeignKey("ridges.id"))


class WaterWork(db.Model):
    __tablename__ = "water_works"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class LocationSpecific(db.Model):
    __tablename__ = "location_specifics"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class PermissibleWork(db.Model):
    __tablename__ = "permissible_works"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class NatureOfWork(db.Model):
    __tablename__ = "nature_of_works"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    short_name = db.Column(db.String, nullable=True)
    

class MajorScheduledCategory(db.Model):
    __tablename__ = "major_scheduled_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class ActivityList(db.Model):
    __tablename__ = "activities_list"

    id = db.Column(db.Integer, primary_key=True)

    activity_type = db.Column(db.Integer, db.ForeignKey("activity_types.id"))
    beneficiary_type = db.Column(db.Integer, db.ForeignKey("beneficiaries.id"))
    cluster_type = db.Column(db.Integer, db.ForeignKey("clusters.id"))
    major_scheduled_category = db.Column(db.Integer, db.ForeignKey("major_scheduled_categories.id"))
    category = db.Column(db.Integer, db.ForeignKey("categories.id"))
    nature_of_work = db.Column(db.Integer, db.ForeignKey("nature_of_works.id"))
    permissible_work = db.Column(db.Integer, db.ForeignKey("permissible_works.id"))
    location_specifics = db.Column(db.Integer, db.ForeignKey("location_specifics.id"))
    water_work = db.Column(db.Integer, db.ForeignKey("water_works.id"))
    work_type = db.Column(db.Integer, db.ForeignKey("work_types.id"))
    slope = db.Column(db.Integer, db.ForeignKey("slopes.id"))
    ridge = db.Column(db.Integer, db.ForeignKey("ridges.id"))


    # Relationships
    activitytype = db.relationship("ActivityType", backref="activities_list")
    beneficiary = db.relationship("Beneficiary", backref="activities_list")
    cluster = db.relationship("Cluster", backref="activities_list")
    majorcategory = db.relationship("MajorScheduledCategory", backref="activities_list")
    category_rel = db.relationship("Category", backref="activities_list")
    nature_of_work_rel = db.relationship("NatureOfWork", backref="activities_list")
    permissible = db.relationship("PermissibleWork", backref="activities_list")
    location_specific = db.relationship("LocationSpecific", backref="activities_list")
    water = db.relationship("WaterWork", backref="activities_list")
    worktype = db.relationship("WorkType", backref="activities_list")
    slope_rel = db.relationship("Slope", backref="activities_list")
    ridge_rel = db.relationship("Ridge", backref="activities_list")

