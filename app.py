from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# DB 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///members_new.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# DB 모델
class Members(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    phone = db.Column(db.String(20), unique=True)
    branch = db.Column(db.String(50))
    reg_date = db.Column(db.String(20))


# 🔥 Render 서버에서도 테이블이 자동으로 생성되도록 보장하는 코드
with app.app_context():
    db.create_all()


# 루트 URL → 통합 QR 화면으로 자동 이동
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


# 하나의 QR → 전화번호 입력 화면
@app.route('/unified')
def unified():
    branch = request.args.get('branch', 'dongdaemun')
    return render_template("unified.html", branch=branch)


# 전화번호 입력 후 자동 분기
@app.route('/unified-check', methods=['POST'])
def unified_check():
    phone = request.form['phone']
    branch = request.form['branch']

    user = Members.query.filter_by(phone=phone).first()

    if user is None:
        return redirect(f"/join?branch={branch}&phone={phone}")
    else:
        return redirect(f"/visit?branch={branch}&phone={phone}")


# 실행 (로컬 개발용)
if __name__ == "__main__":
    app.run(debug=True)
