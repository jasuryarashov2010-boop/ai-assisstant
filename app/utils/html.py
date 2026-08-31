from aiogram import html

def esc(value: str) -> str: return html.quote(str(value))

def bar(value:int, total:int, width:int=10)->str:
    if total<=0: return '░'*width
    filled=min(width, round(value/total*width)); return '█'*filled + '░'*(width-filled)
