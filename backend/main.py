from fastapi import FastAPI
import databases
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy import text
import asyncio
import os
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s- %(message)s'
)
logger = logging.getLogger(__name__)

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
    
    engine = create_engine(DATABASE_URL)
    metadata.create_all(engine)

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/students/{telegram_id}/{name}")
async def create_student(telegram_id: str, name: str):
    logger.info(f"Attemting register student: {name}, id: {telegram_id}")
    try:
        query = students.select().where(students.c.telegram_id == telegram_id)
        existing_student = await database.fetch_one(query)
        if existing_student:
            return "already_exists"
        
        query = students.insert().values(telegram_id=telegram_id, name=name)
        await database.execute(query)
        return "ok"
    except Exception as e:
        logger.info(f"Error registering student: {name}, id: {telegram_id}")
        return "error"

@app.get("/students/{telegram_id}")
async def get_student_scores(telegram_id: str):
    logger.info(f"Fetching scores for student: {telegram_id}")
    query = students.select().where(students.c.telegram_id == telegram_id)
    student = await database.fetch_one(query)
    if not student:
        logger.error(f"Student not found: {telegram_id}")
        return "not found"
    
    query = scores.select().where(scores.c.telegram_id == telegram_id)
    student_scores = await database.fetch_all(query)
    
    return [{"subject": score.subject, "score": score.score} for score in student_scores]

@app.post("/scores/{telegram_id}/{subject}/{score}")
async def create_score(telegram_id: str, subject: str, score: int):
    logger.info(f"Adding score: {telegram_id}, {subject}, {score}")
    query = students.select().where(students.c.telegram_id == telegram_id)
    student = await database.fetch_one(query)
    if not student:
        logger.warning(f"Student not found when adding score: {telegram_id}")
        return "not found"
    
    if not 0 <= score <= 100:
        logger.warning(f"Invalid score attempted: {score} for student {telegram_id}")
        return "invalid_score"
    
    try:
        query = scores.insert().values(telegram_id=telegram_id, subject=subject, score=score)
        await database.execute(query)
        logger.info(f"Score added successfully: {telegram_id}, {subject}, {score}")
        return "ok"
    except Exception as e:
        logger.error(f"Error adding score for {telegram_id}: {str(e)}")
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
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "database": "disconnected"}