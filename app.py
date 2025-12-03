from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///members.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# =========================
# 1) 회원 테이블
# =========================
class Members(db.Model):
    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)
    branch = db.Column(db.String(50))
    name = db.Column(db.String(50))
    phone = db.Column(db.String(50), unique=True)
    birth = db.Column(db.String(20))
    visit_count = db.Column(db.Integer, default=1)
    marketing = db.Column(db.Boolean, default=False)
    privacy = db.Column(db.Boolean, default=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)


# =========================
# 2) 쿠폰 테이블
# =========================
class Coupons(db.Model):
    __tablename__ = "coupons"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"))
    coupon_type = db.Column(db.String(50))  # WELCOME / VISIT3 / VISIT5 / VISIT10 / BIRTHDAY
    issue_date = db.Column(db.DateTime, default=datetime.utcnow)
    used = db.Column(db.Boolean, default=False)

    member = db.relationship("Members", backref=db.backref("coupons", lazy=True))


# =========================
# 3) 쿠폰 발급 로직 함수
# =========================
def issue_coupons_if_needed(member, visit_before, visit_after):
    """
    visit_before: 변경 전 방문 횟수
    visit_after : 변경 후 방문 횟수
    반환값: 새로 발급된 쿠폰 타입 리스트 (예: ["WELCOME", "VISIT3"])
    """
    coupons_issued = []

    # 1) 신규가입 웰컴 쿠폰: 0 → 1일 때 한 번만
    if visit_before == 0 and visit_after == 1:
        c = Coupons(member_id=member.id, coupon_type="WELCOME")
        db.session.add(c)
        coupons_issued.append("WELCOME")

    # 2) 3회 방문 쿠폰
    if visit_after >= 3 and visit_before < 3:
        c = Coupons(member_id=member.id, coupon_type="VISIT3")
        db.session.add(c)
        coupons_issued.append("VISIT3")

    # 3) 5회 방문 쿠폰
    if visit_after >= 5 and visit_before < 5:
        c = Coupons(member_id=member.id, coupon_type="VISIT5")
        db.session.add(c)
        coupons_issued.append("VISIT5")

    # 4) 10회 방문 쿠폰
    if visit_after >= 10 and visit_before < 10:
        c = Coupons(member_id=member.id, coupon_type="VISIT10")
        db.session.add(c)
        coupons_issued.append("VISIT10")

    # 5) 생일 쿠폰 (연 1회)
    if member.birth:
        # birth는 "YYYYMMDD" 형식이라고 가정
        today_md = datetime.today().strftime("%m%d")
        if len(member.birth) >= 8:
            birth_md = member.birth[4:8]  # MMDD
        else:
            birth_md = ""

        if today_md == birth_md:
            # 최근 1년 내에 발급된 생일쿠폰이 있는지 검사
            one_year_ago = datetime.today() - timedelta(days=365)
            existing = Coupons.query.filter(
                Coupons.member_id == member.id,
                Coupons.coupon_type == "BIRTHDAY",
                Coupons.issue_date >= one_year_ago
            ).first()

            if not existing:
                c = Coupons(member_id=member.id, coupon_type="BIRTHDAY")
                db.session.add(c)
                coupons_issued.append("BIRTHDAY")

    # 쿠폰까지 포함해서 DB 반영
    db.session.commit()
    return coupons_issued


# =========================
# 4) 메인 화면
# =========================
@app.route("/")
def index():
    # index.html에서 "신규가입", "재방문" 버튼으로 /register, /visit 링크된다고 가정
    return render_template("index.html")


# =========================
# 5) 신규 가입
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        branch = (request.form.get("branch") or "").strip()
        name = (request.form.get("name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        birth = (request.form.get("birth") or "").strip()

        marketing = True if request.form.get("marketing") == "on" else False
        privacy = True if request.form.get("privacy") == "on" else False

        # 필수 항목 체크
        if not branch or not name or not phone:
            error = "지점명, 이름, 전화번호는 필수입니다."
            return render_template("register.html", branch=branch, error=error)

        if not privacy:
            error = "개인정보 수집 동의(필수)를 체크해 주세요."
            return render_template("register.html", branch=branch, error=error)

        # 중복 번호 체크
        existing = Members.query.filter_by(phone=phone).first()
        if existing:
            error = "이미 가입된 번호입니다."
            return render_template("register.html", branch=branch, error=error)

        # 새 회원 생성 (가입 시 방문 1회로 간주)
        new_member = Members(
            branch=branch,
            name=name,
            phone=phone,
            birth=birth,
            marketing=marketing,
            privacy=privacy,
            visit_count=1
        )
        db.session.add(new_member)
        db.session.commit()  # member.id가 필요하므로 한 번 커밋

        # 방문수 0 → 1 로 증가했다고 보고 쿠폰 발급
        coupons = issue_coupons_if_needed(new_member, 0, 1)

        return redirect(url_for("success", name=name, coupons=len(coupons)))

    # GET 요청 (지점별 QR에서 branch가 넘어온다고 가정)
    branch = request.args.get("branch", "")
    return render_template("register.html", branch=branch)


# =========================
# 6) 재방문 적립
# =========================
@app.route("/visit", methods=["GET", "POST"])
def visit():
    if request.method == "POST":
        branch = (request.form.get("branch") or "").strip()
        phone = (request.form.get("phone") or "").strip()

        if not phone:
            error = "전화번호를 입력해 주세요."
            return render_template("visit.html", branch=branch, error=error)

        member = Members.query.filter_by(phone=phone).first()

        if not member:
            error = "등록된 회원이 없습니다. 먼저 신규가입을 진행해 주세요."
            return render_template("visit.html", branch=branch, error=error)

        # 방문 횟수 증가
        visit_before = member.visit_count or 0
        member.visit_count = visit_before + 1

        # 쿠폰 발급
        coupons = issue_coupons_if_needed(member, visit_before, member.visit_count)

        return render_template(
            "visit_success.html",
            member=member,
            coupons=coupons,
            branch=branch
        )

    branch = request.args.get("branch", "")
    return render_template("visit.html", branch=branch)


# =========================
# 7) 가입 완료 페이지
# =========================
@app.route("/success")
def success():
    name = request.args.get("name", "")
    coupons = int(request.args.get("coupons", 0))
    return render_template("success.html", name=name, coupons=coupons)


# =========================
# 8) 관리자 회원 리스트
# =========================
@app.route("/admin/members")
def admin_members():
    sort = request.args.get("sort", "date")

    query = Members.query
    if sort == "name":
        query = query.order_by(Members.name)
    elif sort == "branch":
        query = query.order_by(Members.branch, Members.name)
    else:  # date
        query = query.order_by(Members.join_date.desc())

    members = query.all()
    return render_template("members.html", members=members, sort=sort)


if __name__ == "__main__":
    app.run(debug=True)
