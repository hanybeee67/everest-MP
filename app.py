from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import re

# OCR 기능을 활성화하려면 Google Vision 패키지 설치 및 KEY 설정 필요.
# from google.cloud import vision

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///members.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# ======================================================
# Database Models
# ======================================================
class Members(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch = db.Column(db.String(50))
    name = db.Column(db.String(50))
    phone = db.Column(db.String(50), unique=True)
    birth = db.Column(db.String(20))
    visit_count = db.Column(db.Integer, default=1)
    spend_amount = db.Column(db.Integer, default=0)
    marketing = db.Column(db.Boolean, default=False)
    privacy = db.Column(db.Boolean, default=False)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)


class Coupons(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    type = db.Column(db.String(50))
    description = db.Column(db.String(200))
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    used = db.Column(db.Boolean, default=False)

    member = db.relationship("Members", backref=db.backref("coupons", lazy=True))


# ======================================================
# OCR (현재는 금액만 정규표현식으로 임시 추출)
# ======================================================
def extract_amount_from_receipt(image_bytes):
    # 실제 OCR 연동 전 기본 동작(금액 못 읽으면 0)
    return 0


# ======================================================
# 쿠폰 자동 발행 로직
# ======================================================
def issue_coupons_if_needed(member, old_visit_count, old_amount):
    issued = []

    # 1) 첫 방문 라시 무료 쿠폰
    if old_visit_count == 0 and member.visit_count == 1:
        c = Coupons(
            member_id=member.id,
            type="FIRST_VISIT_LASSI",
            description="첫 방문 감사 라시 무료 쿠폰"
        )
        db.session.add(c)
        issued.append(c)

    # 2) 방문 3회마다 쿠폰
    if (member.visit_count // 3) > (old_visit_count // 3):
        c = Coupons(
            member_id=member.id,
            type="VISIT_3X",
            description=f"{member.visit_count}회 방문 감사 쿠폰"
        )
        db.session.add(c)
        issued.append(c)

    # 3) 누적 결제 금액 10만 원 단위 쿠폰
    old_step = old_amount // 100000
    new_step = member.spend_amount // 100000

    if new_step > old_step:
        diff = new_step - old_step
        for i in range(diff):
            level = (old_step + i + 1) * 100000
            c = Coupons(
                member_id=member.id,
                type="AMOUNT_100K",
                description=f"누적 {level:,}원 달성 감사 쿠폰"
            )
            db.session.add(c)
            issued.append(c)

    return issued


# ======================================================
# OCR 업로드 라우트
# ======================================================
@app.route("/ocr_upload", methods=["POST"])
def ocr_upload():
    file = request.files.get("receipt")
    if not file:
        return jsonify({"amount": 0})

    image_bytes = file.read()
    amount = extract_amount_from_receipt(image_bytes)

    return jsonify({"amount": amount})


# ======================================================
# Index
# ======================================================
@app.route("/")
def index():
    return render_template("index.html")


# ======================================================
# Register (신규가입)
# ======================================================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        branch = request.form.get("branch")
        name = request.form.get("name")
        phone = request.form.get("phone")
        birth = request.form.get("birth")
        marketing = True if request.form.get("marketing") == "on" else False
        privacy = True if request.form.get("privacy") == "on" else False

        existing = Members.query.filter_by(phone=phone).first()
        if existing:
            error = "이미 가입된 번호입니다."
            return render_template("register.html", branch=branch, error=error)

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
        db.session.commit()

        coupons = issue_coupons_if_needed(new_member, 0, 0)
        db.session.commit()

        return redirect(url_for("success", name=name, coupons=len(coupons)))

    branch = request.args.get("branch", "")
    return render_template("register.html", branch=branch)


# ======================================================
# Visit (재방문 적립)
# ======================================================
@app.route("/visit", methods=["GET", "POST"])
def visit():
    if request.method == "POST":
        phone = request.form.get("phone")
        spend_raw = request.form.get("spend_amount", "0").replace(",", "")

        try:
            spend_amount = int(spend_raw)
        except:
            spend_amount = 0

        member = Members.query.filter_by(phone=phone).first()
        if not member:
            return render_template("visit.html", error="등록되지 않은 번호입니다.")

        old_visit = member.visit_count
        old_amount = member.spend_amount

        member.visit_count += 1
        member.spend_amount += spend_amount

        db.session.flush()

        coupons = issue_coupons_if_needed(member, old_visit, old_amount)
        db.session.commit()

        return redirect(url_for("success", name=member.name, coupons=len(coupons)))

    branch = request.args.get("branch", "")
    return render_template("visit.html", branch=branch)


# ======================================================
# Success Page
# ======================================================
@app.route("/success")
def success():
    name = request.args.get("name")
    coupons = request.args.get("coupons", 0)
    try:
        coupons = int(coupons)
    except:
        coupons = 0

    return render_template("success.html", name=name, coupons=coupons)


# ======================================================
# Admin - Members
# ======================================================
@app.route("/admin/members")
def admin_members():
    sort = request.args.get("sort", "id")

    if sort == "name":
        members = Members.query.order_by(Members.name.asc()).all()
    elif sort == "branch":
        members = Members.query.order_by(Members.branch.asc()).all()
    elif sort == "visit":
        members = Members.query.order_by(Members.visit_count.desc()).all()
    elif sort == "amount":
        members = Members.query.order_by(Members.spend_amount.desc()).all()
    elif sort == "date":
        members = Members.query.order_by(Members.join_date.desc()).all()
    else:
        members = Members.query.order_by(Members.id.desc()).all()

    return render_template("members.html", members=members)


# ======================================================
# Admin - Coupons
# ======================================================
@app.route("/admin/coupons")
def admin_coupons():
    coupons = Coupons.query.order_by(Coupons.issued_at.desc()).all()
    return render_template("coupons.html", coupons=coupons)


# ======================================================
# Run App
# ======================================================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
