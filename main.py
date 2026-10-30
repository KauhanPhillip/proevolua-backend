import os
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
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

class GoogleLoginRequest(BaseModel):
    credential: str

class ProfessorUpdate(BaseModel):
    full_name: str
    birth_date: Optional[str] = None  # <--- Atualizado de age para birth_date
    phone: Optional[str] = None
    cref: Optional[str] = None
    specialty: Optional[str] = None

class StudentCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None  # <--- Atualizado de age para birth_date
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
    body_fat_kg: Optional[float] = None
    lean_mass: Optional[float] = None
    skeletal_muscle: Optional[float] = None
    total_body_water: Optional[float] = None
    visceral_fat: Optional[int] = None
    bone_mass: Optional[float] = None
    metabolic_age: Optional[int] = None
    chest: Optional[float] = None
    waist: Optional[float] = None
    arms: Optional[float] = None
    legs: Optional[float] = None

class AssessmentUpdate(BaseModel):
    weight: float
    height: Optional[float] = None
    body_fat: Optional[float] = None
    body_fat_kg: Optional[float] = None
    lean_mass: Optional[float] = None
    skeletal_muscle: Optional[float] = None
    total_body_water: Optional[float] = None
    visceral_fat: Optional[int] = None
    bone_mass: Optional[float] = None
    metabolic_age: Optional[int] = None
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

# --- ROTA DE LOGIN COM GOOGLE ---
@app.post("/auth/google")
def google_login(data: GoogleLoginRequest):
    try:
        info = id_token.verify_oauth2_token(
            data.credential,
            google_requests.Request(),
            os.environ.get("GOOGLE_CLIENT_ID"),
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Token do Google inválido")

    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="E-mail do Google não verificado")

    raw_email = info["email"]
    name = info.get("name") or "Professor"

    try:
        response = (
            supabase.table("professors")
            .select("*")
            .in_("email", [raw_email, raw_email.lower()])
            .execute()
        )

        if response.data:
            professor = response.data[0]
        else:
            created = supabase.table("professors").insert({
                "email": raw_email.lower(),
                "full_name": name,
                "password": secrets.token_urlsafe(32),
            }).execute()
            professor = created.data[0]

        return {
            "message": "Login realizado com sucesso!",
            "professor_id": professor["id"],
            "name": professor.get("full_name", name),
            "picture": info.get("picture"),
        }
    except Exception as e:
        print("ERRO NO LOGIN COM GOOGLE:", str(e))
        raise HTTPException(status_code=400, detail=str(e))

# --- ROTAS DO PERFIL DO PROFESSOR ---
PROFESSOR_PUBLIC_FIELDS = "id,full_name,email,birth_date,phone,cref,specialty,created_at"  # <--- Atualizado de age para birth_date

def _parse_dt(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None

@app.get("/professors/{professor_id}")
def get_professor(professor_id: int):
    try:
        response = (
            supabase.table("professors")
            .select(PROFESSOR_PUBLIC_FIELDS)
            .eq("id", professor_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Professor não encontrado")
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/professors/{professor_id}")
def update_professor(professor_id: int, professor: ProfessorUpdate):
    try:
        response = supabase.table("professors").update({
            "full_name": professor.full_name,
            "birth_date": professor.birth_date,  # <--- Atualizado de age para birth_date
            "phone": professor.phone,
            "cref": professor.cref,
            "specialty": professor.specialty,
        }).eq("id", professor_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Professor não encontrado")

        row = {k: v for k, v in response.data[0].items() if k != "password"}
        return {"message": "Perfil atualizado com sucesso!", "data": row}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/professors/{professor_id}/stats")
def get_professor_stats(professor_id: int):
    try:
        students = (
            supabase.table("students").select("*").eq("professor_id", professor_id).execute().data or []
        )
        ids = [s["id"] for s in students]

        workouts, assessments = [], []
        if ids:
            workouts = supabase.table("workouts").select("id").in_("student_id", ids).execute().data or []
            assessments = (
                supabase.table("assessments")
                .select("id,student_id,weight,created_at")
                .in_("student_id", ids)
                .execute()
                .data
                or []
            )

        names = {s["id"]: s.get("name") for s in students}
        epoch = datetime.min.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)

        last_by_student = {}
        for a in assessments:
            dt = _parse_dt(a.get("created_at"))
            if dt and dt > last_by_student.get(a["student_id"], epoch):
                last_by_student[a["student_id"]] = dt

        needs_reassessment = []
        for s in students:
            last = last_by_student.get(s["id"])
            days = (now - last).days if last else None
            if last is None or days >= 30:
                needs_reassessment.append({
                    "id": s["id"],
                    "name": s.get("name"),
                    "last_assessment": last.isoformat() if last else None,
                    "days": days,
                })
        needs_reassessment.sort(key=lambda x: (x["days"] is not None, -(x["days"] or 0)))

        recent_students = sorted(
            students, key=lambda s: _parse_dt(s.get("created_at")) or epoch, reverse=True
        )[:5]
        recent_assessments = sorted(
            assessments, key=lambda a: _parse_dt(a.get("created_at")) or epoch, reverse=True
        )[:5]

        return {
            "total_students": len(students),
            "total_workouts": len(workouts),
            "total_assessments": len(assessments),
            "students_without_goal": len([s for s in students if not (s.get("goal") or "").strip()]),
            "needs_reassessment": needs_reassessment,
            "recent_students": [
                {"id": s["id"], "name": s.get("name"), "goal": s.get("goal"), "created_at": s.get("created_at")}
                for s in recent_students
            ],
            "recent_assessments": [
                {
                    "id": a["id"],
                    "student_id": a["student_id"],
                    "student_name": names.get(a["student_id"]),
                    "weight": a.get("weight"),
                    "created_at": a.get("created_at"),
                }
                for a in recent_assessments
            ],
        }
    except Exception as e:
        print("ERRO NO RESUMO DO PROFESSOR:", str(e))
        raise HTTPException(status_code=400, detail=str(e))

# --- ROTAS DE ALUNOS ---
@app.post("/students")
def create_student(student: StudentCreate):
    try:
        data_to_insert = student.model_dump() if hasattr(student, 'model_dump') else student.dict()
        response = supabase.table("students").insert(data_to_insert).execute()
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
            "phone": student.phone,
            "birth_date": student.birth_date,  
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
        print("ERRO DETALHADO SUPABASE (PUT):", str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "ProEvolua API running"}