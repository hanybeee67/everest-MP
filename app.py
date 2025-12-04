from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///members.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -------------------------
# Models
# -------------------------
class Members(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch = db.Column(db.String(50))
    name = db.Column(db.String(50))
    phone = db.Column(db.String(50))
    birth = db.Column(db.String(20))
    marketing = db.Column(db.Boolean, default=False)
    privacy = db.Column(db.Boolean, default=False)
    visit_count = db.Column(db.Integer, default=1)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)

class Receipts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"))
    approval_no = db.Column(db.String(50), unique=True)
    amount = db.Column(db.String(20))
    branch = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------------
# 쿠폰 발급 로직 (이전 버전 그대로)
# -------------------------
def issue_coupons_if_needed(member, old_count, new_count):
    coupons = []
    if (old_count // 3) != (new_count // 3):
        coupons.append("방문 3회 쿠폰")
    return coupons


# -------------------------
# 방문 OCR 라우트
# -------------------------
@app.route("/visit", methods=["GET", "POST"])
def visit():
    if request.method == "POST":
        branch = request.form.get("branch")
        phone = request.form.get("phone")
        file = request.files.get("receipt_image")

        if not file:
            return render_template("visit.html", error="영수증 사진을 업로드해주세요.", branch=branch)

        # 영수증 저장 경로
        os.makedirs("receipt_upload", exist_ok=True)
        filepath = f"receipt_upload/{datetime.now().timestamp()}.jpg"
        file.save(filepath)

        # OCR 실행
        from receipt_ocr import extract_receipt_info
        amount, approval_no, raw_text = extract_receipt_info(filepath)

        if not approval_no:
            return render_template("visit.html", error="영수증에서 승인번호를 찾지 못했습니다.", branch=branch)

        # 승인번호 중복 방지
        existing = Receipts.query.filter_by(approval_no=approval_no).first()
        if existing:
            return render_template("visit.html", error="이미 적립된 영수증입니다.", branch=branch)

        # 회원 조회
        member = Members.query.filter_by(phone=phone).first()
        if not member:
            return render_template("visit.html", error="등록되지 않은 회원입니다.", branch=branch)

        # 방문 횟수 증가
        visit_before = member.visit_count or 0
        member.visit_count = visit_before + 1

        # 영수증 DB 저장
        receipt = Receipts(
            member_id=member.id,
            approval_no=approval_no,
            amount=amount,
            branch=branch
        )
        db.session.add(receipt)

        # 쿠폰 발급
        coupons = issue_coupons_if_needed(member, visit_before, member.visit_count)

        db.session.commit()

        return render_template(
            "visit_success.html",
            member=member,
            coupons=coupons,
            amount=amount,
            approval_no=approval_no
        )

    branch = request.args.get("branch", "")
    return render_template("visit.html", branch=branch)


# -------------------------
# 기본 페이지
# -------------------------
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
