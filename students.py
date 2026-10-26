from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date
from database import supabase

router = APIRouter(prefix="/students", tags=["Students"])

class StudentCreate(BaseModel):
    professor_id: str
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None  # "M" ou "F"
    registration: int  # Número de matrícula obrigatório e único

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_student(student: StudentCreate):
    try:
        data = student.model_dump()
        
        # Converte a data para string caso exista, para o Supabase aceitar corretamente
        if student.birth_date:
            data["birth_date"] = student.birth_date.isoformat()

        response = supabase.table("students").insert(data).execute()
        
        return {
            "message": "Aluno cadastrado com sucesso!",
            "data": response.data
        }
    except Exception as e:
        # Se tentarem registar um número de matrícula duplicado, o Supabase vai disparar um erro que apanhamos aqui
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{professor_id}")
def get_students_by_professor(professor_id: str):
    try:
        response = supabase.table("students").select("*").eq("professor_id", professor_id).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))