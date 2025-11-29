from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# ===== DB 설정 =====
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///members.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# ===== DB 모델 =====
class Members(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    birth = db.Column(db.String(20))
    branch = db.Column(db.String(50))
    agree_marketing = db.Column(db.String(5))
    agree_privacy = db.Column(db.String(5))
    created_at = db.Column(db.String(30))


# ===== 첫 실행 시 테이블 생성 =====
with app.app_context():
    db.create_all()


# ============================================
# 1) 루트 → 지점 선택 페이지
# ============================================
@app.route("/")
def index():
    return render_template("branch_select.html")


# ============================================
# 2) unified: 전화번호 입력 → 신규/재방문 체크
# ============================================
@app.route("/unified", methods=["GET", "POST"])
def unified():
    if request.method == "GET":
        branch = request.args.get("branch", None)
        return render_template("unified.html", branch=branch)

    # POST 요청이면 등록·재방문 체크
    phone = request.form.get("phone")
    branch = request.form.get("branch")

    exist = Members.query.filter_by(phone=phone).first()

    if exist:
        # 재방문
        name = exist.name
        return render_template("visit.html", name=name)

    else:
        # 신규 가입 페이지로 이동
        return render_template("join.html", phone=phone, branch=branch)


# ============================================
# 3) 신규 가입(join)
# ============================================
@app.route("/join", methods=["POST"])
def join():
    name = request.form.get("name")
    phone = request.form.get("phone")
    branch = request.form.get("branch")
    birth = request.form.get("birth")

    agree_marketing = "yes" if request.form.get("agree_marketing") else "no"
    agree_privacy = "yes" if request.form.get("agree_privacy") else "no"

    new_member = Members(
        name=name,
        phone=phone,
        branch=branch,
        birth=birth,
        agree_marketing=agree_marketing,
        agree_privacy=agree_privacy,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    db.session.add(new_member)
    db.session.commit()

    return render_template("success.html", name=name)


# ============================================
# 4) 관리자 페이지 (정렬 기능)
# ============================================
@app.route("/admin/members")
def admin_members():
    sort_type = request.args.get("sort", "date")

    if sort_type == "name":
        members = Members.query.order_by(Members.name.asc()).all()
    elif sort_type == "branch":
        members = Members.query.order_by(Members.branch.asc()).all()
    else:
        members = Members.query.order_by(Members.id.desc()).all()

    return render_template("members.html", members=members)


# ============================================
# 5) 서버 실행
# ============================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
