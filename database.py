import sqlite3
from datetime import datetime

def create_table():
    connection = sqlite3.connect("registrations.db")
    connection.execute("PRAGMA foreign_keys = ON")

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            student_class TEXT NOT NULL,
            phone TEXT NOT NULL,
            registered_at TEXT NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'پرداخت نشده'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            day TEXT NOT NULL,
            time TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO classes
        (id, name, capacity, day, time, price, description)
        VALUES (1, 'دهم', 30, 'شنبه و دوشنبه', '17:00 تا 19:00', 500000, 'کلاس تقویتی پایه دهم')
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO classes
        (id, name, capacity, day, time, price, description)
        VALUES (2, 'یازدهم', 30, 'یکشنبه و سه‌شنبه', '17:00 تا 19:00', 500000, 'کلاس تقویتی پایه یازدهم')
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO classes
        (id, name, capacity, day, time, price, description)
        VALUES (3, 'دوازدهم', 30, 'شنبه و چهارشنبه', '17:00 تا 19:00', 500000, 'کلاس تقویتی پایه دوازدهم')
    """)

    cursor.execute("PRAGMA table_info(registrations)")
    columns = [column[1] for column in cursor.fetchall()]

    if "payment_status" not in columns:
        cursor.execute("""
            ALTER TABLE registrations
            ADD COLUMN payment_status TEXT NOT NULL DEFAULT 'پرداخت نشده'
        """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            transaction_id TEXT UNIQUE,
            status TEXT NOT NULL DEFAULT 'در انتظار پرداخت',
            created_at TEXT NOT NULL,
            FOREIGN KEY (registration_id)
            REFERENCES registrations(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_id INTEGER NOT NULL,
            old_status TEXT NOT NULL,
            new_status TEXT NOT NULL,
            changed_by INTEGER NOT NULL,
            changed_at TEXT NOT NULL,
            FOREIGN KEY (registration_id)
            REFERENCES registrations(id)
        )
    """)

    connection.commit()
    connection.close()

def get_registrations():
    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, name, student_class, phone, registered_at, payment_status 
        FROM registrations
        """
    )

    registrations = cursor.fetchall()

    connection.close()

    return registrations


def phone_exists(phone, database_name="registrations.db"):
    connection = sqlite3.connect(database_name)

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM registrations WHERE phone = ?",
            (phone,)
        )

        registration = cursor.fetchone()

        return registration is not None

    finally:
        connection.close()


def delete_registration(registration_id, database_name="registrations.db"):
    connection = sqlite3.connect(database_name)
    connection.execute("PRAGMA foreign_keys = ON")

    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT id FROM registrations WHERE id = ?",
            (registration_id,)
        )

        if cursor.fetchone() is None:
            return "not_found"

        cursor.execute(
            "SELECT 1 FROM payments WHERE registration_id = ? LIMIT 1",
            (registration_id,)
        )
        has_payments = cursor.fetchone() is not None

        cursor.execute(
            "SELECT 1 FROM payment_history WHERE registration_id = ? LIMIT 1",
            (registration_id,)
        )
        has_history = cursor.fetchone() is not None

        if has_payments or has_history:
            return "has_history"

        cursor.execute(
            "DELETE FROM registrations WHERE id = ?",
            (registration_id,)
        )
        connection.commit()

        return "deleted"

    except sqlite3.IntegrityError:
        connection.rollback()
        return "has_history"

    finally:
        connection.close()

def get_class_capacity(student_class):
    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT capacity
        FROM classes
        WHERE name = ?
        """,
        (student_class,)
    )

    result = cursor.fetchone()

    connection.close()

    if result is None:
        return None

    return result[0]

def get_registration_count(student_class):
    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM registrations
        WHERE student_class = ?
        """,
        (student_class,)
    )

    result = cursor.fetchone()

    connection.close()

    return result[0]

def has_class_capacity(student_class):
    capacity = get_class_capacity(student_class)
    registration_count = get_registration_count(student_class)

    if capacity is None:
        return False

    return registration_count < capacity

def get_classes():
    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, name, capacity, day, time, price, description
        FROM classes
        ORDER BY id
        """
    )

    classes = cursor.fetchall()

    connection.close()

    return classes

def update_class_capacity(student_class, new_capacity):
    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE classes
        SET capacity = ?
        WHERE name = ?
        """,
        (new_capacity, student_class)
    )

    connection.commit()

    updated = cursor.rowcount

    connection.close()

    return updated > 0

def update_class_info(student_class, day, time, price, description):
    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE classes
        SET day = ?, time = ?, price = ?, description = ?
        WHERE name = ?
        """,
        (day, time, price, description, student_class)
    )

    connection.commit()

    updated = cursor.rowcount

    connection.close()

    return updated > 0

def create_payment(
    registration_id,
    amount,
    created_at,
    database_name="registrations.db"
):
    connection = sqlite3.connect(database_name)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO payments
            (registration_id, amount, status, created_at)
            VALUES (?, ?, 'در انتظار پرداخت', ?)
            """,
            (registration_id, amount, created_at)
        )

        payment_id = cursor.lastrowid
        connection.commit()

        return payment_id

    except sqlite3.Error:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_class_price(student_class, database_name="registrations.db"):
    connection = sqlite3.connect(database_name)
    cursor = connection.cursor()

    cursor.execute(
        "SELECT price FROM classes WHERE name = ?",
        (student_class,)
    )

    result = cursor.fetchone()
    connection.close()

    if result is None:
        return None

    return result[0]

def get_latest_payment(registration_id, database_name="registrations.db"):
    connection = sqlite3.connect(database_name)
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, status
        FROM payments
        WHERE registration_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (registration_id,))

    result = cursor.fetchone()
    connection.close()

    return result

def check_payment(registration_id, database_name="registrations.db"):
    latest_payment = get_latest_payment(registration_id, database_name)

    if latest_payment is None:
        return "not_found"

    status = latest_payment[1]

    if status == "در انتظار پرداخت" or status == "پرداخت موفق":
        return latest_payment

    if status == "پرداخت ناموفق":
        return "failed"

    return "unknown_status"

def check_registration_phone_constraint(database_name="registrations.db"):
    connection = sqlite3.connect(database_name)
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(registrations)")
    columns = cursor.fetchall()

    cursor.execute("PRAGMA index_list(registrations)")
    indexes = cursor.fetchall()

    connection.close()

    print("Columns:")
    for column in columns:
        print(column)

    print("\nIndexes:")
    for index in indexes:
        print(index)

def create_phone_unique_index(database_name="registrations.db"):
    connection = sqlite3.connect(database_name)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_registrations_phone
        ON registrations(phone)
    """)

    connection.commit()
    connection.close()

def create_registration_with_payment(
    name,
    student_class,
    phone,
    registered_at,
    database_name="registrations.db"
):
    connection = sqlite3.connect(database_name)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        cursor = connection.cursor()

        # شروع تراکنش نوشتن پیش از بررسی ظرفیت
        cursor.execute("BEGIN IMMEDIATE")

        # دریافت ظرفیت و شهریه کلاس
        cursor.execute(
            """
            SELECT capacity, price
            FROM classes
            WHERE name = ?
            """,
            (student_class,)
        )
        class_info = cursor.fetchone()

        if class_info is None:
            connection.rollback()
            return None

        capacity, amount = class_info

        # بررسی تعداد ثبت‌نام‌ها با همان اتصال
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM registrations
            WHERE student_class = ?
            """,
            (student_class,)
        )
        registration_count = cursor.fetchone()[0]

        if registration_count >= capacity:
            connection.rollback()
            return "capacity_full"

        # ایجاد ثبت‌نام
        cursor.execute(
            """
            INSERT INTO registrations
            (name, student_class, phone, registered_at, payment_status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                student_class,
                phone,
                registered_at,
                "پرداخت نشده"
            )
        )

        registration_id = cursor.lastrowid

        # ایجاد درخواست پرداخت در همان تراکنش
        cursor.execute(
            """
            INSERT INTO payments
            (registration_id, amount, status, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                registration_id,
                amount,
                "در انتظار پرداخت",
                registered_at
            )
        )

        payment_id = cursor.lastrowid

        connection.commit()

        return registration_id, payment_id, amount

    except sqlite3.Error:
        connection.rollback()
        raise

    finally:
        connection.close()

if __name__ == "__main__":
    check_registration_phone_constraint()
    create_phone_unique_index()

    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute("PRAGMA index_list(registrations)")
    indexes = cursor.fetchall()

    connection.close()

    print("Indexes after creation:")
    for index in indexes:
        print(index)

    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT phone, COUNT(*)
        FROM registrations
        GROUP BY phone
        HAVING COUNT(*) > 1
    """)

    duplicates = cursor.fetchall()
    connection.close()

    print("Duplicate phone numbers:", len(duplicates))

    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM registrations
        WHERE phone IS NULL OR phone = ''
    """)

    empty_phones = cursor.fetchone()[0]
    connection.close()

    print("Empty phone numbers:", empty_phones)

    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute("PRAGMA table_info(payments)")
    payment_columns = cursor.fetchall()

    cursor.execute("PRAGMA index_list(payments)")
    payment_indexes = cursor.fetchall()

    connection.close()

    print("Payment columns:")
    for column in payment_columns:
        print(column)

    print("Payment indexes:")
    for index in payment_indexes:
        print(index)

    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute("PRAGMA index_info('sqlite_autoindex_payments_1')")
    payment_index_columns = cursor.fetchall()

    connection.close()

    print("Columns in unique payment index:")
    for column in payment_index_columns:
        print(column)

    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute("PRAGMA foreign_key_list(payments)")
    payment_foreign_keys = cursor.fetchall()

    connection.close()

    print("Payment foreign keys:")
    for foreign_key in payment_foreign_keys:
        print(foreign_key)

    connection = sqlite3.connect("registrations.db")
    cursor = connection.cursor()

    cursor.execute("PRAGMA foreign_keys")
    foreign_keys_status = cursor.fetchone()

    connection.close()

    print("Foreign keys enabled:", foreign_keys_status)

    connection = sqlite3.connect("registrations.db")
    connection.execute("PRAGMA foreign_keys = ON")

    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys")

    print("Foreign keys enabled:", cursor.fetchone())

    connection.close()

