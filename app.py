"""
DART(전자공시시스템) Open API를 감싸는 원격 MCP 서버

제공 기능
1. search_disclosures : 기간/유형별 공시 목록 검색 (증권신고서 등)
2. get_document_text  : 특정 공시(rcept_no)의 원문 텍스트 조회 (증권신고서 본문 등)
3. find_corp_code      : 회사명으로 DART 고유번호(corp_code) 조회
4. get_financial_statement : 단일회사 재무제표 조회

환경변수
- DART_API_KEY : DART Open API 인증키 (40자리)

배포 방법 (Replit 기준)
1. Replit에서 Python Repl 생성 후 이 파일을 app.py 로 저장
2. requirements.txt 도 함께 저장 후 Shell에서 `pip install -r requirements.txt`
3. Replit Secrets에 DART_API_KEY 값 등록
4. Run 클릭 -> Replit이 공개 URL을 발급 (예: https://xxxx.replit.app)
5. Claude 앱 > Customize > Connectors > Add custom connector 에 그 URL + "/mcp" 경로를 붙여 등록
   (Streamable HTTP transport 사용, 엔드포인트는 보통 서버 루트 또는 /mcp)
"""

import os
import re
import io
import zipfile
from typing import Optional

import requests
from mcp.server.fastmcp import FastMCP

DART_API_KEY = os.environ.get("DART_API_KEY", "")
BASE_URL = "https://opendart.fss.or.kr/api"

mcp = FastMCP("dart-mcp")

# corp_code 조회용 캐시 (최초 1회만 전체 다운로드)
_corp_code_cache: Optional[list] = None


def _require_key():
    if not DART_API_KEY:
        raise RuntimeError(
            "DART_API_KEY 환경변수가 설정되어 있지 않습니다. "
            "Replit Secrets에 DART_API_KEY를 등록해주세요."
        )


def _load_corp_codes():
    """DART 전체 기업 고유번호 목록을 다운로드해서 메모리에 캐싱합니다."""
    global _corp_code_cache
    if _corp_code_cache is not None:
        return _corp_code_cache

    _require_key()
    resp = requests.get(
        f"{BASE_URL}/corpCode.xml",
        params={"crtfc_key": DART_API_KEY},
        timeout=60,
    )
    resp.raise_for_status()

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    xml_name = next(n for n in zf.namelist() if n.endswith(".xml"))
    xml_text = zf.read(xml_name).decode("utf-8")

    # 간단한 정규식 파싱 (외부 xml 파서 의존성을 줄이기 위함)
    entries = []
    for block in re.findall(r"<list>(.*?)</list>", xml_text, flags=re.S):
        def _field(tag):
            m = re.search(fr"<{tag}>(.*?)</{tag}>", block, flags=re.S)
            return m.group(1).strip() if m else ""

        entries.append(
            {
                "corp_code": _field("corp_code"),
                "corp_name": _field("corp_name"),
                "stock_code": _field("stock_code"),
                "modify_date": _field("modify_date"),
            }
        )

    _corp_code_cache = entries
    return entries


@mcp.tool()
def find_corp_code(corp_name: str) -> list:
    """
    회사명(부분 일치)으로 DART 고유번호(corp_code)를 검색합니다.
    상장사는 stock_code(종목코드)도 함께 반환됩니다.
    다른 도구(get_financial_statement 등)에서 사용할 corp_code를 찾을 때 먼저 호출하세요.
    """
    entries = _load_corp_codes()
    name = corp_name.strip()
    matches = [e for e in entries if name in e["corp_name"]]
    return matches[:20]


@mcp.tool()
def search_disclosures(
    bgn_de: str,
    end_de: str,
    corp_name: Optional[str] = None,
    pblntf_ty: Optional[str] = None,
    corp_cls: Optional[str] = "K",
    page_no: int = 1,
    page_count: int = 100,
) -> dict:
    """
    DART 공시 목록을 검색합니다.

    Args:
        bgn_de: 검색 시작일 (YYYYMMDD)
        end_de: 검색 종료일 (YYYYMMDD)
        corp_name: 회사명으로 먼저 필터링하고 싶을 때 (선택, find_corp_code로 corp_code를 찾아 내부적으로 사용)
        pblntf_ty: 공시유형 코드 (선택). 예: A=정기공시, B=주요사항보고, C=발행공시(증권신고서 포함), D=지분공시 등
        corp_cls: Y=유가증권 K=코스닥 N=코넥스 E=기타 (기본값 K, 코스닥)
        page_no: 페이지 번호 (기본 1)
        page_count: 페이지당 건수 (최대 100)

    Returns:
        DART API 원본 응답(dict). list 필드에 공시 목록, 각 항목에 rcept_no(접수번호)가 포함됨.
        rcept_no는 get_document_text 호출 시 사용합니다.
    """
    _require_key()
    corp_code = None
    if corp_name:
        matches = find_corp_code(corp_name)
        if matches:
            corp_code = matches[0]["corp_code"]

    params = {
        "crtfc_key": DART_API_KEY,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "page_no": page_no,
        "page_count": page_count,
    }
    if corp_code:
        params["corp_code"] = corp_code
    if pblntf_ty:
        params["pblntf_ty"] = pblntf_ty
    if corp_cls:
        params["corp_cls"] = corp_cls

    resp = requests.get(f"{BASE_URL}/list.json", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def get_document_text(rcept_no: str, max_chars: int = 30000) -> str:
    """
    특정 공시(접수번호 rcept_no)의 원문을 텍스트로 반환합니다.
    증권신고서, 투자설명서 등 원문 안의 피어그룹/밸류에이션 배수/위험요소 등을
    직접 확인하고 싶을 때 사용하세요.

    Args:
        rcept_no: search_disclosures 결과의 rcept_no (접수번호, 14자리)
        max_chars: 반환할 최대 문자 수 (원문이 매우 길 수 있어 기본 30000자로 제한)

    Returns:
        HTML/XML 태그를 제거한 원문 텍스트 (앞부분부터 max_chars 만큼)
    """
    _require_key()
    resp = requests.get(
        f"{BASE_URL}/document.xml",
        params={"crtfc_key": DART_API_KEY, "rcept_no": rcept_no},
        timeout=60,
    )
    resp.raise_for_status()

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    texts = []
    for name in zf.namelist():
        raw = zf.read(name).decode("utf-8", errors="ignore")
        # 태그 제거 (간단한 방식 - 표/서식은 소실되지만 본문 텍스트는 유지됨)
        clean = re.sub(r"<[^>]+>", " ", raw)
        clean = re.sub(r"&[a-zA-Z]+;", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        texts.append(f"--- {name} ---\n{clean}")

    full_text = "\n\n".join(texts)
    return full_text[:max_chars]


@mcp.tool()
def get_financial_statement(
    corp_code: str, bsns_year: str, reprt_code: str = "11011"
) -> dict:
    """
    단일회사 전체 재무제표를 조회합니다.

    Args:
        corp_code: DART 고유번호 (find_corp_code로 조회)
        bsns_year: 사업연도 (YYYY)
        reprt_code: 11013=1분기, 11012=반기, 11014=3분기, 11011=사업보고서(연간, 기본값)

    Returns:
        DART API 원본 응답(dict). list 필드에 계정과목별 재무 수치가 담김.
    """
    _require_key()
    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": "CFS",  # 연결재무제표 기준 (개별은 OFS)
    }
    resp = requests.get(f"{BASE_URL}/fnlttSinglAcnt.json", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Replit 등 원격 호스팅 환경을 위해 streamable-http transport 사용
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
