from datetime import datetime

from flask import Flask
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
db = SQLAlchemy()


class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(256))
    title = db.Column(db.String(256))
    date_time = db.Column(db.DateTime, default=datetime.now())
    content = db.Column(db.String())
    image = db.Column(db.String(256))


class Laws(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    continent = db.Column(db.String(20))
    country = db.Column(db.String(50))
    laws = db.Column(db.String())


class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_email = db.Column(db.String(256), unique=True)
    google_name = db.Column(db.String(256))
    twitter_user_name = db.Column(db.String(256), unique=True)
    twitter_name = db.Column(db.String(256))
    user_name = db.Column(db.String(256), unique=True)
    email = db.Column(db.String(256), unique=True)
    profile_pic = db.Column(db.String(256), default="https://i.ibb.co/8mq8Tfh/default.jpg")
    password = db.Column(db.String(256))

    def __init__(self, google_email, google_name, twitter_user_name, twitter_name, user_name, email,
                 password):
        self.google_email = google_email
        self.google_name = google_name
        self.twitter_user_name = twitter_user_name
        self.twitter_name = twitter_name
        self.user_name = user_name
        self.email = email
        if password is not None:
            self.password = generate_password_hash(password)
        else:
            self.password = password

    def check_password(self, password):
        return check_password_hash(self.password, password)


class OAuth(OAuthConsumerMixin, db.Model):
    provider_user_id = db.Column(db.String(256), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(Users.id), nullable=False)
    user = db.relationship(Users)


login_manager = LoginManager()
login_manager.login_view = 'signup'


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))
