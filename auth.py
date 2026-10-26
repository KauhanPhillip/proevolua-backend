from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from database import supabase

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

@router.post("/login")
def login_professor(credentials: LoginSchema):
    try:
        # Procura o professor pelo email na tabela 'professors'
        response = supabase.table("professors").select("*").eq("email", credentials.email).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos."
            )
        
        professor = response.data[0]
        
        # Valida se a senha corresponde à guardada na base de dados
        if professor.get("password") != credentials.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos."
            )
        
        # Sucesso: Retorna os dados do professor para o React guardar na sessão
        return {
            "message": "Login efetuado com sucesso!",
            "professor": {
                "id": professor["id"],
                "full_name": professor["full_name"],
                "email": professor["email"],
                "cref": professor.get("cref")
            }
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))