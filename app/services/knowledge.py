from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import KnowledgeItem

async def relevant_knowledge(session: AsyncSession, query: str) -> str:
    terms = [x for x in query.lower().split() if len(x) > 3][:6]
    rows = (await session.scalars(select(KnowledgeItem).where(KnowledgeItem.is_active).limit(30))).all()
    scored=[]
    for row in rows:
        text=(row.title+' '+row.content).lower(); score=sum(1 for t in terms if t in text)
        if score: scored.append((score,row))
    scored.sort(key=lambda x:x[0], reverse=True)
    return '\n\n'.join(f'<b>{r.title}</b>\n{r.content}' for _,r in scored[:5])
