from aiogram.fsm.state import State, StatesGroup

class OrderForm(StatesGroup):
    name = State()
    phone = State()
    address = State()

class AddCategory(StatesGroup):
    title = State()

class AddItem(StatesGroup):
    category_id = State()
    authenticity = State()  
    title = State()
    description = State()
    brand = State()
    size = State()
    price = State()
    photo = State()
    tags_photo = State()

class EditItem(StatesGroup):
    price = State()

class Broadcast(StatesGroup):
    message = State()

class UserProfile(StatesGroup):
    country = State()
    city = State()
    full_name = State()
    phone = State()

class AdminUserSearch(StatesGroup):
    waiting_for_user_input = State()

class RegistrationStates(StatesGroup):
    waiting_for_invite = State()


class AddSniper(StatesGroup):
    link = State()

class GiveVip(StatesGroup):
    tg_id = State()
    days = State()


class SupportFSM(StatesGroup):
    waiting_for_user_issue = State()
    waiting_for_admin_reply = State()


class GlobalParser(StatesGroup):
    select_platform = State()
    enter_query = State()
    select_category = State()

class AddFilter(StatesGroup):
    waiting_for_url = State()        
    waiting_for_brand = State()     
    waiting_for_size = State()       
    waiting_for_condition = State()  
    waiting_for_price = State()


class AddReview(StatesGroup):
    waiting_for_comment = State()


class CurrencyCalcState(StatesGroup):
    waiting_for_currency = State()
    waiting_for_price = State()
    waiting_for_weight = State()


class AddWTB(StatesGroup):
    waiting_for_title = State()
    waiting_for_size = State()
    waiting_for_budget = State()


class LegitCheck(StatesGroup):
    waiting_for_clg = State()
    waiting_for_brand = State()


class Evaluator(StatesGroup):
    waiting_for_query = State()