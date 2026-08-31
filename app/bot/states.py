from aiogram.fsm.state import State, StatesGroup

class AIChat(StatesGroup): active = State()
class Voice(StatesGroup): active = State()
class File(StatesGroup): active = State()
class Image(StatesGroup): active = State()
class Vision(StatesGroup): active = State()
class Ticket(StatesGroup): active = State()
class Rating(StatesGroup): comment = State()
class Feedback(StatesGroup): active = State()
class Admin(StatesGroup):
    user_id = State(); broadcast = State(); channel = State(); kb_title = State(); kb_content = State(); learning = State()
