from fastapi import FastAPI
import databases
import sqlalchemy

DATABASE_URL = "postgresql://postgres:password@postgres:5432/ege_db"
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

students = sqlalchemy.Table(
    "students",
    metadata,
    sqlalchemy.Column("telegram_id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String),
)

scores = sqlalchemy.Table(
    "scores",
    metadata,
    sqlalchemy.Column("telegram_id", sqlalchemy.String),
    sqlalchemy.Column("subject", sqlalchemy.String),
    sqlalchemy.Column("score", sqlalchemy.Integer),
)

app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()
    engine = sqlalchemy.create_engine(DATABASE_URL)
    metadata.create_all(engine)

@app.post("/students/{telegram_id}/{name}")
async def create_student(telegram_id: str, name: str):
    try:
        query = students.insert().values(telegram_id=telegram_id, name=name)
        await database.execute(query)
        return "ok"
    except:
        return "error"

@app.get("/students/{telegram_id}")
async def get_student(telegram_id: str):
    query = students.select().where(students.c.telegram_id == telegram_id)
    student = await database.fetch_one(query)
    if not student:
        return "not found"
    
    query = scores.select().where(scores.c.telegram_id == telegram_id)
    student_scores = await database.fetch_all(query)
    
    return [{"subject": s.subject, "score": s.score} for s in student_scores]

@app.post("/scores/{telegram_id}/{subject}/{score}")
async def create_score(telegram_id: str, subject: str, score: int):
    query = students.select().where(students.c.telegram_id == telegram_id)
    student = await database.fetch_one(query)
    if not student:
        return "not found"
    
    try:
        query = scores.insert().values(telegram_id=telegram_id, subject=subject, score=score)
        await database.execute(query)
        return "ok"
    except:
        return "error"

@app.get("/subjects")
async def get_subjects():
    return ["Математика", "Русский", "Информатика"]