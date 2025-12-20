import sqlite3
from reportlab.pdfgen import canvas
from datetime import datetime

DB_NAME = "users.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


# 🔹 Top 100 (faqat balli userlar)
def get_top_100():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, score 
        FROM users 
        WHERE score > 0
        ORDER BY score DESC
        LIMIT 100
    """)

    data = cursor.fetchall()
    conn.close()
    return data


# 🔹 Faol ishtirokchilar
def get_active_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, score 
        FROM users 
        WHERE score > 0
        ORDER BY score DESC
    """)

    data = cursor.fetchall()
    conn.close()
    return data


# 🔹 Universal PDF
def generate_rating_pdf(data, title="Reyting"):
    file_name = "rating.pdf"
    pdf = canvas.Canvas(file_name)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, 820, title)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        50, 800,
        f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    y = 760
    pdf.setFont("Helvetica", 11)

    for i, (uid, score) in enumerate(data, start=1):
        pdf.drawString(
            50, y,
            f"{i}. User ID: {uid}  |  Ball: {score}"
        )
        y -= 18

        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = 800

    pdf.save()
    return file_name
