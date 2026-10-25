
import sqlite3
from datetime import datetime

DATABASE_NAME = "delete_test.db"

REGISTRATION_STATUSES = {
    "unpaid": "پرداخت نشده",
    "paid": "پرداخت موفق",
    "failed": "پرداخت ناموفق",
}

PAYMENT_STATUSES = {
    "unpaid": "در انتظار پرداخت",
    "paid": "پرداخت موفق",
    "failed": "پرداخت ناموفق",
}


def test_set_payment(registration_id, status_key):
    connection = sqlite3.connect(DATABASE_NAME)

    try:
        connection.execute("BEGIN")
        cursor = connection.cursor()

        if status_key not in REGISTRATION_STATUSES:
            print("هشدار: وضعیت درخواستی نامعتبر است.")
            return

        cursor.execute(
            """
            SELECT payment_status
            FROM registrations
            WHERE id = ?
            """,
            (registration_id,),
        )
        registration = cursor.fetchone()

        if registration is None:
            print("هشدار: ثبت‌نام پیدا نشد.")
            return

        cursor.execute(
            """
            SELECT id, status
            FROM payments
            WHERE registration_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (registration_id,),
        )
        payment = cursor.fetchone()

        if payment is None:
            print("هشدار: پرداختی برای این ثبت‌نام وجود ندارد.")
            return

        payment_id, old_payment_status = payment

        allowed_payment_statuses = {
            "در انتظار پرداخت",
            "پرداخت موفق",
            "پرداخت ناموفق",
        }

        if old_payment_status not in allowed_payment_statuses:
            print("هشدار: وضعیت آخرین پرداخت ناشناخته است.")
            print("هیچ تغییری انجام نمی‌شود.")
            return

        old_registration_status = registration[0]
        new_registration_status = REGISTRATION_STATUSES[status_key]
        new_payment_status = PAYMENT_STATUSES[status_key]

        if (
            old_registration_status == new_registration_status
            and old_payment_status == new_payment_status
        ):
            print("وضعیت‌ها از قبل هماهنگ هستند.")
            return

        cursor.execute(
            """
            UPDATE registrations
            SET payment_status = ?
            WHERE id = ?
            """,
            (new_registration_status, registration_id),
        )

        cursor.execute(
            """
            UPDATE payments
            SET status = ?
            WHERE id = ?
            """,
            (new_payment_status, payment_id),
        )

        cursor.execute(
            """
            INSERT INTO payment_history
            (registration_id, old_status, new_status, changed_by, changed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                registration_id,
                old_registration_status,
                new_registration_status,
                999999,  # شناسهٔ آزمایشی ادمین
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

        print("آزمایش موفق بود:")
        print("وضعیت ثبت‌نام و پرداخت هماهنگ شدند.")
        print("رکورد تاریخچه نیز ایجاد شد.")

    except sqlite3.Error as error:
        print("خطای دیتابیس:", error)

    finally:
        connection.rollback()
        connection.close()
        print("تغییرات آزمایشی ذخیره نشدند.")


test_set_payment(2, "paid")
print()
test_set_payment(3, "paid")