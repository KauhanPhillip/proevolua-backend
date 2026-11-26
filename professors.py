from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from database import supabase

router = APIRouter(prefix="/professors", tags=["Professors"])


class ProfessorCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    birth_date: Optional[str] = None
    age: Optional[int] = None
    phone: Optional[str] = None
    cref: Optional[str] = None
    specialty: Optional[str] = None


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_professor(professor: ProfessorCreate):
    try:
        payload = professor.model_dump(exclude_none=True)
        payload["email"] = payload["email"].strip().lower()
        payload["approval_status"] = "pending"
        payload["approved_at"] = None

        response = supabase.table("professors").insert(payload).execute()
        return {
            "message": "Cadastro enviado! Aguarde a aprovação do administrador.",
            "data": response.data,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{professor_id}")
def get_professor_by_id(professor_id: str):
    try:
        response = (
            supabase.table("professors")
            .select("*")
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