from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from database import supabase

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELOS ---
class StudentCreate(BaseModel):
    name: str
    email: Optional[str] = None
    age: Optional[int] = None
    goal: Optional[str] = None
    professor_id: int

class Exercise(BaseModel):
    name: str
    sets: int
    reps: str
    weight: Optional[str] = None

class WorkoutCreate(BaseModel):
    student_id: str
    title: str
    exercises: List[Exercise]

# --- ROTAS DE ALUNOS ---
@app.post("/students")
def create_student(student: StudentCreate):
    try:
        response = supabase.table("students").insert(student.dict()).execute()
        return {"message": "Aluno cadastrado com sucesso!", "data": response.data}
    except Exception as e:
        print("=== ERRO AO CADASTRAR ALUNO ===")
        print(e)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/professors/{professor_id}/students")
def list_professor_students(professor_id: int):
    try:
        response = supabase.table("students").select("*").eq("professor_id", professor_id).execute()
        return response.data
    except Exception as e:
        print("=== ERRO AO LISTAR ALUNOS ===")
        print(e)
        raise HTTPException(status_code=400, detail=str(e))

# --- ROTAS DE TREINOS ---
@app.post("/workouts")
def create_workout(workout: WorkoutCreate):
    try:
        response = supabase.table("workouts").insert({
            "student_id": workout.student_id,
            "title": workout.title,
            "exercises": [e.dict() for e in workout.exercises]
        }).execute()
        return {"message": "Ficha criada com sucesso!", "data": response.data}
    except Exception as e:
        print("=== ERRO AO CRIAR WORKOUT ===")
        print(e)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/students/{student_id}/workouts")
def get_student_workouts(student_id: str):
    try:
        response = supabase.table("workouts").select("*").eq("student_id", student_id).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "ProEvolua API running"}