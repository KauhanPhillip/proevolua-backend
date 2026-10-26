from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import date
from database import supabase

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])

class EvaluationCreate(BaseModel):
    student_id: str
    evaluation_date: Optional[date] = None
    weight: float  # Peso em kg
    height: float  # Altura em metros (ex: 1.75)
    age: int      # Idade (necessária para o cálculo de gordura)
    gender: str   # "M" ou "F"
    
    # Dobras cutâneas (mm)
    chest_fold: Optional[float] = None
    abdominal_fold: Optional[float] = None
    thigh_fold: Optional[float] = None
    triceps_fold: Optional[float] = None
    subscapular_fold: Optional[float] = None
    suprailiac_fold: Optional[float] = None
    midaxillary_fold: Optional[float] = None
    
    # Perímetros (cm)
    chest_perim: Optional[float] = None
    waist_perim: Optional[float] = None
    abdomen_perim: Optional[float] = None
    hips_perim: Optional[float] = None
    right_arm_perim: Optional[float] = None
    left_arm_perim: Optional[float] = None
    right_thigh_perim: Optional[float] = None
    left_thigh_perim: Optional[float] = None
    right_calf_perim: Optional[float] = None
    left_calf_perim: Optional[float] = None
    notes: Optional[str] = None

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_evaluation(evaluation: EvaluationCreate):
    try:
        data = evaluation.model_dump()
        
        # 1. Cálculo automático do IMC
        if evaluation.height > 0:
            bmi = evaluation.weight / (evaluation.height ** 2)
            data["bmi"] = round(bmi, 2)
        
        # 2. Cálculo automático do Percentual de Gordura (Jackson & Pollock - 3 dobras)
        body_fat = None
        sum_folds = 0
        
        if evaluation.gender.upper() == "M" and evaluation.chest_fold and evaluation.abdominal_fold and evaluation.thigh_fold:
            sum_folds = evaluation.chest_fold + evaluation.abdominal_fold + evaluation.thigh_fold
            body_density = 1.10938 - (0.0008267 * sum_folds) + (0.0000016 * (sum_folds ** 2)) - (0.0002574 * evaluation.age)
            body_fat = (495 / body_density) - 450
            
        elif evaluation.gender.upper() == "F" and evaluation.triceps_fold and evaluation.suprailiac_fold and evaluation.thigh_fold:
            sum_folds = evaluation.triceps_fold + evaluation.suprailiac_fold + evaluation.thigh_fold
            body_density = 1.0994921 - (0.0009929 * sum_folds) + (0.0000023 * (sum_folds ** 2)) - (0.0001392 * evaluation.age)
            body_fat = (495 / body_density) - 450

        if body_fat is not None:
            data["body_fat_percentage"] = round(body_fat, 2)
            
            # 3. Cálculo automático da Massa Gorda e Massa Magra (em kg)
            fat_mass = evaluation.weight * (body_fat / 100)
            lean_mass = evaluation.weight - fat_mass
            
            data["fat_mass_kg"] = round(fat_mass, 2)
            data["lean_mass_kg"] = round(lean_mass, 2)

        # Insere a avaliação na tabela 'evaluations' do Supabase
        response = supabase.table("evaluations").insert(data).execute()
        
        return {
            "message": "Avaliação física cadastrada e todas as métricas calculadas com sucesso!",
            "data": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/student/{student_id}")
def get_evaluations_by_student(student_id: str):
    try:
        response = supabase.table("evaluations").select("*").eq("student_id", student_id).order("evaluation_date", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))