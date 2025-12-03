from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import base64
import os
from google.cloud import vision

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///members.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# ============================
#  DB Models
# ============================
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


# ============================
#  Google Vision OCR
# ============================
def extract_amount_from_receipt(image_bytes):
    """
    Google Vision OCR로 영수증에서 총 금액 숫자를 파싱한다.
    금액을 찾으면 정수로 반환, 못 찾으면 0
    """

    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)

    if response.error.message:
        return 0

    text = response.text_annotations[0].description if response.text_annotations else ""

    # 숫자 형태 추출
    import re
    nums = re.findall(r"[0-9,]+", text)

    if not nums:
        return 0

    # 가장 큰 금액을 총액으로 판단
    values = [int(n.replace(",", "")) for n in nums]
    return max(values)


# ============================
#  쿠폰 발행 로직
# ============================
def issue_coupons_if_needed(member, old_visit_count, old_amount):

    issued = []

    # 1) 첫 방문 고객 라시 무료 쿠폰
    if old_visit_count == 0 and member.visit_count == 1:
        coupon = Coupons(
            member_id=member.id,
            type="FIRST_VISIT_LASSI",
            description="첫 방문 감사 라시 무료 쿠폰"
        )
        db.session.add(coupon)
        issued.append(coupon)

    # 2) 방문 3회 단위 쿠폰
    if member.visit_count // 3 > old_visit_count // 3:
        coupon = Coupons(
            member_id=member.id,
            type="VISIT_3X",
            description=f"{member.visit_count}회 방문 감사 쿠폰"
        )
        db.session.add(coupon)
        issued.append(coupon)

    # 3) 10만 원 누적 단위 쿠폰
    old_step = old_amount // 100000
    new_step = member.spend_amount // 100000
    if new_step > old_step:
        diff = new_step - old_step
        for i in range(diff):
            level = (old_step + i + 1) * 100000
            coupon = Coupons(
                member_id=member.id,
                type="AMOUNT_100K",
                description=f"누적 {level:,}원 달성 감사 쿠폰"
            )
            db.session.add(coupon)
            issued.append(coupon)

    return issued


# ============================
#  OCR 업로드 라우트
# ============================
@app.route("/ocr_upload", methods=["POST"])
def ocr_upload():
    file = request.files.get("receipt")
    if not file:
        return jsonify({"amount": 0})

    image_bytes = file.read()
    amount = extract_amount_from_receipt(image_bytes)

    return jsonify({"amount": amount})


# ============================
#  REGISTER
# ============================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method
