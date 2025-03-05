# importing libs required
from flask import (Flask, render_template, request, send_file, session, Response, redirect, url_for, flash)
from flask_sqlalchemy import SQLAlchemy
from io import BytesIO
from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
#for 2nd push
from functools import wraps
import os
# import uuid

# init and config, of app and db
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///posts.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# creating tables using sqlalchemy ORM
class Adder(db.Model):
    __tablename__ = 'adders'
    id = db.Column(db.Integer, primary_key=True)
    adderId = db.Column(db.Text(150), nullable=False,  unique=True)
    password = db.Column(db.Text(150), nullable=False)
    # for next push
    role = db.Column(db.Text(50), default="admin")
    # Dummy data of adders are pre-populated

class User(db.Model):
    __tablename__ = 'users'
    userId = db.Column(db.Text, primary_key=True)
    name = db.Column(db.Text(150), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    blood = db.Column(db.Text(10), nullable=False)
    bloodDonateAva = db.Column(db.Boolean, default=False)
    bloodLocCity = db.Column(db.Text(50))
    #for next push
    role = db.Column(db.Text(50), default="user")
    # Dummy data of end users are pre-populated

class Hospital(db.Model):
    __tablename__ = 'hospitals'
    id = db.Column(db.Integer, primary_key=True)
    hospitalId = db.Column(db.Text, nullable=False,  unique=True)
    hospitalName = db.Column(db.Text(150), nullable=False)
    password = db.Column(db.Text(50), nullable=False)
    email = db.Column(db.Text, nullable=False,  unique=True)
    addedDate = db.Column(db.Date, nullable=False)
    adderId = db.Column(db.Text, db.ForeignKey('adders.adderId'))
    adder = db.relationship('Adder', backref='hospitals')
    hospitalLoc = db.Column(db.Text)
    phone = db.Column(db.Integer, unique=True)
    #for next push
    role = db.Column(db.Text(50), default="hospital")

    # adders add hospital data (not pre-populated)


class File(db.Model):
    __tablename__ = 'files'
    id = db.Column(db.Integer, primary_key=True)
    userId = db.Column(db.Text, db.ForeignKey('users.userId'))
    file_name = db.Column(db.Text(150), nullable=False)
    mimetype = db.Column(db.Text(50))
    category = db.Column(db.Text(50))
    data = db.Column(db.LargeBinary, nullable=False)
    hospitalId = db.Column(db.Text, db.ForeignKey('hospitals.hospitalId'))
    testPre = db.Column(db.Boolean, default=True)
    uploadDate = db.Column(db.Date, nullable=False)
    hospitalName = db.Column(db.Text(100))

    hospital = db.relationship('Hospital', backref='files')
    users = db.relationship('User', backref='files')

    # connected with both hospitals as well as users table
    # not pre-populated


#role based auth
def role_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "role" not in session or session["role"] not in roles:
                flash("Access denied!")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper


@app.route('/', methods=['POST', 'GET'])
def index():#
    if request.method == "POST":
        userId = request.form['name']
        password = request.form['password']

        try:

            user_info = User.query.filter_by(userId=userId).first()
            #print(int(password) == user_info.number)
            if user_info and user_info.number == int(password):
                session["userId"] = user_info.userId
                session["role"] = user_info.role
                return redirect(url_for('display', userId=user_info.userId))

            flash("Invalid credentials")

            return redirect(url_for('index'))
        except ValueError:
            flash("Invalid credentials")
    return render_template('index.html')


@app.route('/LoginAsAuth', methods=['POST', 'GET'])
def LoginAsAuth():
    if request.method == 'POST':
        hosAuth = request.form['hosAuth']
        Id = request.form['Id']
        password = request.form['password']
        if hosAuth == "Hospital":
            hospital_info = Hospital.query.filter_by(hospitalId=Id).first()
            if hospital_info and hospital_info.password == password:
                session["userId"] = hospital_info.hospitalId
                session["role"] = hospital_info.role
                return redirect(url_for('hospital', name=hospital_info.hospitalName, Id=hospital_info.hospitalId))
            flash("invalid cre.")
        else:
            adder = Adder.query.filter_by(adderId=Id).first()
            if adder and adder.password == password:
                session["userId"] = adder.adderId
                session["role"] = adder.role
                return redirect(url_for('authority', Id=adder.adderId))
            flash("invalid cre")
    return render_template('loginAuth.html')


@app.route('/authAdder/<string:Id>', methods=["POST", "GET"])
@role_required('admin')
def authority(Id):#
    hos_info = Hospital.query.filter_by(adderId=Id).all()
    if request.method == 'POST':
        hospitalId = request.form['hospitalId']
        hospitalName = request.form['hospitalName']
        password = request.form['password']
        email = request.form['email']
        hospitalLoc = request.form['hospitalLoc']
        try:
            addHospital = Hospital(hospitalId=hospitalId,
                                   hospitalName=hospitalName,
                                   password=password,
                                   email=email,
                                   addedDate=datetime.now().date(),
                                   adderId=Id,
                                   hospitalLoc=hospitalLoc)

            db.session.add(addHospital)
            db.session.commit()

            return redirect(url_for('authority', Id=Id))
        except IntegrityError:
            flash("you are entering the Credentials that are not unique")
            return redirect(url_for('authority', Id=Id))

    return render_template('adder.html', info=hos_info, adderId=Id)

@app.route('/authAdder/<string:adderId>/<string:Id>', methods=['POST', 'GET'])
@role_required('admin')
def adderOpreEdit(adderId, Id):#
    hospital_info = Hospital.query.filter_by(hospitalId=Id).first()
    if request.method == 'POST':
        hospitalName = request.form['hospitalName']
        password = request.form['password']
        email = request.form['email']

        hospital_info.hospitalName = hospitalName
        hospital_info.password = password
        hospital_info.email = email
        db.session.commit()
        return redirect(url_for('authority', Id=adderId))
    return render_template("adderEdit.html", hospital_info=hospital_info, adderId=adderId, Id=Id)

@app.route('/delete/<string:adderId>/<string:Id>', methods=["DELETE", "GET", "POST"])
@role_required('admin')
def delete(adderId, Id):#
    if request.method == "GET":
        deleteHospital = Hospital.query.filter_by(hospitalId=Id).first()
        if deleteHospital:
            db.session.delete(deleteHospital)
            db.session.commit()
    return redirect(url_for('authority', Id=adderId))


@app.route('/hospital/<string:name>/<string:Id>', methods=['POST', 'GET'])
@role_required('hospital')
def hospital(name, Id):
    # display hospital's
    if request.method == "POST":
        file = request.files['file']
        test = request.form['test']
        # print(test)
        filename = request.form['filename']
        userId = request.form['userId']
        category = request.form['category']
        date = datetime.now().date()

        user = User.query.filter_by(userId=userId).first()
        if user:
                # print("down1")
                # print(filename.endswith(('.pdf', '.jpg', '.jpeg', '.png')))
                # if file.mimetype in ['pdf', 'jpg', 'png']:
            if file.filename.endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                #   print("down2")
                if test == 'true':
                    test = 1
                        # print(test)
                else:
                    test = 0
                #print(test)
                to_upload = File(userId=userId,
                                 file_name=filename,
                                 mimetype=file.mimetype,
                                 category=category,
                                 data=file.read(),
                                 hospitalId=Id,
                                 testPre=test,
                                 uploadDate=date,
                                 hospitalName=name)
                # print("down3")
                db.session.add(to_upload)
                db.session.commit()
                # print("down4")
                return redirect(url_for('hospital', name=name, Id=Id))

            flash("invalid formate")
            return redirect(url_for('hospital', name=name, Id=Id))

        flash("Person not found")
        return redirect(url_for('hospital', name=name, Id=Id))

    files = File.query.filter_by(hospitalId=Id).order_by(File.uploadDate.desc()).all()
    return render_template('HospitalDisplay.html', files=files, name=name, Id=Id)

@app.route('/user/<string:userId>', methods=['POST', 'GET'])
@role_required('user')
def display(userId):
    # display user's
    file = File.query.filter_by(userId=userId).all()
    user_info = User.query.filter_by(userId=userId).first()
    bloodcon = user_info.bloodDonateAva
    return render_template('endUser.html', images=file, userId=userId, bloodcon=bloodcon)


@app.route('/display/<string:id>', methods=['POST', 'GET'])
@role_required('hospital','user')
def display_doc(id):
    image_info = File.query.get(id)
    if image_info:
        if 'pdf' in image_info.mimetype:
            return Response(image_info.data, mimetype=image_info.mimetype)
        return send_file(BytesIO(image_info.data), mimetype=image_info.mimetype)
    return "not exists"


@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    #print("session out")
    return redirect(url_for('index'))


compatible_blood_groups = {
        "AB+": ['O-', 'O+', 'B-', 'B+', 'A-', 'A+', 'AB-', 'AB+'],
        "AB-": ['O-', 'B-', 'A-', 'AB-'],
        "A+": ['O-', 'O+', 'A-', 'A+'],
        "A-": ['O-', 'A-'],
        "B+": ['O-', 'O+', 'B-', 'B+'],
        "B-": ['O-', 'B-'],
        "O+": ['O-', 'O+'],
        "O-": ['O-']
    }


@app.route('/BloodDonation/<string:userId>/<int:who>', methods=['GET', 'POST'])
@role_required('hospital', 'user')
def BloodDonation(userId, who):
    # print(type(who), who)
    if who == 0:
        currcent_user = 0
        user = User.query.filter_by(userId=userId).first()
        c = compatible_blood_groups.get(user.blood, [])
        # print(c)
        name = None
        if request.method == 'POST':
            location = request.form['loc'].lower()
            # print(location)
            available_users = User.query.filter(
                and_(
                    User.blood.in_(c),
                    User.bloodDonateAva == True,
                    User.userId != userId,
                    User.bloodLocCity == location
                )
            ).all()
        else:
            available_users = User.query.filter(
                and_(
                    User.blood.in_(c),
                    User.bloodDonateAva == True,
                    User.userId != userId
                )
            ).all()
    else:
        currcent_user = 1
        # print(currcent_user)
        hospital = Hospital.query.filter_by(hospitalId=userId).first()
        name = hospital.hospitalName
        # print(hospital)
        if request.method == 'POST':
            # print(1)
            blood_group = request.form['filter']
            # print(blood_group)
            available_users = User.query.filter(
                and_(
                    User.bloodDonateAva == True,
                    User.bloodLocCity == hospital.hospitalLoc,
                    User.blood == blood_group
                )
            ).all()
            # print(available_users)
        else:
            # print(1)
            # available_users = User.query.all()
            """available_users = User.query.filter(
                and_(
                    User.bloodDonateAva == 'True',
                    User.bloodLocCity == hospital.hospitalLoc
                )
            ).all()"""
            available_users = User.query.filter_by(bloodDonateAva=True, bloodLocCity=hospital.hospitalLoc).all()
            # print(available_users)

    return render_template('blood.html',
                           userId=userId,
                           available_users=available_users,
                           currcent_user=currcent_user,
                           name=name)
# stopped, done with user blood view


@app.route('/permision-for-blood/<string:userId>', methods=['POST', 'GET'])
@role_required('user')
def bloodPermision(userId):
    user_info = User.query.filter_by(userId=userId).first()
    if request.method == "POST":
        permision = request.form['permision']
        # print(type(bool(permision)))
        if permision == "True":
            user_info.bloodDonateAva = True
        else:
            user_info.bloodDonateAva = False
        db.session.commit()
    bloodcon = user_info.bloodDonateAva
    return redirect(url_for('display', userId=userId, bloodcon=bloodcon))


@app.route('/user/<string:userId>/filter', methods=['POST', 'GET'])
@role_required('user')
def filterByCategory(userId):
    if request.method == "POST":
        category = request.form['category']
        file = File.query.filter(
            and_(
                File.userId == userId,
                File.category == category
            )
        ).all()
        user_info = User.query.filter_by(userId=userId).first()
        bloodcon = user_info.bloodDonateAva
        return render_template('endUser.html', images=file, userId=userId, bloodcon=bloodcon)
    return redirect(url_for('display', userId=userId))

@app.route('/user/<string:userId>/hospitals', methods=['POST', 'GET'])
@role_required('hospital','user')
def viewHospitals(userId):
    hospitalList = Hospital.query.all()
    if request.method == "POST":
        loc = request.form["searchLoc"].lower()
        hospitalList = Hospital.query.filter_by(hospitalLoc=loc).all()
    #print(hospitalList[0].hospitalLoc)
    return render_template('hospitalList.html', hospitalList=hospitalList, userId=userId)



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=False)