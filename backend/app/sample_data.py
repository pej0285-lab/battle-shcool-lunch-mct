from __future__ import annotations

from .models import School


SAMPLE_SCHOOLS: tuple[School, ...] = (
    School(office_code="B10", office_name="서울특별시교육청", school_code="7010057", school_name="서울고등학교", region="서울", kind="고등학교"),
    School(office_code="B10", office_name="서울특별시교육청", school_code="7010117", school_name="경기고등학교", region="서울", kind="고등학교"),
    School(office_code="J10", office_name="경기도교육청", school_code="7530086", school_name="분당고등학교", region="경기", kind="고등학교"),
    School(office_code="J10", office_name="경기도교육청", school_code="7530180", school_name="수내고등학교", region="경기", kind="고등학교"),
    School(office_code="C10", office_name="부산광역시교육청", school_code="7150038", school_name="부산고등학교", region="부산", kind="고등학교"),
    School(office_code="D10", office_name="대구광역시교육청", school_code="7240052", school_name="경북고등학교", region="대구", kind="고등학교"),
    School(office_code="E10", office_name="인천광역시교육청", school_code="7310058", school_name="인천고등학교", region="인천", kind="고등학교"),
    School(office_code="F10", office_name="광주광역시교육청", school_code="7380292", school_name="광주제일고등학교", region="광주", kind="고등학교"),
    School(office_code="G10", office_name="대전광역시교육청", school_code="7430058", school_name="대전고등학교", region="대전", kind="고등학교"),
    School(office_code="H10", office_name="울산광역시교육청", school_code="7480054", school_name="울산고등학교", region="울산", kind="고등학교"),
    School(office_code="M10", office_name="충청북도교육청", school_code="8000091", school_name="청주고등학교", region="충북", kind="고등학교"),
    School(office_code="N10", office_name="충청남도교육청", school_code="8140045", school_name="공주고등학교", region="충남", kind="고등학교"),
)
