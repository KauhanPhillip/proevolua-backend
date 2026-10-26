from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from database import supabase

# É obrigatório ter esta exata variável 'router' definida:
router = APIRouter(prefix="/professors", tags=["Professors"])

class ProfessorCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    cref: Optional[str] = None

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_professor(professor: ProfessorCreate):
    try:
        response = supabase.table("professors").insert(professor.model_dump()).execute()
        return {"message": "Professor cadastrado com sucesso!", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{professor_id}")
def get_professor_by_id(professor_id: str):
    try:
        response = supabase.table("professors").select("*").eq("id", professor_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Professor não encontrado")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))