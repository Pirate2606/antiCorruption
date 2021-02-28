import base64
import json
import os
import re
import string

import requests
from flask import render_template, url_for, redirect, request, session
from flask_login import login_required, logout_user, login_user
from flask_uploads import UploadSet, configure_uploads, IMAGES
from werkzeug.routing import ValidationError

from cli import create_db
from config import Config
from models import db, app, Users, login_manager, Laws, Blog
from oauth import google, twitter

app.config.from_object(Config)
app.cli.add_command(create_db)
app.register_blueprint(google.blueprint, url_prefix="/login")
app.register_blueprint(twitter.blueprint, url_prefix="/login")
db.init_app(app)
login_manager.init_app(app)

# Upload Photos
photos = UploadSet('photos', IMAGES)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOADED_PHOTOS_DEST'] = 'static/pictures'
configure_uploads(app, photos)

# enabling insecure login for OAuth login
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'


@app.route('/')
def home():
    if not session.get('user_id'):
        return render_template("home.html")
    else:
        return render_template("home.html", username=Users.query.filter_by(id=session.get('user_id')).first().user_name)


@app.route('/sign_up', methods=['GET', 'POST'])
def signup():
    if session.get("user_id"):
        return redirect(url_for('home'))
    email_flag = False
    username_flag = False
    password_flag = False

    if request.method == "POST":
        user_name = request.form['username']
        email = request.form['email']
        password = request.form['password']

        password_flag = check_password(password)
        try:
            email_flag = check_mail(email)
        except ValidationError:
            email_flag = True

        try:
            username_flag = check_username(user_name)
        except ValidationError:
            username_flag = True

        if not username_flag and not email_flag and not password_flag and password_flag != "short":
            # Entering data into Database (Register table)
            user = Users(None, None, None, None, user_name, email, password)
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            login_user(user)

            return redirect(url_for('home'))

    return render_template('sign-up.html',
                           email_flag=email_flag,
                           username_flag=username_flag,
                           password_flag=password_flag)


@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if session.get("user_id"):
        return redirect(url_for('home'))
    flag = False
    if request.method == "POST":
        user = Users.query.filter_by(email=request.form['username']).first()
        if user is None:
            user = Users.query.filter_by(user_name=request.form['username']).first()
        if user is not None:
            if user.check_password(request.form['password']):
                user = Users.query.filter_by(email=user.email).first()
                session['user_id'] = user.id
                login_user(user)
                return redirect(url_for("home"))
            else:
                flag = True
        else:
            flag = True
    return render_template('sign-in.html', flag=flag)


# logout the user
@app.route("/logout")
@login_required
def logout():
    session.pop('user_id', None)
    logout_user()
    return redirect(url_for("home"))


@app.route('/laws')
def laws():
    laws_ = Laws().query.all()
    if not session.get('user_id'):
        return render_template("laws.html", laws=laws_)
    else:
        return render_template("laws.html",
                               laws=laws_,
                               username=Users.query.filter_by(id=session.get('user_id')).first().user_name)


@app.route('/laws/<country>')
def laws_with_country(country):
    law = Laws().query.filter_by(country=country).first()
    if not session.get('user_id'):
        return render_template("country_laws.html", law=law, country=country)
    else:
        return render_template("country_laws.html",
                               law=law,
                               country=country,
                               username=Users.query.filter_by(id=session.get('user_id')).first().user_name)


@app.route('/report_corruption')
def report():
    all_countries = ['Argentina', 'Bangladesh', 'Brazil', 'Bulgaria', 'Cambodia',
                     'Chile', 'Columbia', 'Czech Republic', 'France', 'Georgia',
                     'Hungary', 'Ireland', 'Italy', 'Jamaica', 'Jordan', 'Kenya',
                     'Madagascar', 'Morocco', 'Nepal', 'Nigeria', 'Pakistan', 'Peru',
                     'Portugal', 'Russia', 'South Africa', 'Sri Lanka', 'Uganda', 'Zimbabwe']
    urls = []
    for c in all_countries:
        if " " in c:
            c = c.replace(" ", "-")
        url = "https://www.transparency.org/en/report-corruption/" + c.lower()
        urls.append(url)
    if not session.get('user_id'):
        return render_template("report.html", all_countries=all_countries, urls=urls)
    else:
        return render_template("report.html",
                               all_countries=all_countries,
                               urls=urls,
                               username=Users.query.filter_by(id=session.get('user_id')).first().user_name)


@app.route('/blog/<title>')
def individual_blog(title):
    id_ = request.args.get("v")
    blog_ = Blog().query.filter_by(id=id_).first()
    if not session.get('user_id'):
        return render_template("individual_blog.html", blog_=blog_)
    else:
        return render_template("individual_blog.html",
                               blog_=blog_,
                               username=Users.query.filter_by(id=session.get('user_id')).first().user_name)


@app.route('/all_blog')
def all_blog():
    blog = Blog().query.all()
    urls = []
    for b in blog:
        b = b.title.replace(" ", "-")
        urls.append(b.lower())
    total_items = len(blog)
    number_of_rows = (len(blog) // 3) + 1
    if not session.get('user_id'):
        return render_template("blog.html", blog=blog, number_of_rows=number_of_rows, total_items=total_items, urls=urls)
    else:
        return render_template("blog.html",
                               blog=blog,
                               number_of_rows=number_of_rows,
                               total_items=total_items,
                               urls=urls,
                               username=Users.query.filter_by(id=session.get('user_id')).first().user_name)


@app.route('/create_blog', methods=["GET", "POST"])
@login_required
def create_blog():
    blog = Blog()
    if request.method == "POST":
        file = request.files['blog_pic']
        if 'blog_pic' in request.files and allowed_file(file.filename):
            image_filename = photos.save(file)
            static = os.path.join(os.path.curdir, "static")
            pictures = os.path.join(static, "pictures")
            image_location = os.path.join(pictures, image_filename)
            with open(image_location, "rb") as file:
                url = "https://api.imgbb.com/1/upload"
                payload = {
                    "key": '00a33d9bbaa2f24bf801c871894e91d4',
                    "image": base64.b64encode(file.read()),
                }
                res = requests.post(url, payload)
                str_name = ""
                for r in res:
                    str_name += r.decode("utf8")
                blog.image = json.loads(str_name)['data']['url']
        title = request.form["title"]
        content = request.form["content"]
        blog.user_name = Users.query.filter_by(id=session['user_id']).first().user_name
        blog.title = title
        blog.content = content
        db.session.add(blog)
        db.session.commit()
        return redirect("all_blog")
    return render_template("create_blog.html",
                           username=Users.query.filter_by(id=session.get('user_id')).first().user_name)


@app.route('/profile/<username>')
@login_required
def profile(username):
    user = Users.query.filter_by(user_name=username).first_or_404()
    blog_posted = Blog.query.filter_by(user_name=username).all()
    number_of_blog = len(blog_posted)
    formatted_date = []
    urls = []
    for blog in blog_posted:
        b = blog.title.replace(" ", "-")
        urls.append(b.lower())
        date_time = blog.date_time
        formatted_date.append(date_time.strftime("%b %d, %Y | %H:%M"))
    if len(formatted_date) == 0:
        formatted_date = ["None"]
    return render_template("profile.html",
                           user=user,
                           blog_posted=blog_posted,
                           number_of_blog=number_of_blog,
                           formatted_date=formatted_date,
                           urls=urls,
                           username=Users.query.filter_by(id=session.get('user_id')).first().user_name)


@app.errorhandler(404)
def error_404(error):
    return render_template('404.html'), 404


@app.errorhandler(403)
def error_403(error):
    return render_template('403.html'), 403


# Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def check_mail(data):
    if Users.query.filter_by(email=data).first():
        raise ValidationError('Your email is already registered.')
    else:
        return False


def check_username(data):
    if Users.query.filter_by(user_name=data).first():
        raise ValidationError('This username is already registered.')
    else:
        return False


def check_password(data):
    special_char = string.punctuation
    if len(data) < 6:
        return "short"
    elif not re.search("[a-zA-Z]", data):
        return True
    elif not re.search("[0-9]", data):
        return True
    for char in data:
        if char in special_char:
            break
    else:
        return True
    return False


if __name__ == '__main__':
    app.run()
