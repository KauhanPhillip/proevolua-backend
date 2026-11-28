import os
import secrets
from datetime import datetime, timezone, timedelta, date
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
    age: Optional[int] = None
    phone: Optional[str] = None
    cref: Optional[str] = None
    specialty: Optional[str] = None

class StudentCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
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


# --- MODELOS DE MENSALIDADES ---
class PlanCreate(BaseModel):
    name: str
    price: float
    duration_days: int
    active: bool = True

class SubscriptionUpsert(BaseModel):
    plan_id: Optional[str] = None
    plan_name: str
    price: float
    duration_days: int
    due_date: str  # AAAA-MM-DD
    active: bool = True

class PaymentCreate(BaseModel):
    amount: float
    paid_at: Optional[str] = None  # AAAA-MM-DD (padrão: hoje)
    method: Optional[str] = None
    notes: Optional[str] = None

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
    # 1) Valida o token direto com o Google (ninguém consegue falsificar o e-mail pelo front)
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

    # 2) Procura o professor pelo e-mail; se não existir, cria automaticamente
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
                "password": secrets.token_urlsafe(32),  # senha aleatória, ninguém digita
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
# Nunca devolvemos a senha: só estes campos são selecionados
PROFESSOR_PUBLIC_FIELDS = "id,full_name,email,age,phone,cref,specialty,created_at"

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
            "age": professor.age,
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

        # Data da última avaliação de cada aluno
        last_by_student = {}
        for a in assessments:
            dt = _parse_dt(a.get("created_at"))
            if dt and dt > last_by_student.get(a["student_id"], epoch):
                last_by_student[a["student_id"]] = dt

        # Alunos nunca avaliados ou sem avaliação há 30 dias ou mais
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
        # Nunca avaliados primeiro; depois os mais antigos
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
            "phone": student.phone,
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

# --- ROTAS DE MENSALIDADES ---
def _parse_date(value, field="data"):
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"{field} inválida (use AAAA-MM-DD)")

# Planos
@app.get("/professors/{professor_id}/plans")
def list_plans(professor_id: int):
    try:
        response = (
            supabase.table("plans").select("*").eq("professor_id", professor_id)
            .order("created_at").execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/professors/{professor_id}/plans")
def create_plan(professor_id: int, plan: PlanCreate):
    if plan.price < 0 or plan.duration_days < 1:
        raise HTTPException(status_code=400, detail="Valor e duração inválidos")
    try:
        response = supabase.table("plans").insert({
            "professor_id": professor_id,
            "name": plan.name.strip(),
            "price": plan.price,
            "duration_days": plan.duration_days,
            "active": plan.active,
        }).execute()
        return {"message": "Plano criado com sucesso!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/plans/{plan_id}")
def update_plan(plan_id: str, plan: PlanCreate):
    if plan.price < 0 or plan.duration_days < 1:
        raise HTTPException(status_code=400, detail="Valor e duração inválidos")
    try:
        response = supabase.table("plans").update({
            "name": plan.name.strip(),
            "price": plan.price,
            "duration_days": plan.duration_days,
            "active": plan.active,
        }).eq("id", plan_id).execute()
        return {"message": "Plano atualizado com sucesso!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/plans/{plan_id}")
def delete_plan(plan_id: str):
    try:
        response = supabase.table("plans").delete().eq("id", plan_id).execute()
        return {"message": "Plano excluído com sucesso!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Painel de mensalidades: assinaturas + pagamentos do professor.
# O status (pago / a vencer / vencida) é calculado no front, com a data do navegador.
@app.get("/professors/{professor_id}/billing")
def get_billing(professor_id: int):
    try:
        students = (
            supabase.table("students").select("id").eq("professor_id", professor_id).execute().data or []
        )
        ids = [s["id"] for s in students]
        if not ids:
            return {"subscriptions": [], "payments": []}

        subscriptions = supabase.table("subscriptions").select("*").in_("student_id", ids).execute().data or []
        payments = (
            supabase.table("payments").select("*").in_("student_id", ids)
            .order("paid_at", desc=True).execute().data or []
        )
        return {"subscriptions": subscriptions, "payments": payments}
    except Exception as e:
        print("ERRO NAS MENSALIDADES:", str(e))
        raise HTTPException(status_code=400, detail=str(e))

# Assinatura do aluno (uma por aluno): cria ou atualiza
@app.put("/students/{student_id}/subscription")
def upsert_subscription(student_id: str, sub: SubscriptionUpsert):
    if sub.price < 0 or sub.duration_days < 1:
        raise HTTPException(status_code=400, detail="Valor e duração inválidos")
    due = _parse_date(sub.due_date, "Vencimento")
    try:
        payload = {
            "student_id": student_id,
            "plan_id": sub.plan_id or None,
            "plan_name": sub.plan_name,
            "price": sub.price,
            "duration_days": sub.duration_days,
            "due_date": due.isoformat(),
            "active": sub.active,
        }
        existing = supabase.table("subscriptions").select("id").eq("student_id", student_id).execute().data
        if existing:
            response = supabase.table("subscriptions").update(payload).eq("student_id", student_id).execute()
        else:
            response = supabase.table("subscriptions").insert(payload).execute()
        return {"message": "Mensalidade salva com sucesso!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/students/{student_id}/subscription")
def delete_subscription(student_id: str):
    try:
        response = supabase.table("subscriptions").delete().eq("student_id", student_id).execute()
        return {"message": "Mensalidade removida com sucesso!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Pagamentos
@app.get("/students/{student_id}/payments")
def list_student_payments(student_id: str):
    try:
        response = (
            supabase.table("payments").select("*").eq("student_id", student_id)
            .order("paid_at", desc=True).execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Registra o pagamento (valor inteiro) e avança o vencimento pela duração do plano
@app.post("/students/{student_id}/payments")
def create_payment(student_id: str, payment: PaymentCreate):
    try:
        subs = supabase.table("subscriptions").select("*").eq("student_id", student_id).execute().data
        if not subs:
            raise HTTPException(status_code=400, detail="Este aluno ainda não tem mensalidade cadastrada")
        sub = subs[0]

        paid_at = _parse_date(payment.paid_at, "Data do pagamento") if payment.paid_at else date.today()
        due_before = _parse_date(sub["due_date"])
        due_after = due_before + timedelta(days=int(sub["duration_days"]))

        created = supabase.table("payments").insert({
            "student_id": student_id,
            "subscription_id": sub["id"],
            "plan_name": sub.get("plan_name"),
            "amount": payment.amount,
            "paid_at": paid_at.isoformat(),
            "method": payment.method,
            "notes": payment.notes,
            "due_before": due_before.isoformat(),
            "due_after": due_after.isoformat(),
        }).execute()

        supabase.table("subscriptions").update({"due_date": due_after.isoformat()}).eq("id", sub["id"]).execute()
        return {"message": "Pagamento registrado com sucesso!", "data": created.data}
    except HTTPException:
        raise
    except Exception as e:
        print("ERRO AO REGISTRAR PAGAMENTO:", str(e))
        raise HTTPException(status_code=400, detail=str(e))

# Desfaz um pagamento lançado por engano e devolve o vencimento anterior
@app.delete("/payments/{payment_id}")
def delete_payment(payment_id: str):
    try:
        found = supabase.table("payments").select("*").eq("id", payment_id).execute().data
        if not found:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado")
        pay = found[0]

        subs = supabase.table("subscriptions").select("*").eq("student_id", pay["student_id"]).execute().data
        if subs and pay.get("due_before") and pay.get("due_after"):
            # só devolve o vencimento se ele ainda é o que esse pagamento gerou
            if str(subs[0]["due_date"])[:10] == str(pay["due_after"])[:10]:
                supabase.table("subscriptions").update(
                    {"due_date": str(pay["due_before"])[:10]}
                ).eq("id", subs[0]["id"]).execute()

        supabase.table("payments").delete().eq("id", payment_id).execute()
        return {"message": "Pagamento desfeito com sucesso!"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "ProEvolua API running"}