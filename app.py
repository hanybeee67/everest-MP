from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# DB 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///members.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# DB 모델
class Members(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    phone = db.Column(db.String(20), unique=True)
    branch = db.Column(db.String(50))
    reg_date = db.Column(db.String(20))


# 메인 페이지
@app.route('/')
def index():
    return redirect('/unified?branch=dongdaemun')


# 신규 가입
@app.route('/join', methods=['GET', 'POST'])
def join():
    branch = request.args.get('branch')
    phone = request.args.get('phone')

    if request.method == 'POST':
        name = request.form['name']
        reg_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        new_member = Members(name=name, phone=phone, branch=branch, reg_date=reg_date)
        db.session.add(new_member)
        db.session.commit()

        return render_template("success.html", name=name, branch=branch)

    return render_template("join.html", branch=branch, phone=phone)


# 재방문
@app.route('/visit')
def visit():
    branch = request.args.get('branch')
    phone = request.args.get('phone')
    return render_template("visit.html", branch=branch, phone=phone)


# 하나의 QR → 초기 화면
@app.route('/unified')
def unified():
    branch = request.args.get('branch', 'dongdaemun')
    return render_template("unified.html", branch=branch)


# QR → 전화번호 → 자동 분기
@app.route('/unified-check', methods=['POST'])
def unified_check():
    phone = request.form['phone']
    branch = request.form['branch']

    user = Members.query.filter_by(phone=phone).first()

    if user is None:
        return redirect(f"/join?branch={branch}&phone={phone}")
    else:
        return redirect(f"/visit?branch={branch}&phone={phone}")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
