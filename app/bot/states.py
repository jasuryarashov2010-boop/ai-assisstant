from aiogram.fsm.state import State, StatesGroup
class AIChat(StatesGroup): text=State()
class Voice(StatesGroup): voice=State()
class File(StatesGroup): file=State()
class Image(StatesGroup): prompt=State()
class Vision(StatesGroup): photo=State()
class Ticket(StatesGroup): message=State()
class Rating(StatesGroup): comment=State()
class Feedback(StatesGroup): text=State()
class Admin(StatesGroup):
    user_id=State(); broadcast=State(); channel=State(); kb_title=State(); kb_content=State(); learning=State()
