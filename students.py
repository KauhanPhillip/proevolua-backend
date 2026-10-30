from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date  
from database import supabase

router = APIRouter()

class StudentCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None  
    goal: Optional[str] = None
    professor_id: str

@router.post("/students")
def create_student(student: StudentCreate):
    try:
        data_to_insert = student.model_dump() if hasattr(student, 'model_dump') else student.dict()
        
        if data_to_insert.get("birth_date"):
            data_to_insert["birth_date"] = str(data_to_insert["birth_date"])

        response = supabase.table("students").insert(data_to_insert).execute()
        return {"message": "Aluno cadastrado com sucesso!", "data": response.data}
    except Exception as e:
        print("=== ERRO AO CADASTRAR ALUNO ===")
        print(e)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/professors/{professor_id}/students")
def list_professor_students(professor_id: str):
    try:
        response = (
            supabase.table("students_with_last_assessment")
            .select("*")
            .eq("professor_id", professor_id)
            .execute()
        )
        return response.data
    except Exception as e:
        print("=== ERRO AO LISTAR ALUNOS ===")
        print(e)
        raise HTTPException(status_code=400, detail=str(e))