from app.db import db


class Cluster(db.Model):
    __tablename__ = "nrega_clusters"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class Category(db.Model):
    __tablename__ = "nrega_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class Ridge(db.Model):
    __tablename__ = "nrega_ridges"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class Beneficiary(db.Model):
    __tablename__ = "nrega_beneficiaries"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    


class ActivityType(db.Model):
    __tablename__ = "nrega_activity_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    short_name = db. Column(db.String, nullable=True)

class WorkType(db.Model):
    __tablename__ = "nrega_work_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class Slope(db.Model):
    __tablename__ = "nrega_slopes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    ridge_id = db.Column(db.Integer, db.ForeignKey("nrega_ridges.id"))


class WaterWork(db.Model):
    __tablename__ = "nrega_water_works"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class LocationSpecific(db.Model):
    __tablename__ = "nrega_location_specifics"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class PermissibleWork(db.Model):
    __tablename__ = "nrega_permissible_works"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class NatureOfWork(db.Model):
    __tablename__ = "nrega_nature_of_works"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    short_name = db.Column(db.String, nullable=True)
    

class MajorScheduledCategory(db.Model):
    __tablename__ = "nrega_major_scheduled_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)


class ActivityList(db.Model):
    __tablename__ = "nrega_activities_list"

    id = db.Column(db.Integer, primary_key=True)
    activity_type = db.Column(db.Integer, db.ForeignKey("nrega_activity_types.id"))
    beneficiary_type = db.Column(db.Integer, db.ForeignKey("nrega_beneficiaries.id"))
    cluster_type = db.Column(db.Integer, db.ForeignKey("nrega_clusters.id"))
    major_scheduled_category = db.Column(db.Integer, db.ForeignKey("nrega_major_scheduled_categories.id"))
    category = db.Column(db.Integer, db.ForeignKey("nrega_categories.id"))
    nature_of_work = db.Column(db.Integer, db.ForeignKey("nrega_nature_of_works.id"))
    permissible_work = db.Column(db.Integer, db.ForeignKey("nrega_permissible_works.id"))
    location_specifics = db.Column(db.Integer, db.ForeignKey("nrega_location_specifics.id"))
    water_work = db.Column(db.Integer, db.ForeignKey("nrega_water_works.id"))
    work_type = db.Column(db.Integer, db.ForeignKey("nrega_work_types.id"))
    slope = db.Column(db.Integer, db.ForeignKey("nrega_slopes.id"))
    ridge = db.Column(db.Integer, db.ForeignKey("nrega_ridges.id"))


    # Relationships
    activitytype = db.relationship("ActivityType", backref="nrega_activities_list")
    beneficiary = db.relationship("Beneficiary", backref="nrega_activities_list")
    cluster = db.relationship("Cluster", backref="nrega_activities_list")
    majorcategory = db.relationship("MajorScheduledCategory", backref="nrega_activities_list")
    category_rel = db.relationship("Category", backref="nrega_activities_list")
    nature_of_work_rel = db.relationship("NatureOfWork", backref="nrega_activities_list")
    permissible = db.relationship("PermissibleWork", backref="nrega_activities_list")
    location_specific = db.relationship("LocationSpecific", backref="nrega_activities_list")
    water = db.relationship("WaterWork", backref="nrega_activities_list")
    worktype = db.relationship("WorkType", backref="nrega_activities_list")
    slope_rel = db.relationship("Slope", backref="nrega_activities_list")
    ridge_rel = db.relationship("Ridge", backref="nrega_activities_list")

