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
class LoginRequest(BaseModel):
    email: str
    password: str

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
    rest_time: Optional[str] = None
    notes: Optional[str] = None
    day: Optional[str] = None

class WorkoutCreate(BaseModel):
    student_id: str
    title: str
    description: Optional[str] = None
    exercises: List[Exercise]

class AssessmentCreate(BaseModel):
    student_id: str
    weight: float
    height: Optional[float] = None
    body_fat: Optional[float] = None
    body_fat_kg: Optional[float] = None       # Novo
    lean_mass: Optional[float] = None         # Novo
    skeletal_muscle: Optional[float] = None   # Novo
    total_body_water: Optional[float] = None  # Novo
    visceral_fat: Optional[int] = None        # Novo
    bone_mass: Optional[float] = None         # Novo
    metabolic_age: Optional[int] = None
    chest: Optional[float] = None
    waist: Optional[float] = None
    arms: Optional[float] = None
    legs: Optional[float] = None

class AssessmentUpdate(BaseModel):
    weight: float
    height: Optional[float] = None
    body_fat: Optional[float] = None
    chest: Optional[float] = None
    waist: Optional[float] = None
    arms: Optional[float] = None
    legs: Optional[float] = None

# --- ROTA DE LOGIN ---
@app.post("/auth/login")
def login(data: LoginRequest):
    try:
        response = supabase.table("professors").select("*").eq("email", data.email).execute()
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
        
        professor = response.data[0]
        if professor.get("password") and professor.get("password") != data.password:
            raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

        return {
            "message": "Login realizado com sucesso!",
            "professor_id": professor["id"],
            "name": professor.get("full_name", "Professor")
        }
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- ROTAS DE ALUNOS ---
@app.post("/students")
def create_student(student: StudentCreate):
    try:
        response = supabase.table("students").insert(student.dict()).execute()
        return {"message": "Aluno cadastrado com sucesso!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/professors/{professor_id}/students")
def list_professor_students(professor_id: int):
    try:
        response = supabase.table("students").select("*").eq("professor_id", professor_id).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/students/{student_id}")
def get_student(student_id: str):
    try:
        response = supabase.table("students").select("*").eq("id", student_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/students/{student_id}")
def update_student(student_id: str, student: StudentCreate):
    try:
        response = supabase.table("students").update({
            "name": student.name,
            "email": student.email,
            "age": student.age,
            "goal": student.goal
        }).eq("id", student_id).execute()
        return {"message": "Aluno atualizado com sucesso!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/students/{student_id}")
def delete_student(student_id: str):
    try:
        response = supabase.table("students").delete().eq("id", student_id).execute()
        return {"message": "Aluno excluído com sucesso!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- ROTAS DE TREINOS ---
@app.post("/workouts")
def create_workout(workout: WorkoutCreate):
    try:
        response = supabase.table("workouts").insert({
            "student_id": workout.student_id,
            "title": workout.title,
            "description": workout.description,
            "exercises": [e.dict() for e in workout.exercises]
        }).execute()
        return {"message": "Ficha criada com sucesso!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/workouts/{workout_id}")
def update_workout(workout_id: str, workout: WorkoutCreate):
    try:
        response = supabase.table("workouts").update({
            "title": workout.title,
            "description": workout.description,
            "exercises": [e.dict() for e in workout.exercises]
        }).eq("id", workout_id).execute()
        return {"message": "Ficha de treino atualizada com sucesso!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/students/{student_id}/workouts")
def get_student_workouts(student_id: str):
    try:
        response = supabase.table("workouts").select("*").eq("student_id", student_id).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/workouts/{workout_id}")
def delete_workout(workout_id: str):
    try:
        response = supabase.table("workouts").delete().eq("id", workout_id).execute()
        return {"message": "Ficha de treino excluída com sucesso!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- ROTAS DE AVALIAÇÃO FÍSICA (MEDIDAS) ---
@app.post("/assessments")
def create_assessment(assessment: AssessmentCreate):
    try:
        response = supabase.table("assessments").insert(assessment.dict()).execute()
        return {"message": "Avaliação registrada com sucesso!", "data": response.data}
    except Exception as e:
        print("ERRO DETALHADO SUPABASE (POST):", str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/students/{student_id}/assessments")
def get_student_assessments(student_id: str):
    try:
        response = supabase.table("assessments").select("*").eq("student_id", student_id).execute()
        return response.data
    except Exception as e:
        print("ERRO DETALHADO SUPABASE (GET):", str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/assessments/{assessment_id}")
def update_assessment(assessment_id: str, assessment: AssessmentUpdate):
    try:
        response = supabase.table("assessments").update(assessment.dict()).eq("id", assessment_id).execute()
        return {"message": "Avaliação atualizada com sucesso!", "data": response.data}
    except Exception as e:
        print("ERRO DETALHADO SUPABASE (PUT):", str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/assessments/{assessment_id}")
def delete_assessment(assessment_id: str):
    try:
        response = supabase.table("assessments").delete().eq("id", assessment_id).execute()
        return {"message": "Avaliação excluída com sucesso!", "data": response.data}
    except Exception as e:
        print("ERRO DETALHADO SUPABASE (DELETE):", str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "ProEvolua API running"}