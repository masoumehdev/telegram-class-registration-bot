import os
import sqlite3

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.request import HTTPXRequest
from database import(
    create_table, 
    get_registrations, 
    phone_exists,
    delete_registration,
    has_class_capacity,
    get_registration_count,
    get_classes,
    update_class_capacity,
    get_class_capacity,
    update_class_info,
    create_phone_unique_index,
    create_registration_with_payment
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from datetime import datetime


load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID_VALUE = os.getenv("ADMIN_ID")

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing from .env")

if not ADMIN_ID_VALUE or not ADMIN_ID_VALUE.isdigit():
    raise ValueError("ADMIN_ID is missing or invalid in .env")

ADMIN_ID = int(ADMIN_ID_VALUE)

if ADMIN_ID <= 0:
    raise ValueError("ADMIN_ID must be a positive number")


CLASS = 1
NAME = 2
PHONE = 3

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("📚 ثبت‌نام در کلاس", callback_data="register")],
        [InlineKeyboardButton("ℹ️ اطلاعات کلاس", callback_data="class_info")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "سلام! 👋\nبه ربات ثبت‌نام کلاس خوش آمدید.",
        reply_markup=reply_markup
    )

    return CLASS

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Your Telegram ID: {update.effective_user.id}"
    )

async def show_registrations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ شما اجازه دسترسی به این بخش را ندارید."
        )
        return

    registrations = get_registrations()

    if not registrations:
        await update.message.reply_text(
            "هنوز هیچ ثبت‌نامی انجام نشده است."
        )
        return

    text = "📋 لیست ثبت‌نام‌ها:\n\n"

    for registration in registrations:
        id_, name, student_class, phone, registered_at, payment_status = registration

        text += (
            f"🆔 {id_}\n"
            f"👤 نام: {name}\n"
            f"📚 پایه: {student_class}\n"
            f"📱 شماره: {phone}\n"
            f"🕐 زمان ثبت‌نام: {registered_at}\n"
            f"💳 وضعیت پرداخت: {payment_status}\n"
            f"────────────\n"
        )

    await update.message.reply_text(text)

async def show_classes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ شما اجازه دسترسی به این بخش را ندارید."
        )
        return

    classes = get_classes()

    message = "📚 وضعیت کلاس‌ها\n\n"

    for class_id, name, capacity, day, time, price, description in classes:
        registration_count = get_registration_count(name)
        remaining = capacity - registration_count

        message += (
            f"📌 {name}\n"
            f"📅 روز: {day}\n"
            f"🕐 ساعت: {time}\n"
            f"💰 شهریه: {price:,} تومان\n"
            f"📝 توضیحات: {description}\n"
            f"ظرفیت: {capacity}\n"
            f"ثبت‌نام‌شده: {registration_count}\n"
            f"باقی‌مانده: {remaining}\n\n"
        )

    await update.message.reply_text(message)

async def show_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ شما اجازه دسترسی به این بخش را ندارید."
        )
        return

    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, student_class, phone, payment_status
        FROM registrations
        ORDER BY id
    """)

    registrations = cursor.fetchall()
    connection.close()

    if not registrations:
        await update.message.reply_text(
            "هنوز هیچ ثبت‌نامی انجام نشده است."
        )
        return

    message = "💳 وضعیت پرداخت دانش‌آموزان\n\n"

    for id_, name, student_class, phone, payment_status in registrations:
        message += (
            f"🆔 شماره ثبت‌نام: {id_}\n"
            f"👤 نام: {name}\n"
            f"📚 پایه: {student_class}\n"
            f"📱 موبایل: {phone}\n"
            f"💰 وضعیت پرداخت: {payment_status}\n"
            f"────────────\n"
        )

    await update.message.reply_text(message)

async def payment_report(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ شما اجازه دسترسی ندارید."
        )
        return

    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT payment_status, COUNT(*)
        FROM registrations
        GROUP BY payment_status
    """)

    results = cursor.fetchall()
    connection.close()

    counts = {
        "پرداخت موفق": 0,
        "پرداخت نشده": 0,
        "پرداخت ناموفق": 0,
    }

    for status, count in results:
        counts[status] = count

    total = sum(counts.values())

    message = (
        "📊 گزارش وضعیت پرداخت‌ها\n\n"
        f"✅ پرداخت موفق: {counts['پرداخت موفق']}\n"
        f"⏳ پرداخت نشده: {counts['پرداخت نشده']}\n"
        f"❌ پرداخت ناموفق: {counts['پرداخت ناموفق']}\n"
        f"👥 کل ثبت‌نام‌ها: {total}"
    )

    await update.message.reply_text(message)


async def set_payment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ شما اجازه دسترسی به این بخش را ندارید."
        )
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "روش استفاده:\n"
            "/setpayment شماره_ثبت‌نام unpaid/paid/failed"
        )
        return

    try:
        registration_id = int(context.args[0])
        if registration_id <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ شماره ثبت‌نام باید یک عدد مثبت باشد."
        )
        return

    statuses = {
        "unpaid": "پرداخت نشده",
        "paid": "پرداخت موفق",
        "failed": "پرداخت ناموفق",
    }

    payment_statuses = {
        "unpaid": "در انتظار پرداخت",
        "paid": "پرداخت موفق",
        "failed": "پرداخت ناموفق",
    }

    status_key = context.args[1].lower()

    if status_key not in statuses:
        await update.message.reply_text(
            "❌ وضعیت نامعتبر است.\n"
            "یکی از این گزینه‌ها را وارد کن:\n"
            "unpaid / paid / failed"
        )
        return

    connection = sqlite3.connect("registrations.db")
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        cursor = connection.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        # بررسی وجود ثبت‌نام و خواندن وضعیت فعلی
        cursor.execute(
            """
            SELECT payment_status
            FROM registrations
            WHERE id = ?
            """,
            (registration_id,)
        )
        registration = cursor.fetchone()

        if registration is None:
            connection.rollback()
            await update.message.reply_text(
                "❌ ثبت‌نامی با این شماره پیدا نشد."
            )
            return

        old_status = registration[0]

        # پیدا کردن آخرین رکورد پرداخت
        cursor.execute(
            """
            SELECT id, status
            FROM payments
            WHERE registration_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (registration_id,)
        )
        payment = cursor.fetchone()

        if payment is None:
            connection.rollback()
            await update.message.reply_text(
                "❌ برای این ثبت‌نام رکورد پرداختی وجود ندارد؛ "
                "وضعیت تغییر نکرد."
            )
            return

        payment_id, old_payment_status = payment

        valid_registration_statuses = set(statuses.values())
        valid_payment_statuses = set(payment_statuses.values())

        if (
            old_status not in valid_registration_statuses
            or old_payment_status not in valid_payment_statuses
        ):
            connection.rollback()
            await update.message.reply_text(
                "❌ وضعیت فعلی در پایگاه داده معتبر نیست؛ "
                "هیچ تغییری اعمال نشد."
            )
            return

        new_status = statuses[status_key]
        new_payment_status = payment_statuses[status_key]

        # اگر هر دو جدول از قبل هماهنگ هستند، کاری نکن
        if (
            old_status == new_status
            and old_payment_status == new_payment_status
        ):
            connection.rollback()
            await update.message.reply_text(
                "ℹ️ وضعیت پرداخت از قبل درست و هماهنگ است؛ "
                "تغییری ثبت نشد."
            )
            return

        # تغییر وضعیت ثبت‌نام
        cursor.execute(
            """
            UPDATE registrations
            SET payment_status = ?
            WHERE id = ?
            """,
            (new_status, registration_id)
        )

        # تغییر وضعیت آخرین پرداخت
        cursor.execute(
            """
            UPDATE payments
            SET status = ?
            WHERE id = ?
            """,
            (new_payment_status, payment_id)
        )

        # تاریخچه فقط وقتی وضعیت ثبت‌نام تغییر کرده ثبت می‌شود
        if old_status != new_status:
            cursor.execute(
                """
                INSERT INTO payment_history
                (
                    registration_id,
                    old_status,
                    new_status,
                    changed_by,
                    changed_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    registration_id,
                    old_status,
                    new_status,
                    update.effective_user.id,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )

        connection.commit()

    except sqlite3.Error:
        connection.rollback()
        await update.message.reply_text(
            "❌ خطای پایگاه داده رخ داد؛ "
            "تغییرات ذخیره نشدند."
        )
        return

    finally:
        connection.close()

    await update.message.reply_text(
        f"✅ وضعیت پرداخت ثبت‌نام شماره {registration_id} "
        f"به «{new_status}» تغییر کرد.\n"
        f"📋 وضعیت جدول پرداخت‌ها نیز هماهنگ شد."
    )

async def payment_history_command(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ شما اجازه دسترسی ندارید.")
        return

    if not context.args:
        await update.message.reply_text(
            "لطفاً شناسه ثبت‌نام را وارد کنید.\n"
            "مثال: /payment_history 1"
        )
        return

    try:
        registration_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ شناسه ثبت‌نام باید عدد باشد."
        )
        return

    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT old_status, new_status, changed_by, changed_at
        FROM payment_history
        WHERE registration_id = ?
        ORDER BY id ASC
        """,
        (registration_id,)
    )

    history = cursor.fetchall()
    connection.close()

    if not history:
        await update.message.reply_text(
            "برای این ثبت‌نام تاریخچه‌ای پیدا نشد."
        )
        return

    message = f"📋 تاریخچه پرداخت ثبت‌نام شماره {registration_id}:\n\n"

    for old_status, new_status, changed_by, changed_at in history:
        message += (
            f"🔄 {old_status} ← {new_status}\n"
            f"👤 شناسه ادمین: {changed_by}\n"
            f"🕒 زمان: {changed_at}\n\n"
        )

    await update.message.reply_text(message)

async def class_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    classes = get_classes()

    message = "📚 اطلاعات کلاس‌ها\n\n"

    for class_id, name, capacity, day, time, price, description in classes:
        registration_count = get_registration_count(name)
        remaining = capacity - registration_count

        if remaining > 0:
            status = f"🟢 {remaining} ظرفیت باقی‌مانده"
        else:
            status = "🔴 ظرفیت تکمیل شده"

        message += (
            f"📌 {name}\n"
            f"📅 روز: {day}\n"
            f"🕐 ساعت: {time}\n"
            f"💰 شهریه: {price:,} تومان\n"
            f"📝 توضیحات: {description}\n"
            f"ظرفیت: {capacity}\n"
            f"{status}\n\n"
        )

    await query.message.reply_text(message)

async def set_capacity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ شما اجازه دسترسی به این بخش را ندارید."
        )
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ فرمت دستور صحیح نیست.\n"
            "مثال:\n"
            "/setcapacity دهم 30"
        )
        return

    student_class = context.args[0]

    try:
        new_capacity = int(context.args[1])
    except ValueError:
        await update.message.reply_text(
            "❌ ظرفیت باید یک عدد باشد."
        )
        return

    if new_capacity < 1:
        await update.message.reply_text(
            "❌ ظرفیت باید حداقل ۱ نفر باشد."
        )
        return

    updated = update_class_capacity(student_class, new_capacity)

    if updated:
        await update.message.reply_text(
            f"✅ ظرفیت کلاس {student_class} به {new_capacity} نفر تغییر کرد."
        )
    else:
        await update.message.reply_text(
            "❌ کلاسی با این نام پیدا نشد."
        )


async def edit_class_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ شما اجازه دسترسی به این بخش را ندارید."
        )
        return

    if len(context.args) < 5:
        await update.message.reply_text(
            "❌ فرمت دستور صحیح نیست.\n\n"
            "مثال:\n"
            "/editclass دهم شنبه_و_دوشنبه 17:00-19:00 600000 کلاس_تقویتی_جدید"
        )
        return

    student_class = context.args[0]
    day = context.args[1].replace("_", " ")
    time = context.args[2]
    description = " ".join(context.args[4:]).replace("_", " ")

    try:
        price = int(context.args[3])
    except ValueError:
        await update.message.reply_text(
            "❌ شهریه باید عدد باشد."
        )
        return

    if price < 0:
        await update.message.reply_text(
            "❌ شهریه نمی‌تواند منفی باشد."
        )
        return

    updated = update_class_info(
        student_class, day, time, price, description
    )

    if updated:
        await update.message.reply_text(
            f"✅ اطلاعات کلاس {student_class} با موفقیت تغییر کرد."
        )
    else:
        await update.message.reply_text(
            "❌ کلاسی با این نام پیدا نشد."
        )

async def delete_registration_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ شما اجازه دسترسی به این بخش را ندارید."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "❌ لطفاً شناسه ثبت‌نام را وارد کنید.\n"
            "مثال: /delete 3"
        )
        return

    try:
        registration_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ شناسه ثبت‌نام باید یک عدد باشد."
        )
        return

    result = delete_registration(registration_id)

    if result == "deleted":
        await update.message.reply_text(
            "✅ ثبت‌نام با موفقیت حذف شد."
        )

    elif result == "not_found":
        await update.message.reply_text(
            "❌ ثبت‌نامی با این شناسه پیدا نشد."
        )

    elif result == "has_history":
        await update.message.reply_text(
            "⚠️ این ثبت‌نام سابقه پرداخت یا تاریخچه دارد؛ "
            "برای حفظ سوابق، حذف آن انجام نشد."
        )

    else:
        await update.message.reply_text(
            "❌ نتیجه حذف مشخص نیست. لطفاً دیتابیس را بررسی کنید."
        )


async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    capacity_10 = get_class_capacity("دهم")
    registered_10 = get_registration_count("دهم")
    remaining_10 = capacity_10 - registered_10

    capacity_11 = get_class_capacity("یازدهم")
    registered_11 = get_registration_count("یازدهم")
    remaining_11 = capacity_11 - registered_11

    capacity_12 = get_class_capacity("دوازدهم")
    registered_12 = get_registration_count("دوازدهم")
    remaining_12 = capacity_12 - registered_12

    if remaining_10 > 0:
        class_10_text = f"دهم — {remaining_10} ظرفیت باقی‌مانده"
    else:
        class_10_text = "دهم — تکمیل ظرفیت"

    if remaining_11 > 0:
        class_11_text = f"یازدهم — {remaining_11} ظرفیت باقی‌مانده"
    else:
        class_11_text = "یازدهم — تکمیل ظرفیت"

    if remaining_12 > 0:
        class_12_text = f"دوازدهم — {remaining_12} ظرفیت باقی‌مانده"
    else:
        class_12_text = "دوازدهم — تکمیل ظرفیت"

    keyboard = [
        [InlineKeyboardButton(
            class_10_text,
            callback_data="class_10"
        )],
        [InlineKeyboardButton(
            class_11_text,
            callback_data="class_11"
        )],
        [InlineKeyboardButton(
            class_12_text,
            callback_data="class_12"
        )],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "📚 لطفاً پایه تحصیلی خود را انتخاب کنید:",
        reply_markup=reply_markup
    )

    return CLASS

async def select_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    classes = {
        "class_10": "دهم",
        "class_11": "یازدهم",
        "class_12": "دوازدهم",
    }

    selected_class = classes[query.data]

    if not has_class_capacity(selected_class):
        await query.message.reply_text(
            "❌ ظرفیت این کلاس تکمیل شده است."
        )
        return ConversationHandler.END

    context.user_data["class"] = selected_class

    await query.message.reply_text(
        f"پایه {selected_class} انتخاب شد.\n"
        "لطفاً نام و نام خانوادگی خود را وارد کنید:"
    )

    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()

    if not name:
        await update.message.reply_text(
            "❌ لطفاً نام و نام خانوادگی خود را وارد کنید."
        )
        return NAME

    if not any(char.isalpha() for char in name):
        await update.message.reply_text(
            "❌ لطفاً نام واقعی خود را وارد کنید."
        )
        return NAME

    context.user_data["name"] = name

    if context.user_data.get("editing") == "name":
        context.user_data.pop("editing", None)

        await update.message.reply_text(
            "✅ نام شما با موفقیت تغییر کرد."
        )

        return await show_registration_confirmation(update, context)

    await update.message.reply_text(
        f"نام شما: {name}\n"
        f"پایه: {context.user_data['class']}\n\n"
        "حالا شماره موبایل خود را وارد کنید:"
    )

    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()

    # تبدیل اعداد فارسی و عربی به انگلیسی
    phone = phone.translate(str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789"
    ))

    if not phone.isdigit():
        await update.message.reply_text(
            "❌ لطفاً فقط شماره موبایل خود را وارد کنید."
        )
        return PHONE

    if len(phone) != 11 or not phone.startswith("09"):
        await update.message.reply_text(
            "❌ شماره موبایل باید ۱۱ رقم باشد و با 09 شروع شود."
        )
        return PHONE

    if context.user_data.get("editing") == "phone":
        if phone_exists(phone):
            await update.message.reply_text(
                "❌ این شماره موبایل قبلاً ثبت‌نام کرده است. "
                "لطفاً شماره دیگری وارد کنید."
            )
            return PHONE

    context.user_data["phone"] = phone

    if context.user_data.get("editing") == "phone":
        context.user_data.pop("editing", None)

        await update.message.reply_text(
            "✅ شماره موبایل شما با موفقیت تغییر کرد."
        )

        return await show_registration_confirmation(update, context)

    keyboard = [
    [
        InlineKeyboardButton("✅ تأیید", callback_data="confirm"),
        InlineKeyboardButton("✏️ ویرایش", callback_data="edit"),
    ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📋 اطلاعات ثبت‌نام:\n\n"
        f"نام: {context.user_data['name']}\n"
        f"پایه: {context.user_data['class']}\n"
        f"شماره: {phone}\n\n"
        "آیا اطلاعات درست است؟",
        reply_markup=reply_markup
    )

    return PHONE

async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if context.user_data.get("registration_processing"):
        return ConversationHandler.END

    context.user_data["registration_processing"] = True

    name = context.user_data["name"]
    student_class = context.user_data["class"]
    phone = context.user_data["phone"]

    if phone_exists(phone):
        await query.message.reply_text(
            "❌ این شماره موبایل قبلاً ثبت‌نام کرده است."
        )
        context.user_data["registration_processing"] = False
    
        return ConversationHandler.END
  
    registered_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        result = create_registration_with_payment(
            name,
            student_class,
            phone,
            registered_at
        )

    except sqlite3.IntegrityError:
        context.user_data["registration_processing"] = False

        try:
            duplicate_phone = phone_exists(phone)
        except sqlite3.Error:
            await query.message.reply_text(
                "❌ هنگام بررسی اطلاعات ثبت‌نام خطایی رخ داد. "
                "لطفاً دوباره تلاش کنید."
            )
            return ConversationHandler.END

        if duplicate_phone:
            await query.message.reply_text(
                "❌ این شماره موبایل قبلاً ثبت‌نام کرده است."
            )
        else:
            await query.message.reply_text(
                "❌ هنگام ثبت اطلاعات، محدودیتی در دیتابیس نقض شد. "
                "لطفاً با پشتیبانی تماس بگیرید."
            )

        return ConversationHandler.END

    except sqlite3.Error:
        context.user_data["registration_processing"] = False

        await query.message.reply_text(
            "❌ هنگام ثبت‌نام یا ایجاد درخواست پرداخت خطایی رخ داد. "
            "هیچ‌کدام از این دو عملیات ذخیره نشدند؛ لطفاً دوباره تلاش کنید."
        )
        return ConversationHandler.END

    if result is None:
        context.user_data["registration_processing"] = False
        await query.message.reply_text(
            "❌ شهریه این کلاس پیدا نشد. لطفاً با پشتیبانی تماس بگیرید."
        )
        return ConversationHandler.END

    if result == "capacity_full":
        context.user_data["registration_processing"] = False
        await query.message.reply_text(
            "❌ متأسفانه ظرفیت این کلاس تکمیل شده است."
        )
        return ConversationHandler.END

    registration_id, payment_id, amount = result

    payment_status = "در انتظار پرداخت"

    context.user_data["registration_processing"] = False

    await query.message.reply_text(
        f"✅ ثبت‌نام شما ثبت شد.\n"
        f"شماره ثبت‌نام: {registration_id}\n"
        f"شماره درخواست پرداخت: {payment_id}\n"
        f"مبلغ: {amount:,} تومان\n"
        f"وضعیت پرداخت: {payment_status}\n\n"
        "توجه: این پروژه فعلاً پرداخت آزمایشی دارد و مبلغی واقعاً پرداخت نشده است."
    )

    return ConversationHandler.END

async def edit_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("👤 نام", callback_data="edit_name")],
        [InlineKeyboardButton("📚 پایه", callback_data="edit_class")],
        [InlineKeyboardButton("📱 شماره", callback_data="edit_phone")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "✏️ کدام اطلاعات را می‌خواهید ویرایش کنید؟",
        reply_markup=reply_markup
    )

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["editing"] = "name"

    await query.message.reply_text(
        "👤 لطفاً نام و نام خانوادگی جدید خود را وارد کنید:"
    )

    return NAME

async def edit_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("دهم", callback_data="edit_class_10")],
        [InlineKeyboardButton("یازدهم", callback_data="edit_class_11")],
        [InlineKeyboardButton("دوازدهم", callback_data="edit_class_12")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "📚 لطفاً پایه جدید خود را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def select_edit_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    classes = {
        "edit_class_10": "دهم",
        "edit_class_11": "یازدهم",
        "edit_class_12": "دوازدهم",
    }

    selected_class = classes[query.data]

    if not has_class_capacity(selected_class):
        await query.message.reply_text(
            "❌ ظرفیت این کلاس تکمیل شده است."
        )
        return PHONE

    context.user_data["class"] = selected_class

    await query.message.reply_text(
        f"✅ پایه به {selected_class} تغییر کرد."
    )

    return await show_registration_confirmation(update, context)

async def show_registration_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("✅ تأیید", callback_data="confirm"),
            InlineKeyboardButton("✏️ ویرایش", callback_data="edit"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        "📋 اطلاعات ثبت‌نام:\n\n"
        f"نام: {context.user_data['name']}\n"
        f"پایه: {context.user_data['class']}\n"
        f"شماره: {context.user_data['phone']}\n\n"
        "آیا اطلاعات درست است؟"
    )

    if update.callback_query:
        await update.callback_query.message.reply_text(
            message,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup
        )

    return PHONE

async def edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["editing"] = "phone"

    await query.message.reply_text(
        "📱 لطفاً شماره موبایل جدید خود را وارد کنید:"
    )

    return PHONE

conversation_handler = ConversationHandler(
    entry_points=[
        CommandHandler("start", start)
    ],

    states={
        CLASS: [
            CallbackQueryHandler(
                register_start,
                pattern="^register$"
            ),
            CallbackQueryHandler(
                select_class,
                pattern="^class_(10|11|12)$"
            ),
            CallbackQueryHandler(
                class_info,
                pattern="^class_info$"
            ),
        ],

        NAME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                get_name
            ),
        ],

        PHONE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                get_phone
            ),
            CallbackQueryHandler(
                confirm_registration,
                pattern="^confirm$"
            ),
            CallbackQueryHandler(
                edit_registration,
                pattern="^edit$"
            ),
            CallbackQueryHandler(
                edit_name,
                pattern="^edit_name$"
            ),
            CallbackQueryHandler(
                edit_class,
                pattern="^edit_class$"
            ),
            CallbackQueryHandler(
                edit_phone,
                pattern="^edit_phone$"
            ),
            CallbackQueryHandler(
                select_edit_class,
                pattern="^edit_class_(10|11|12)$"
            ),
        ],
    },

    fallbacks=[
    CommandHandler("start", start),
    ],
)

create_table()
create_phone_unique_index()

request = HTTPXRequest(
    proxy="http://127.0.0.1:8080",
    connect_timeout=30,
    read_timeout=30,
)

app = (
    Application.builder()
    .token(TOKEN)
    .request(request)
    .get_updates_request(request)
    .build()
)

app.add_handler(CommandHandler("myid", my_id))

app.add_handler(CommandHandler("registrations", show_registrations))
app.add_handler(CommandHandler("delete", delete_registration_command))
app.add_handler(CommandHandler("classes", show_classes))
app.add_handler(CommandHandler("setcapacity", set_capacity_command))
app.add_handler(CommandHandler("payments", show_payments))
app.add_handler(CommandHandler("setpayment", set_payment_command))
app.add_handler(CommandHandler("payment_history", payment_history_command))
app.add_handler(CommandHandler("payment_report", payment_report))
app.add_handler(CommandHandler("editclass", edit_class_command))


app.add_handler(conversation_handler)

app.run_polling()