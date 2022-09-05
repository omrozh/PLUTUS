import flask
from flask_sqlalchemy import SQLAlchemy
from uuid import uuid4
from flask_mail import Mail, Message
import random
from flask_bcrypt import Bcrypt
from datetime import datetime


app = flask.Flask(__name__)
app.config["SECRET_KEY"] = "PLUTUS-TEST-KEY"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"

app.config['MAIL_SERVER'] = 'smtp.google.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'noreply@getplutus.io'
app.config['MAIL_PASSWORD'] = 'jhel lnxf dtqi wide'
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


class User(db.Model):
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    one_time_code = db.Column(db.Integer)
    number_of_tickets = db.Column(db.String, default=0)
    email_verified = db.Column(db.Boolean, default=False)
    try_balance = db.Column(db.Float)


class PlatinumSubscription(db.Model):
    id = db.Column(db.String, primary_key=True)
    user_fk = db.Column(db.String)
    timestamp = db.Column(db.DateTime)


class CrystalSubscription(db.Model):
    id = db.Column(db.String, primary_key=True)
    user_fk = db.Column(db.String)
    timestamp = db.Column(db.DateTime)


class DailyLottery(db.Column):
    id = db.Column(db.String, primary_key=True)
    amount = db.Column(db.String)
    day = db.Column(db.Integer)
    month = db.Column(db.Integer)
    year = db.Column(db.Integer)


class MessageForUser(db.Column):
    id = db.Column(db.String, primary_key=True)
    user_fk = db.Column(db.String)
    message_content = db.Column(db.String)
    timestamp = db.Column(db.DateTime)


class LotteryParticipation(db.Model):
    id = db.Column(db.String, primary_key=True)
    dl_fk = db.Column(db.String)
    user_fk = db.Column(db.String)


class Session(db.Model):
    id = db.Column(db.String, primary_key=True)
    user_fk = db.Column(db.String)


def send_verification_message(user_code, user):
    msg = Message("Welcome to Plutus",
                  sender="noreply@getplutus.io",
                  recipients=[user.email])
    msg.body = f'''
        Welcome to Plutus,
        Use the link bellow to verify your account:
        https://getplutus.io/verify/{user_code}/{user.id}
        
        Please do not share this link with anyone.
    '''


@app.route("/create-user", methods=["POST"])
def create_user():
    values = flask.request.values
    new_user = User(id=str(uuid4()), email=values["email"], password=bcrypt.generate_password_hash(values["password"]),
                    one_time_code=random.randint(999999, 9999999))
    db.session.add(new_user)
    db.session.commit()

    return "User Creation Successful"


@app.route("/create-session", methods=["POST"])
def create_session():
    values = flask.request.values
    login_user = User.query.filter_by(email=values["email"]).first()
    if bcrypt.check_password_hash(login_user.password, values["password"]):
        new_session = Session(id=str(uuid4()), user_fk=login_user.id)
        db.session.add(new_session)
        db.session.commit()

        return new_session.id


@app.route("/get-info-for-user/<info_type>", methods=["POST"])
def get_info_for_user(info_type):
    values = flask.request.values

    get_session = Session.query.get(values["sessionId"])
    get_user = User.query.get(get_session.user_fk)

    if info_type == "number_of_tickets":
        return str(get_user.number_of_tickets)

    elif info_type == "try_balance":
        return str(get_user.try_balance)


@app.route("/earn-ticket")
def earn_ticket():
    # update later after appodeal integration
    pass


@app.route("/participate-to-lottery", methods=["POST"])
def participate_to_lottery():
    values = flask.request.values

    get_session = Session.query.get(values["sessionId"])
    get_user = User.query.get(get_session.user_fk)

    today_lottery = DailyLottery.query.filter_by(day=datetime.today().day).filter_by(month=datetime.today().month). \
        filter_by(year=datetime.today().year).first()

    if get_user.number_of_tickets > 0:
        user_is_crystal_member = CrystalSubscription.query.filter_by(user_fk=get_user.id).first() is not None
        user_is_platinum_member = PlatinumSubscription.query.filter_by(user_fk=get_user.id).first() is not None

        number_of_times = 4 if user_is_crystal_member else 2 if user_is_platinum_member else 1

        for i in range(1):
            new_lottery_participant = LotteryParticipation(id=str(uuid4()), dl_fk=today_lottery.id, user_fk=get_user.id)

            db.session.add(new_lottery_participant)

        get_user.number_of_tickets -= 1

        db.session.commit()

        return "Received Lottery Application"


@app.route("/get-daily-lottery-participation-number", methods=["POST"])
def daily_lottery_participation_number():
    values = flask.request.values

    get_session = Session.query.get(values["sessionId"])
    get_user = User.query.get(get_session.user_fk)

    today_lottery = DailyLottery.query.filter_by(day=datetime.today().day).filter_by(month=datetime.today().month). \
        filter_by(year=datetime.today().year).first()

    return str(len(LotteryParticipation.query.filter_by(dl_fk=today_lottery.id).filter_by(user_fk=get_user.id).all()))


@app.route("/get-daily-lottery-pool")
def get_daily_lottery_pool():
    today_lottery = DailyLottery.query.filter_by(day=datetime.today().day).filter_by(month=datetime.today().month).\
        filter_by(year=datetime.today().year).first()
    return str(today_lottery.amount)


@app.route("/refresh-session", methods=["POST"])
def refresh_session():
    values = flask.request.values

    get_session = Session.query.get(values["sessionId"])
    get_session.id = str(uuid4())

    db.session.commit()

    return get_session.id


@app.route("/verify-session", methods=["POST"])
def verify_session():
    values = flask.request.values

    get_session = None

    if not values["sessionId"] == "NO-SESSION":
        get_session = Session.query.get(values["sessionID"])

    if get_session is not None:
        return "SESSION RECOGNISED"
    else:
        raise KeyError


@app.route("/get-platinum", methods=["POST", "GET"])
def get_platinum():
    if flask.request.method == "POST":
        values = flask.request.values
        get_user = User.query.get(Session.query.get(values["sessionId"]).user_fk)

        if get_user.number_of_tickets >= 15:

            get_user.number_of_tickets -= 15
            new_platinum = PlatinumSubscription(timestamp=datetime.today(), user_fk=get_user.id)

            db.session.add(new_platinum)
            db.session.commit()

            return flask.render_template("platinum-approved.html")

        return flask.render_template("ineligible.html")

    return flask.render_template("get-platinum.html")
    # Webpage for platinum


@app.route("/get-crystal", methods=["POST", "GET"])
def get_crystal():
    if flask.request.method == "POST":
        values = flask.request.values
        get_user = User.query.get(Session.query.get(values["sessionId"]).user_fk)

        if get_user.number_of_tickets >= 25 and len(LotteryParticipation.query.filter_by(user_fk=get_user.id).all) > 74:
            get_user.number_of_tickets -= 25
            new_platinum = PlatinumSubscription(timestamp=datetime.today(), user_fk=get_user.id)

            db.session.add(new_platinum)
            db.session.commit()

            return flask.render_template("crystal-approved.html")
        return flask.render_template("ineligible.html")

    return flask.render_template("get-crystal.html")


@app.route("/get-messages", methods=["POST"])
def get_messages():
    values = flask.request.values
    get_user = User.query.get(Session.query.get(values["sessionId"]).user_fk)
    messages_for_user = [
        {
            "message_content": i.message_content,
            "timestamp": i.timestamp
        } for i in MessageForUser.query.filter_by(user_dk=get_user.id).all()
    ]

    return flask.jsonify(messages_for_user)
