import os
import logging
import sqlite3
import datetime
from enum import Enum
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext, ConversationHandler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Channel ID for scheduled appointments
CHANNEL_USERNAME = "@barberuzpro"

# States for the conversation
(
    MAIN_MENU,
    SELECTING_SERVICE,
    CHOOSING_DATE,
    CHOOSING_TIME,
    CONFIRMING_APPOINTMENT,
    CONTACT_INFO,
    ADMIN_PANEL,
    ADMIN_VIEW_APPOINTMENTS,
    ADMIN_VIEW_CLIENTS,
    HANDLING_EXISTING_APPOINTMENT,
) = range(10)

# Service types as provided
class ServiceType(Enum):
    HaircutforElder = "Soch olish kattalar uchun"
    HaircutforChildren = "Soch olish bolalar uchun"
    HairStraightening = "Kantovka to'g'rilash"
    BeardTrim = "Soqol olish"
    HairWash = "Bosh yuvish"
    Combo = "Combo (soch olish + soqol olish + yuz chistkasi)"
    HairColoring = "Soch bo'yash"
    BeardColoring = "Soqol bo'yash"
    FaceMask = "Yuz niqobi"
    HairCurling = "Soch jingalak qilish"
    HairBalding = "Sochni kalga oldirish"
    HairStylingforBridgeGroom = "Soch olish (to'y uchun)"

# Service prices
SERVICE_PRICES = {
    ServiceType.HaircutforElder: 40000,
    ServiceType.HaircutforChildren: 30000,
    ServiceType.HairStraightening: 25000,
    ServiceType.BeardTrim: 25000,
    ServiceType.HairWash: 25000,
    ServiceType.Combo: 80000,
    ServiceType.HairColoring: 35000,
    ServiceType.BeardColoring: 35000,
    ServiceType.FaceMask: 25000,
    ServiceType.HairCurling: 30000,
    ServiceType.HairBalding: 20000,
    ServiceType.HairStylingforBridgeGroom: 300000,
}

# Working hours
WORKING_HOURS = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]

# Admin user IDs (replace with actual admin Telegram IDs)
ADMIN_IDS = [123456789]  # Add your admin Telegram IDs here

# Database setup
def setup_database():
    conn = sqlite3.connect('barber_shop.db')
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        phone_number TEXT,
        registration_date TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        service TEXT,
        price INTEGER,
        date TEXT,
        time TEXT,
        status TEXT DEFAULT 'scheduled',
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Start command handler
def start(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    user_id = user.id
    
    # Store user data in the database
    conn = sqlite3.connect('barber_shop.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO users (user_id, username, first_name, last_name, registration_date) VALUES (?, ?, ?, ?, ?)",
            (user_id, user.username, user.first_name, user.last_name, now)
        )
        conn.commit()
    
    conn.close()
    
    # Check if user is admin
    if user_id in ADMIN_IDS:
        keyboard = [
            [KeyboardButton("📅 Yangi buyurtma berish")],
            [KeyboardButton("🔍 Mening buyurtmalarim")],
            [KeyboardButton("👤 Admin panel")]
        ]
    else:
        keyboard = [
            [KeyboardButton("📅 Yangi buyurtma berish")],
            [KeyboardButton("🔍 Mening buyurtmalarim")],
            [KeyboardButton("📞 Aloqa")]
        ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    update.message.reply_text(
        f"Assalomu alaykum, {user.first_name}! 💈\n\n"
        "Sartaroshxonamizning telegram botiga xush kelibsiz!\n"
        "Soch olish, soqol olish va boshqa xizmatlar uchun qulaylik bilan buyurtma berishingiz mumkin.",
        reply_markup=reply_markup
    )
    
    return MAIN_MENU

# Main menu handler
def main_menu(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    
    if text == "📅 Yangi buyurtma berish":
        return start_booking(update, context)
    elif text == "🔍 Mening buyurtmalarim":
        return view_my_appointments(update, context)
    elif text == "📞 Aloqa":
        update.message.reply_text(
            "Bizning ma'lumotlar:\n\n"
            "📱 Telefon: +998 91 551 10 15\n"
            "📍 Manzil: Samarqand, o'rdashev ko'chasi, 56\n"
            "⏰ Ish vaqti: 09:00 - 21:00\n\n"
            "Savollaringiz bo'lsa, iltimos bog'laning!"
        )
        return MAIN_MENU
    elif text == "👤 Admin panel" and update.effective_user.id in ADMIN_IDS:
        return admin_panel(update, context)
    
    update.message.reply_text("Iltimos, quyidagi menuni tanlang")
    return MAIN_MENU

# Start booking process
def start_booking(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    
    # Check if user already has an active appointment
    conn = sqlite3.connect('barber_shop.db')
    cursor = conn.cursor()
    
    # Get current date in the format used in the database
    current_date = datetime.datetime.now().strftime("%d.%m.%Y")
    
    cursor.execute(
        """
        SELECT id, service, date, time 
        FROM appointments 
        WHERE user_id = ? AND status = 'scheduled' AND date >= ?
        ORDER BY date, time
        LIMIT 1
        """,
        (user_id, current_date)
    )
    
    existing_appointment = cursor.fetchone()
    conn.close()
    
    if existing_appointment:
        # User has an existing appointment, ask if they want to make a new one or edit existing
        appt_id, service, date, time = existing_appointment
        
        keyboard = [
            [InlineKeyboardButton("📝 Yangi buyurtma berish", callback_data="new_appointment")],
            [InlineKeyboardButton("✏️ Mavjud buyurtmani tahrirlash", callback_data=f"edit_appointment_{appt_id}")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"Sizda allaqachon buyurtma mavjud:\n\n"
            f"🧔 Xizmat: {service}\n"
            f"📅 Sana: {date}\n"
            f"🕒 Vaqt: {time}\n\n"
            f"Nima qilishni istaysiz?",
            reply_markup=reply_markup
        )
        
        return HANDLING_EXISTING_APPOINTMENT
    
    # No existing appointment, continue with service selection
    keyboard = []
    row = []
    
    # Create buttons for services
    for i, service in enumerate(ServiceType):
        if i % 2 == 0 and i > 0:  # 2 services per row
            keyboard.append(row)
            row = []
        
        # Format: Service name - Price
        button_text = f"{service.value} - {SERVICE_PRICES[service]:,} so'm"
        row.append(InlineKeyboardButton(button_text, callback_data=f"service_{service.name}"))
    
    if row:  # Add the last row if it exists
        keyboard.append(row)
        
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "Xizmat turini tanlang:",
        reply_markup=reply_markup
    )
    
    return SELECTING_SERVICE

# Handle service selection
def select_service(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    if query.data == "back_to_main":
        query.message.delete()
        keyboard = [
            [KeyboardButton("📅 Yangi buyurtma berish")],
            [KeyboardButton("🔍 Mening buyurtmalarim")],
            [KeyboardButton("📞 Aloqa")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        query.message.reply_text("Asosiy menyu:", reply_markup=reply_markup)
        return MAIN_MENU
    
    service_name = query.data.replace("service_", "")
    service = ServiceType[service_name]
    
    # Save selected service in user_data
    context.user_data['selected_service'] = service
    context.user_data['service_price'] = SERVICE_PRICES[service]
    
    # Generate calendar for date selection
    today = datetime.datetime.now()
    keyboard = []
    
    # Generate 7 days from today
    for i in range(7):
        current_date = today + datetime.timedelta(days=i)
        date_str = current_date.strftime("%d.%m.%Y")
        day_name = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"][current_date.weekday()]
        button_text = f"{date_str} ({day_name})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"date_{date_str}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_services")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        f"Siz tanladingiz: {service.value} - {SERVICE_PRICES[service]:,} so'm\n\n"
        "Endi sana tanlang:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_DATE

# Handle date selection
def choose_date(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    if query.data == "back_to_services":
        return start_booking(update, context)
    
    selected_date = query.data.replace("date_", "")
    context.user_data['selected_date'] = selected_date
    
    # Get available time slots
    conn = sqlite3.connect('barber_shop.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT time FROM appointments WHERE date = ? AND status = 'scheduled'",
        (selected_date,)
    )
    
    booked_times = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Create time selection keyboard
    keyboard = []
    row = []
    
    for i, time in enumerate(WORKING_HOURS):
        if i % 3 == 0 and i > 0:  # 3 time slots per row
            keyboard.append(row)
            row = []
        
        # Check if time slot is available
        if time in booked_times:
            button = InlineKeyboardButton(f"❌ {time}", callback_data=f"unavailable")
        else:
            button = InlineKeyboardButton(f"✅ {time}", callback_data=f"time_{time}")
        
        row.append(button)
    
    if row:  # Add the last row if it exists
        keyboard.append(row)
        
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_dates")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(
        f"Tanlangan sana: {selected_date}\n\n"
        "Endi vaqtni tanlang:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_TIME

# Handle time selection and unavailable slots
def choose_time(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    if query.data == "back_to_dates":
        # Go back to date selection
        service = context.user_data['selected_service']
        
        # Generate calendar for date selection
        today = datetime.datetime.now()
        keyboard = []
        
        # Generate 7 days from today
        for i in range(7):
            current_date = today + datetime.timedelta(days=i)
            date_str = current_date.strftime("%d.%m.%Y")
            day_name = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"][current_date.weekday()]
            button_text = f"{date_str} ({day_name})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"date_{date_str}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_services")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            f"Siz tanladingiz: {service.value} - {SERVICE_PRICES[service]:,} so'm\n\n"
            "Endi sana tanlang:",
            reply_markup=reply_markup
        )
        
        return CHOOSING_DATE
    
    if query.data == "unavailable":
        query.answer("Bu vaqt band!", show_alert=True)
        return CHOOSING_TIME
    
    selected_time = query.data.replace("time_", "")
    context.user_data['selected_time'] = selected_time
    
    # Confirmation keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ Tasdiqlash", callback_data="confirm"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    service = context.user_data['selected_service']
    date = context.user_data['selected_date']
    time = context.user_data['selected_time']
    price = context.user_data['service_price']
    
    query.edit_message_text(
        "📋 Buyurtma ma'lumotlari:\n\n"
        f"🧔 Xizmat: {service.value}\n"
        f"📅 Sana: {date}\n"
        f"🕒 Vaqt: {time}\n"
        f"💰 Narxi: {price:,} so'm\n\n"
        "Tasdiqlaysizmi?",
        reply_markup=reply_markup
    )
    
    return CONFIRMING_APPOINTMENT

# Handle appointment confirmation
def confirm_appointment(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    if query.data == "cancel":
        query.edit_message_text("Buyurtma bekor qilindi. Yangi buyurtma berish uchun asosiy menyudan foydalaning.")
        return ConversationHandler.END
    
    user = update.effective_user
    user_id = user.id
    
    # Check if we have user's phone number
    conn = sqlite3.connect('barber_shop.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT phone_number FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if not user_data or not user_data[0]:
        # Need to get phone number
        keyboard = [[KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        query.edit_message_text("Buyurtmani yakunlash uchun telefon raqamingizni yuboring.")
        query.message.reply_text(
            "Pastdagi tugmani bosing yoki raqamingizni o'zingiz yuboring.\n"
            "Format: +998XXXXXXXXX",
            reply_markup=reply_markup
        )
        
        return CONTACT_INFO
    
    # If we already have the phone number, create the appointment
    return save_appointment(update, context)

# Handle contact information
def contact_info(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    
    # Check if we received contact or text message
    if update.message.contact:
        phone_number = update.message.contact.phone_number
    else:
        phone_number = update.message.text.strip()
        
        # Basic validation for phone number
        if not (phone_number.startswith("+") and len(phone_number) >= 12):
            update.message.reply_text(
                "Noto'g'ri format. Iltimos, raqamingizni +998XXXXXXXXX formatida yuboring yoki tugmani bosing.",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
            return CONTACT_INFO
    
    # Save phone number to database
    conn = sqlite3.connect('barber_shop.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE users SET phone_number = ? WHERE user_id = ?",
        (phone_number, user_id)
    )
    
    conn.commit()
    conn.close()
    
    # Continue to save appointment
    return save_appointment(update, context)

# Save appointment to database
def save_appointment(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    service = context.user_data['selected_service']
    date = context.user_data['selected_date']
    time = context.user_data['selected_time']
    price = context.user_data['service_price']
    
    conn = sqlite3.connect('barber_shop.db')
    cursor = conn.cursor()
    
    # Save the appointment
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO appointments (user_id, service, price, date, time, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, service.value, price, date, time, "scheduled", now)
    )
    
    conn.commit()
    appointment_id = cursor.lastrowid
    
    # Get user info for the notification
    cursor.execute("SELECT first_name, last_name, phone_number FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    first_name, last_name, phone_number = user_data if user_data else ("", "", "")
    full_name = f"{first_name} {last_name}" if last_name else first_name
    
    conn.close()
    
    # Send confirmation message
    keyboard = [
        [KeyboardButton("📅 Yangi buyurtma berish")],
        [KeyboardButton("🔍 Mening buyurtmalarim")],
        [KeyboardButton("📞 Aloqa")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    confirmation_text = (
        "✅ Buyurtmangiz muvaffaqiyatli saqlandi!\n\n"
        f"🆔 Buyurtma raqami: #{appointment_id}\n"
        f"🧔 Xizmat: {service.value}\n"
        f"📅 Sana: {date}\n"
        f"🕒 Vaqt: {time}\n"
        f"💰 Narxi: {price:,} so'm\n\n"
        "Bizni tanlaganingiz uchun rahmat! Belgilangan vaqtda kutib qolamiz."
    )
    
    # Handle different update types (callback query or message)
    if update.callback_query:
        update.callback_query.edit_message_text(confirmation_text)
        update.callback_query.message.reply_text("Asosiy menyu:", reply_markup=reply_markup)
    else:
        update.message.reply_text(confirmation_text, reply_markup=reply_markup)
    
    # Send appointment to channel
    try:
        channel_text = (
            "🔔 YANGI BUYURTMA:\n\n"
            f"👤 Mijoz: {full_name}\n"
            f"📱 Telefon: {phone_number if phone_number else 'Telefon raqam yo\'q'}\n"
            f"🧔 Xizmat: {service.value}\n"
            f"📅 Sana: {date}\n"
            f"🕒 Vaqt: {time}\n"
            f"💰 Narxi: {price:,} so'm"
        )
        context.bot.send_message(chat_id=CHANNEL_USERNAME, text=channel_text)
    except Exception as e:
        logger.error(f"Failed to send message to channel: {e}")
    
    # Notify admins about the new appointment
    for admin_id in ADMIN_IDS:
        try:
            admin_text = (
                "📣 YANGI BUYURTMA!\n\n"
                f"🆔 Buyurtma raqami: #{appointment_id}\n"
                f"👤 Mijoz: {update.effective_user.first_name} {update.effective_user.last_name or ''}\n"
                f"🧔 Xizmat: {service.value}\n"
                f"📅 Sana: {date}\n"
                f"🕒 Vaqt: {time}\n"
                f"💰 Narxi: {price:,} so'm"
            )
            context.bot.send_message(chat_id=admin_id, text=admin_text)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    # Clear user data
    context.user_data.clear()
    
    return ConversationHandler.END

# View user's appointments
def view_my_appointments(update: Update, context: CallbackContext) -> int:
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('barber_shop.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, service, date, time, status, price FROM appointments "
        "WHERE user_id = ? ORDER BY date DESC, time DESC LIMIT 10",
        (user_id,)
    )
    
    appointments = cursor.fetchall()
    conn.close()
    
    if not appointments:
        update.message.reply_text(
            "Sizda hali buyurtmalar yo'q. Yangi buyurtma berish uchun asosiy menyudan foydalaning."
        )
        return MAIN_MENU
    
    reply_text = "🗓 Sizning buyurtmalaringiz:\n\n"
    
    for appointment in appointments:
        appt_id, service, date, time, status, price = appointment
        
        status_emoji = "✅" if status == "scheduled" else "❌"
        status_text = "Rejalashtirilgan" if status == "scheduled" else "Bekor qilingan"
        
        reply_text += (
            f"🆔 #{appt_id}\n"
            f"🧔 {service}\n"
            f"📅 {date}, {time}\n"
            f"💰 {price:,} so'm\n"
            f"{status_emoji} {status_text}\n\n"
        )
    
    reply_text += "Yangi buyurtma berish uchun asosiy menyudan foydalaning."
    
    update.message.reply_text(reply_text)
    return MAIN_MENU

# Admin panel
def admin_panel(update: Update, context: CallbackContext) -> int:
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("Bu funksiya faqat adminlar uchun mavjud.")
        return MAIN_MENU
    
    keyboard = [
        [KeyboardButton("📋 Bugungi buyurtmalar")],
        [KeyboardButton("🗓 Barcha buyurtmalar")],
        [KeyboardButton("👥 Mijozlar ro'yxati")],
        [KeyboardButton("🔙 Asosiy menyu")]
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    update.message.reply_text(
        "👤 Admin panel:\n\n"
        "Quyidagi amallardan birini tanlang:",
        reply_markup=reply_markup
    )
    
    return ADMIN_PANEL

# Admin panel navigation
def admin_actions(update: Update, context: CallbackContext) -> int:
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("Bu funksiya faqat adminlar uchun mavjud.")
        return MAIN_MENU
    
    text = update.message.text
    
    if text == "📋 Bugungi buyurtmalar":
        today = datetime.datetime.now().strftime("%d.%m.%Y")
        return view_appointments_by_date(update, context, today)
    elif text == "🗓 Barcha buyurtmalar":
        return view_all_appointments(update, context)
    elif text == "👥 Mijozlar ro'yxati":
        return view_clients(update, context)
    elif text == "🔙 Asosiy menyu":
        # Return to main menu
        keyboard = [
            [KeyboardButton("📅 Yangi buyurtma berish")],
            [KeyboardButton("🔍 Mening buyurtmalarim")],
            [KeyboardButton("👤 Admin panel")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        update.message.reply_text("Asosiy menyu:", reply_markup=reply_markup)
        return MAIN_MENU
    
    return ADMIN_PANEL

# Handle errors
def error_handler(update: Update, context: CallbackContext) -> None:
    """Log the error and send a message to the user."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    try:
        # Send message to the user
        update.effective_message.reply_text(
            "Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring."
        )
    except:
        pass

# Helper function to cancel conversation
def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel conversation."""
    update.message.reply_text(
        "Amaliyot bekor qilindi. Asosiy menyuga qaytdingiz."
    )
    
    # Clear user data
    context.user_data.clear()
    
    return ConversationHandler.END

# View appointments for a specific date
def view_appointments_by_date(update: Update, context: CallbackContext, date=None) -> int:
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("Bu funksiya faqat adminlar uchun mavjud.")
        return MAIN_MENU
    
    conn = sqlite3.connect('barber_shop.db')
    cursor = conn.cursor()
    
    if date:
        cursor.execute(
            """
            SELECT a.id, a.service, a.date, a.time, a.status, a.price, 
                   u.first_name, u.last_name, u.phone_number
            FROM appointments a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.date = ?
            ORDER BY a.time
            """,
            (date,)
        )
        title = f"📋 {date} sanasidagi buyurtmalar:"
    else:
        # Get today's date
        today = datetime.datetime.now().strftime("%d.%m.%Y")
        cursor.execute(
            """
            SELECT a.id, a.service, a.date, a.time, a.status, a.price, 
                   u.first_name, u.last_name, u.phone_number
            FROM appointments a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.date = ?
            ORDER BY a.time
            """,
            (today,)
        )
        title = f"📋 Bugungi ({today}) buyurtmalar:"
    
    appointments = cursor.fetchall()
    conn.close()
    
    if not appointments:
        update.message.reply_text(f"{title}\n\nBuyurtmalar yo'q.")
        return ADMIN_PANEL
    
    reply_text = f"{title}\n\n"
    
    for appointment in appointments:
        appt_id, service, date, time, status, price, first_name, last_name, phone = appointment
        
        status_emoji = "✅" if status == "scheduled" else "❌"
        full_name = f"{first_name} {last_name}" if last_name else first_name
        no_phone_text = "Telefon raqam yo'q"
        
        reply_text += (
            f"🆔 #{appt_id}\n"
            f"👤 {full_name}\n"
            f"📱 {phone if phone else no_phone_text}\n"
            f"🧔 {service}\n"
            f"📅 {date}, {time}\n"
            f"💰 {price:,} so'm\n"
            f"{status_emoji} {status}\n\n"
        )
    
    # Send in chunks if too long
    if len(reply_text) > 4096:
        for i in range(0, len(reply_text), 4096):
            update.message.reply_text(reply_text[i:i+4096])
    else:
        update.message.reply_text(reply_text)
    
    return ADMIN_PANEL

# Handle existing appointment choice
def handle_existing_appointment(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    
    if query.data == "back_to_main":
        # Go back to main menu
        keyboard = [
            [KeyboardButton("📅 Yangi buyurtma berish")],
            [KeyboardButton("🔍 Mening buyurtmalarim")],
            [KeyboardButton("📞 Aloqa")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        query.message.delete()
        query.message.reply_text("Asosiy menyu:", reply_markup=reply_markup)
        return MAIN_MENU
    
    elif query.data == "new_appointment":
        # User wants to make a new appointment
        keyboard = []
        row = []
        
        # Create buttons for services
        for i, service in enumerate(ServiceType):
            if i % 2 == 0 and i > 0:  # 2 services per row
                keyboard.append(row)
                row = []
            
            # Format: Service name - Price
            button_text = f"{service.value} - {SERVICE_PRICES[service]:,} so'm"
            row.append(InlineKeyboardButton(button_text, callback_data=f"service_{service.name}"))
        
        if row:  # Add the last row if it exists
            keyboard.append(row)
            
        # Add back button
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            "Xizmat turini tanlang:",
            reply_markup=reply_markup
        )
        
        return SELECTING_SERVICE
        
    elif query.data.startswith("edit_appointment_"):
        # User wants to edit existing appointment
        appt_id = query.data.replace("edit_appointment_", "")
        
        # Get appointment details
        conn = sqlite3.connect('barber_shop.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT service, date, time FROM appointments WHERE id = ?",
            (appt_id,)
        )
        
        appointment = cursor.fetchone()
        conn.close()
        
        if not appointment:
            query.edit_message_text("Bu buyurtma topilmadi. Iltimos, qaytadan urinib ko'ring.")
            return MAIN_MENU
        
        service_value, date, time = appointment
        
        # Store appointment ID for editing
        context.user_data['editing_appointment_id'] = appt_id
        
        # Show appointment details with cancel option
        keyboard = [
            [InlineKeyboardButton("❌ Buyurtmani bekor qilish", callback_data="cancel_appointment")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_appointments")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            f"Buyurtma ma'lumotlari:\n\n"
            f"🆔 #{appt_id}\n"
            f"🧔 Xizmat: {service_value}\n"
            f"📅 Sana: {date}\n"
            f"🕒 Vaqt: {time}\n\n"
            f"Quyidagi amallardan birini tanlang:",
            reply_markup=reply_markup
        )
        
        return HANDLING_EXISTING_APPOINTMENT
    
    elif query.data == "cancel_appointment":
        # User wants to cancel their appointment
        appt_id = context.user_data.get('editing_appointment_id')
        
        if not appt_id:
            query.edit_message_text("Xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.")
            return MAIN_MENU
        
        # Update appointment status to canceled
        conn = sqlite3.connect('barber_shop.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE appointments SET status = 'canceled' WHERE id = ?",
            (appt_id,)
        )
        
        conn.commit()
        conn.close()
        
        # Inform user that appointment was canceled
        keyboard = [
            [KeyboardButton("📅 Yangi buyurtma berish")],
            [KeyboardButton("🔍 Mening buyurtmalarim")],
            [KeyboardButton("📞 Aloqa")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        query.edit_message_text(f"Buyurtma #{appt_id} bekor qilindi.")
        query.message.reply_text("Asosiy menyu:", reply_markup=reply_markup)
        
        # Clear user data
        context.user_data.clear()
        
        return MAIN_MENU
    
    elif query.data == "back_to_appointments":
        # Go back to appointment selection
        user_id = update.effective_user.id
        
        # Get user's appointments
        conn = sqlite3.connect('barber_shop.db')
        cursor = conn.cursor()
        
        current_date = datetime.datetime.now().strftime("%d.%m.%Y")
        cursor.execute(
            """
            SELECT id, service, date, time 
            FROM appointments 
            WHERE user_id = ? AND status = 'scheduled' AND date >= ?
            ORDER BY date, time
            LIMIT 1
            """,
            (user_id, current_date)
        )
        
        existing_appointment = cursor.fetchone()
        conn.close()
        
        if existing_appointment:
            appt_id, service, date, time = existing_appointment
            
            keyboard = [
                [InlineKeyboardButton("📝 Yangi buyurtma berish", callback_data="new_appointment")],
                [InlineKeyboardButton("✏️ Mavjud buyurtmani tahrirlash", callback_data=f"edit_appointment_{appt_id}")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                f"Sizda allaqachon buyurtma mavjud:\n\n"
                f"🧔 Xizmat: {service}\n"
                f"📅 Sana: {date}\n"
                f"🕒 Vaqt: {time}\n\n"
                f"Nima qilishni istaysiz?",
                reply_markup=reply_markup
            )
            
            return HANDLING_EXISTING_APPOINTMENT
    
    return MAIN_MENU

# Main function to run the bot
def main() -> None:
    # Create the updater and pass it your bot's token
    token = os.environ.get("TELEGRAM_TOKEN", "7202959264:AAEmSOBqrB_zXHI-lmMMpGs6GFEB-ayD-WU")
    updater = Updater(token=token)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Setup database
    setup_database()

    # Define conversation handler for booking appointments
    booking_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.regex(r"^📅 Yangi buyurtma berish$"), start_booking),
        ],
        states={
            SELECTING_SERVICE: [CallbackQueryHandler(select_service)],
            CHOOSING_DATE: [CallbackQueryHandler(choose_date)],
            CHOOSING_TIME: [CallbackQueryHandler(choose_time)],
            CONFIRMING_APPOINTMENT: [CallbackQueryHandler(confirm_appointment)],
            CONTACT_INFO: [
                MessageHandler(Filters.contact, contact_info),
                MessageHandler(Filters.text & ~Filters.command, contact_info),
            ],
            HANDLING_EXISTING_APPOINTMENT: [CallbackQueryHandler(handle_existing_appointment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        map_to_parent={
            ConversationHandler.END: MAIN_MENU,
        },
    )

    # Define conversation handler for the main menu
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                booking_handler,
                MessageHandler(Filters.regex(r"^🔍 Mening buyurtmalarim$"), view_my_appointments),
                MessageHandler(Filters.regex(r"^📞 Aloqa$"), main_menu),
                MessageHandler(Filters.regex(r"^👤 Admin panel$"), admin_panel),
            ],
            ADMIN_PANEL: [
                MessageHandler(Filters.text & ~Filters.command, admin_actions),
            ],
            ADMIN_VIEW_APPOINTMENTS: [
                MessageHandler(Filters.text & ~Filters.command, admin_actions),
            ],
            ADMIN_VIEW_CLIENTS: [
                MessageHandler(Filters.text & ~Filters.command, admin_actions),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add conversation handler
    dispatcher.add_handler(conv_handler)

    # Add error handler
    dispatcher.add_error_handler(error_handler)

    # Start the Bot
    updater.start_polling()
    
    # Run the bot until the user presses Ctrl-C
    updater.idle()

if __name__ == "__main__":
    main()

# View clients list
def view_clients(update: Update, context: CallbackContext) -> int:
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("Bu funksiya faqat adminlar uchun mavjud.")
        return MAIN_MENU
    
    conn = sqlite3.connect('barber_shop.db')
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT user_id, username, first_name, last_name, phone_number, registration_date,
               (SELECT COUNT(*) FROM appointments WHERE appointments.user_id = users.user_id) as appointment_count
        FROM users
        ORDER BY appointment_count DESC
        LIMIT 30
        """
    )
    
    clients = cursor.fetchall()
    conn.close()
    
    if not clients:
        update.message.reply_text("Mijozlar yo'q.")
        return ADMIN_PANEL
    
    reply_text = "👥 Mijozlar ro'yxati (top 30):\n\n"
    
    for client in clients:
        user_id, username, first_name, last_name, phone, reg_date, appt_count = client
        
        full_name = f"{first_name} {last_name}" if last_name else first_name
        username_text = f"@{username}" if username else "username yo'q"
        no_phone_text = "Telefon raqam yo'q"
        
        reply_text += (
            f"👤 {full_name} ({username_text})\n"
            f"🆔 {user_id}\n"
            f"📱 {phone if phone else no_phone_text}\n"
            f"📊 Buyurtmalar soni: {appt_count}\n"
            f"📅 Ro'yxatdan o'tgan: {reg_date}\n\n"
        )
    
    # Send in chunks if too long
    if len(reply_text) > 4096:
        for i in range(0, len(reply_text), 4096):
            update.message.reply_text(reply_text[i:i+4096])
    else:
        update.message.reply_text(reply_text)
    
    return ADMIN_PANEL

# View all appointments
def view_all_appointments(update: Update, context: CallbackContext) -> int:
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("Bu funksiya faqat adminlar uchun mavjud.")
        return MAIN_MENU
    
    conn = sqlite3.connect('barber_shop.db')
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT a.id, a.service, a.date, a.time, a.status, a.price, 
               u.first_name, u.last_name, u.phone_number
        FROM appointments a
        JOIN users u ON a.user_id = u.user_id
        ORDER BY a.date DESC, a.time DESC
        LIMIT 20
        """
    )
    
    appointments = cursor.fetchall()
    conn.close()
    
    if not appointments:
        update.message.reply_text("Buyurtmalar yo'q.")
        return ADMIN_PANEL
    
    reply_text = "🗓 So'nggi buyurtmalar (max 20):\n\n"
    
    for appointment in appointments:
        appt_id, service, date, time, status, price, first_name, last_name, phone = appointment
        
        status_emoji = "✅" if status == "scheduled" else "❌"
        full_name = f"{first_name} {last_name}" if last_name else first_name
        no_phone_text = "Telefon raqam yo'q"
        
        reply_text += (
            f"🆔 #{appt_id}\n"
            f"👤 {full_name}\n"
            f"📱 {phone if phone else no_phone_text}\n"
            f"🧔 {service}\n"
            f"📅 {date}, {time}\n"
            f"💰 {price:,} so'm\n"
            f"{status_emoji} {status}\n\n"
        )
    
    # Send in chunks if too long
    if len(reply_text) > 4096:
        for i in range(0, len(reply_text), 4096):
            update.message.reply_text(reply_text[i:i+4096])
    else:
        update.message.reply_text(reply_text)
    
    return ADMIN_PANEL
    