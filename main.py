from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from professors import router as professors_router
from students import router as students_router
from evaluations import router as evaluations_router
from auth import router as auth_router  # <- Importar o router de auth

app = FastAPI(title="ProEvolua API", version="1.0")

# Configuração do CORS para o React conseguir comunicar com o FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Podes restringir para o URL do React depois (ex: http://localhost:5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir os routers
app.include_router(professors_router)
app.include_router(students_router)
app.include_router(evaluations_router)
app.include_router(auth_router)  # <- Registar a rota de auth

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API do ProEvolua!"}