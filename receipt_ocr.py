from paddleocr import PaddleOCR
import re

# PaddleOCR 한국어 모델 초기화
ocr = PaddleOCR(lang='korean')

def extract_receipt_info(image_path):
    """
    영수증 이미지에서 승인금액 / 승인번호 추출
    """

    # OCR 수행
    result = ocr.ocr(image_path, cls=True)

    # 결과 텍스트 전체 합치기
    text = "\n".join([line[1][0] for block in result for line in block])

    # 승인금액 찾기 (예: 718,500)
    amount_match = re.search(r"승인금액\s*[: ]\s*([0-9,]+)", text)
    amount = amount_match.group(1) if amount_match else None

    # 승인번호 찾기 (예: 15178907)
    approval_match = re.search(r"승인번호\s*[: ]\s*([0-9]+)", text)
    approval_no = approval_match.group(1) if approval_match else None

    return amount
