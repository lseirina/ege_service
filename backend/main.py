from fastapi import FastAPI
import databases
import sqlalchemy
from sqlalchemy import text
import asyncio
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/ege_db")

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

students = sqlalchemy.Table(
    "students",
    metadata,
    sqlalchemy.Column("telegram_id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, nullable=False),
)

scores = sqlalchemy.Table(
    "scores",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("telegram_id", sqlalchemy.String, sqlalchemy.ForeignKey("students.telegram_id")),
    sqlalchemy.Column("subject", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("score", sqlalchemy.Integer, nullable=False),
)

app = FastAPI()

async def wait_for_db():
    for i in range(10):
        try:
            await database.connect()
            return True
        except Exception:
            print(f"Database connection failed, retrying... ({i+1}/10)")
            await asyncio.sleep(2)
    raise Exception("Could not connect to database")

@app.on_event("startup")
async def startup():
    await wait_for_db()
    
    async with database.connection() as connection:
        await connection.execute(text("""
            CREATE TABLE IF NOT EXISTS students (
                telegram_id TEXT PRIMARY KEY,
                name TEXT NOT NULL
            )
        """))
        await connection.execute(text("""
            CREATE TABLE IF NOT EXISTS scores (
                id SERIAL PRIMARY KEY,
                telegram_id TEXT REFERENCES students(telegram_id),
                subject TEXT NOT NULL,
                score INTEGER NOT NULL
            )
        """))

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/students/{telegram_id}/{name}")
async def create_student(telegram_id: str, name: str):
    try:
        query = students.select().where(students.c.telegram_id == telegram_id)
        existing_student = await database.fetch_one(query)
        if existing_student:
            return "already_exists"
        
        query = students.insert().values(telegram_id=telegram_id, name=name)
        await database.execute(query)
        return "ok"
    except Exception as e:
        return "error"

@app.get("/students/{telegram_id}")
async def get_student_scores(telegram_id: str):
    query = students.select().where(students.c.telegram_id == telegram_id)
    student = await database.fetch_one(query)
    if not student:
        return "not found"
    
    query = scores.select().where(scores.c.telegram_id == telegram_id)
    student_scores = await database.fetch_all(query)
    
    return [{"subject": score.subject, "score": score.score} for score in student_scores]

@app.post("/scores/{telegram_id}/{subject}/{score}")
async def create_score(telegram_id: str, subject: str, score: int):
    query = students.select().where(students.c.telegram_id == telegram_id)
    student = await database.fetch_one(query)
    if not student:
        return "not found"
    
    if not 0 <= score <= 100:
        return "invalid_score"
    
    try:
        query = scores.insert().values(telegram_id=telegram_id, subject=subject, score=score)
        await database.execute(query)
        return "ok"
    except Exception as e:
        return "error"

@app.get("/subjects")
async def get_subjects():
    return ["Математика", "Русский язык", "Информатика", "Физика", "Химия"]

@app.get("/health")
async def health_check():
    try:
        await database.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected"}