import sqlite3
from reportlab.pdfgen import canvas
from datetime import datetime

DB_NAME = "users.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


# 🔹 Top 100
def get_top_100():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username, phone, score
        FROM users
        WHERE score > 0
        ORDER BY score DESC
        LIMIT 100
    """)

    data = cursor.fetchall()
    conn.close()
    return data


# 🔹 PDF header
def draw_header(pdf, title):
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, 820, title)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        50, 800,
        f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )


# 🔹 Universal PDF
def generate_rating_pdf(data, title="Reyting"):
    file_name = "rating.pdf"
    pdf = canvas.Canvas(file_name)

    draw_header(pdf, title)

    y = 760
    pdf.setFont("Helvetica", 11)

    total_score = 0

    for i, (username, phone, score) in enumerate(data, start=1):
        name = username if username else phone

        pdf.drawString(
            50, y,
            f"{i}. {name}  |  Ball: {score}"
        )

        total_score += score
        y -= 18

        # 🔹 Yangi bet
        if y < 60:
            pdf.showPage()
            draw_header(pdf, title)
            pdf.setFont("Helvetica", 11)
            y = 760

    # 🔹 Umumiy ball (oxirgi betda)
    if y < 100:
        pdf.showPage()
        draw_header(pdf, title)
        y = 760

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(
        50, y - 20,
        f"Umumiy ball: {total_score}"
    )

    pdf.save()
    return file_name
