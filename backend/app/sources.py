from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    category: str
    region: str
    url: str
    trust_level: str
    enabled_default: bool = True


TRUSTED_SOURCES: list[Source] = [
    Source("cninfo", "巨潮资讯", "announcement", "CN", "https://www.cninfo.com.cn/new/index", "official"),
    Source("sse", "上交所上市公司公告", "announcement", "CN", "https://www.sse.com.cn/disclosure/listedinfo/announcement/", "official"),
    Source("szse", "深交所上市公司公告", "announcement", "CN", "https://www.szse.cn/disclosure/listed/notice/index.html", "official"),
    Source("bse", "北交所公告", "announcement", "CN", "https://www.bse.cn/disclosure/announcement.html", "official"),
    Source("hkexnews", "HKEXnews", "announcement", "HK", "https://www.hkexnews.hk/index.htm", "official"),
    Source("sec_edgar", "SEC EDGAR", "filing", "US", "https://data.sec.gov/submissions/CIK0000320193.json", "official"),
    Source("pbc", "中国人民银行", "policy", "CN", "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/index.html", "official"),
    Source("csrc", "中国证监会", "policy", "CN", "http://www.csrc.gov.cn/csrc/c100028/common_list.shtml", "official"),
    Source("state_council", "中国政府网政策", "policy", "CN", "https://www.gov.cn/zhengce/index.htm", "official"),
    Source("fed", "Federal Reserve", "policy", "US", "https://www.federalreserve.gov/feeds/press_all.xml", "official"),
    Source("ecb", "European Central Bank", "policy", "EU", "https://www.ecb.europa.eu/rss/press.html", "official"),
    Source("imf", "IMF News", "macro", "GLOBAL", "https://www.imf.org/en/News", "official"),
]


DEFAULT_THEMES = [
    {"name": "AI", "keywords": ["人工智能", "AI", "算力", "大模型", "芯片", "数据中心"]},
    {"name": "新能源", "keywords": ["新能源", "光伏", "风电", "储能", "锂电", "电动车"]},
    {"name": "半导体", "keywords": ["半导体", "芯片", "晶圆", "封测", "光刻", "存储"]},
    {"name": "医药", "keywords": ["医药", "创新药", "医疗器械", "集采", "临床", "疫苗"]},
    {"name": "军工", "keywords": ["军工", "航空", "航天", "国防", "无人机", "船舶"]},
    {"name": "消费", "keywords": ["消费", "零售", "白酒", "食品饮料", "旅游", "家电"]},
]
