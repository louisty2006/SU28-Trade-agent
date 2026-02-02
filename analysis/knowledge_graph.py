"""
REISHI 霊視 v5.0 - 知识图谱

目的：追踪公司关系，累积式资料库
- 公司资料（供应商、客户、竞争对手）
- 累积式存储
- 自动更新机制
"""

from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import sqlite3
import os


@dataclass
class Relationship:
    name: str
    ticker: Optional[str]
    relationship_type: str
    description: str
    importance: str
    revenue_pct: Optional[float]
    source: str


@dataclass
class CompanyProfile:
    ticker: str
    name: str
    sector: str
    updated: datetime
    confidence: float
    sources: List[str]
    suppliers: List[Relationship]
    customers: List[Relationship]
    competitors: List[str]
    risks: List[str]
    revenue_breakdown: Dict[str, float]


class KnowledgeGraph:
    """
    知识图谱：累积式公司关系资料库
    """
    
    def __init__(self, db_path: str = "data/company_relationships.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                ticker TEXT PRIMARY KEY,
                name TEXT,
                sector TEXT,
                updated TEXT,
                confidence REAL,
                sources TEXT,
                data TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def get_company_profile(self, ticker: str) -> Optional[CompanyProfile]:
        """
        获取公司资料
        
        逻辑：
        1. 检查资料库是否有该公司
        2. 如果有且未过期（< 90 天）→ 直接返回
        3. 如果没有或过期 → 即时查询 → 存入资料库 → 返回
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM companies WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            updated = datetime.fromisoformat(row[3])
            if datetime.now() - updated < timedelta(days=90):
                # 数据仍然有效
                return self._parse_profile(row)
        
        # 需要更新或首次查询
        profile = self.query_relationships(ticker)
        if profile:
            self.save_profile(profile)
        
        return profile
    
    def query_relationships(self, ticker: str) -> Optional[CompanyProfile]:
        """
        即时查询公司关系
        
        三个来源并行：
        1. Web Search
        2. 财报解析
        3. LLM知识
        """
        # MVP: 返回模拟数据
        return CompanyProfile(
            ticker=ticker,
            name=f"{ticker} Inc.",
            sector="Technology",
            updated=datetime.now(),
            confidence=0.7,
            sources=["yahoo"],
            suppliers=[],
            customers=[],
            competitors=[],
            risks=[],
            revenue_breakdown={}
        )
    
    def save_profile(self, profile: CompanyProfile):
        """存入资料库"""
        import json
        
        conn = sqlite3.connect(self.db_path)
        
        conn.execute("""
            INSERT OR REPLACE INTO companies VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            profile.ticker,
            profile.name,
            profile.sector,
            profile.updated.isoformat(),
            profile.confidence,
            json.dumps(profile.sources),
            json.dumps({
                'suppliers': [s.__dict__ for s in profile.suppliers],
                'customers': [c.__dict__ for c in profile.customers],
                'competitors': profile.competitors,
                'risks': profile.risks,
                'revenue_breakdown': profile.revenue_breakdown
            })
        ))
        
        conn.commit()
        conn.close()
    
    def needs_update(self, ticker: str, max_age_days: int = 90) -> bool:
        """检查是否需要更新"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT updated FROM companies WHERE ticker = ?", (ticker,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return True
        
        updated = datetime.fromisoformat(row[0])
        return datetime.now() - updated > timedelta(days=max_age_days)
    
    def _parse_profile(self, row) -> CompanyProfile:
        """从数据库行解析profile"""
        import json
        
        return CompanyProfile(
            ticker=row[0],
            name=row[1],
            sector=row[2],
            updated=datetime.fromisoformat(row[3]),
            confidence=row[4],
            sources=json.loads(row[5]),
            suppliers=[],
            customers=[],
            competitors=[],
            risks=[],
            revenue_breakdown={}
        )
