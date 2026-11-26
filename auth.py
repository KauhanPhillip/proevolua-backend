from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from database import supabase

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


def _ensure_professor_approved(professor: dict) -> None:
    approval_status = (professor.get("approval_status") or "pending").lower()

    if approval_status == "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seu cadastro aguarda aprovação do administrador.",
        )

    if approval_status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seu cadastro não foi aprovado. Entre em contato com o administrador.",
        )

    if approval_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado para esta conta.",
        )


@router.post("/login")
def login_professor(credentials: LoginSchema):
    try:
        response = (
            supabase.table("professors")
            .select("*")
            .eq("email", credentials.email)
            .execute()
        )

        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos.",
            )

        professor = response.data[0]

        if professor.get("password") != credentials.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos.",
            )

        _ensure_professor_approved(professor)

        return {
            "message": "Login efetuado com sucesso!",
            "professor": {
                "id": professor["id"],
                "full_name": professor["full_name"],
                "email": professor["email"],
                "cref": professor.get("cref"),
            },
        }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))