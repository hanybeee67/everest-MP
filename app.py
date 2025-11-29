from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# ===========================
# DB 설정
# ===========================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///members_new.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ===========================
# DB 모델
# ===========================
class Members(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    phone = db.Column(db.String(20), unique=True)
    branch = db.Column(db.String(50))
    birth = db.Column(db.String(20))
    marketing = db.Column(db.String(5))
    privacy = db.Column(db.String(5))
    reg_date = db.Column(db.String(20))


# Render/로컬 모두에서 자동으로 테이블 생성
with app.app_context():
    db.create_all()


# ===========================
# 루트 → 통합 화면으로 이동
# ===========================
@app.route('/')
def index():
    return redirect('/unified?branch=dongdaemun')


# ===========================
# 신규가입
# ===========================
@app.route('/join', methods=['GET', 'POST'])
def join():
    branch = request.args.get('branch')
    phone = request.args.get('phone')

    if request.method == 'POST':
        name = request.form['name']
        birth = request.form['birth']
        marketing = request.form.get('marketing', 'no')
        privacy = request.form.get('privacy', 'no')
        reg_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        new_member = Members(
            name=name,
            phone=phone,
            branch=branch,
            birth=birth,
            marketing=marketing,
            privacy=privacy,
            reg_date=reg_date
        )

        db.session.add(new_member)
        db.session.commit()

        return render_template("success.html", name=name, branch=branch)

    return render_template("join.html", branch=branch, phone=phone)


# ===========================
# 재방문 체크
# ===========================
@app.route('/visit')
def visit():
    branch = request.args.get('branch')
    phone = request.args.get('phone')
    return render_template("visit.html", branch=branch, phone=phone)


# ===========================
# 🔥 관리자 페이지 (전체 회원 조회)
# /admin/members
# ===========================
@app.route('/admin/members')
def admin_members():
    members = Members.query.all()
    return render_template("members.html", members=members)


# ===========================
# 하나의 QR → 전화번호 입력 화면
# ===========================
@app.route('/unified')
def unified():
    branch = request.args.get('branch', 'dongdaemun')
    return render_template("unified.html", branch=branch)


# ===========================
# 전화번호 입력 후 신규/재방문 자동 분기
# ===========================
@app.route('/unified-check', methods=['POST'])
def unified_check():
    phone = request.form['phone']
    branch = request.form['branch']

    user = Members.query.filter_by(phone=phone).first()

    if user is None:
        return redirect(f"/join?branch={branch}&phone={phone}")
    else:
        return redirect(f"/visit?branch={branch}&phone={phone}")


# ===========================
# 실행 (로컬 개발용)
# ===========================
if __name__ == "__main__":
    app.run(debug=True)
