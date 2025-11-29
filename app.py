from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# ===== DB 설정 =====
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///members.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# ===== DB 모델 정의 =====
class Members(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    birth = db.Column(db.String(20))
    branch = db.Column(db.String(50))
    agree_marketing = db.Column(db.String(5))
    agree_privacy = db.Column(db.String(5))
    visit_count = db.Column(db.Integer, default=1)      # ★ 방문횟수
    last_visit = db.Column(db.String(20))               # ★ 하루 1회 제한 일자
    created_at = db.Column(db.String(30))


# ===== DB 자동 생성 =====
with app.app_context():
    db.create_all()


# ============================================
# 1) 첫 화면 → 지점 선택
# ============================================
@app.route("/")
def index():
    return render_template("branch_select.html")


# ============================================
# 2) unified: 전화번호 입력 → 신규/재방문 분기
# ============================================
@app.route("/unified", methods=["GET", "POST"])
def unified():
    # GET: 지점 선택 화면에서 넘어옴
    if request.method == "GET":
        branch = request.args.get("branch", None)
        return render_template("unified.html", branch=branch)

    # POST: 전화번호 입력 후 처리
    phone = request.form.get("phone")
    branch = request.form.get("branch")

    exist = Members.query.filter_by(phone=phone).first()
    today = datetime.now().strftime("%Y-%m-%d")

    if exist:
        # ★ 하루 1회 방문 제한 — last_visit이 오늘과 다를 때만 증가
        if exist.last_visit != today:
            exist.visit_count += 1
            exist.last_visit = today
            db.session.commit()

        return render_template("visit.html", name=exist.name)

    # 신규 가입
    return render_template("join.html", phone=phone, branch=branch)


# ============================================
# 3) 신규 가입 처리
# ============================================
@app.route("/join", methods=["POST"])
def join():
    name = request.form.get("name")
    phone = request.form.get("phone")
    branch = request.form.get("branch")
    birth = request.form.get("birth")

    agree_marketing = "yes" if request.form.get("agree_marketing") else "no"
    agree_privacy = "yes" if request.form.get("agree_privacy") else "no"

    today = datetime.now().strftime("%Y-%m-%d")

    new_member = Members(
        name=name,
        phone=phone,
        branch=branch,
        birth=birth,
        agree_marketing=agree_marketing,
        agree_privacy=agree_privacy,
        visit_count=1,                 # ★ 신규 가입자는 방문횟수 1로 시작
        last_visit=today,               # ★ 마지막 방문 = 가입일
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    db.session.add(new_member)
    db.session.commit()

    return render_template("success.html", name=name)


# ============================================
# 4) 관리자 페이지 (정렬 + 통계)
# ============================================
@app.route("/admin/members")
def admin_members():
    sort = request.args.get("sort", "date")

    # 정렬 조건
    if sort == "name":
        members = Members.query.order_by(Members.name.asc()).all()
    elif sort == "branch":
        members = Members.query.order_by(Members.branch.asc()).all()
    elif sort == "visit":
        members = Members.query.order_by(Members.visit_count.desc()).all()
    else:
        members = Members.query.order_by(Members.id.desc()).all()

    # ===== 통계 값 계산 =====
    total_members = Members.query.count()

    today = datetime.now().strftime("%Y-%m-%d")
    today_members = Members.query.filter(Members.created_at.contains(today)).count()

    # 지점별 회원수 → 가장 회원 많은 지점 계산
    branch_group = db.session.query(
        Members.branch,
        db.func.count(Members.branch)
    ).group_by(Members.branch).all()

    if branch_group:
        top_branch_name, top_branch_count = max(branch_group, key=lambda x: x[1])
    else:
        top_branch_name, top_branch_count = "없음", 0

    # 전체 방문 횟수 합산
    total_visits = db.session.query(db.func.sum(Members.visit_count)).scalar() or 0

    return render_template(
        "members.html",
        members=members,
        sort=sort,
        total_members=total_members,
        today_members=today_members,
        top_branch_name=top_branch_name,
        top_branch_count=top_branch_count,
        total_visits=total_visits
    )


# ============================================
# 서버 실행
# ============================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
