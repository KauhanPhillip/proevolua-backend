from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import supabase

router = APIRouter()

class StudentCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    goal: Optional[str] = None
    professor_id: str  # Aceita como str para enviar UUID ou id como texto

@router.post("/students")
def create_student(student: StudentCreate):
    try:
        response = supabase.table("students").insert(student.dict()).execute()
        return {"message": "Aluno cadastrado com sucesso!", "data": response.data}
    except Exception as e:
        print("=== ERRO AO CADASTRAR ALUNO ===")
        print(e)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/professors/{professor_id}/students")
def list_professor_students(professor_id: str):
    try:
        # Busca da View do Supabase
        response = (
            supabase.table("students_with_last_assessment")
            .select("*")
            .eq("professor_id", professor_id)
            .execute()
        )
        
        # IMPRIME NO TERMINAL O QUE ESTÁ A SER ENVIADO
        print("=== ALUNOS RETORNADOS AO FRONTEND ===")
        for s in response.data:
            print(f"Aluno: {s.get('name')} | Última Avaliação: {s.get('last_assessment_date')}")

        return response.data

    except Exception as e:
        print("=== ERRO AO LISTAR ALUNOS ===")
        print(e)
        raise HTTPException(status_code=400, detail=str(e))