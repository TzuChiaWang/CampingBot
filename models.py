from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()


class Campsite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    altitude = db.Column(db.String(50))
    features = db.Column(db.String(200))
    WC = db.Column(db.String(100))
    signal_strength = db.Column(db.String(100), nullable=True)
    pets = db.Column(db.String(100))
    facilities = db.Column(db.String(200))
    sideservice = db.Column(db.String(200))
    open_time = db.Column(db.String(100))
    parking = db.Column(db.String(100))
    image_urls = db.Column(JSON, nullable=True)
    booking_url = db.Column(db.String(300))
    social_url = db.Column(db.String(300))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "altitude": self.altitude,
            "features": self.features.split(" "),
            "WC": self.WC,
            "singal_strength": self.singal,
            "pets": self.pets,
            "facilities": self.facilities.split(" "),
            "sideservice": self.sideservice,
            "open_time": self.open_time,
            "parking": self.parking,
            "image_url": self.image_url,
            "booking_url": self.booking_url,
            "social_url": self.social_url,
        }
