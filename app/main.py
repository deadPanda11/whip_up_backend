from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from app.db.connection import check_db_connection

from app.api.email import app as email_router
from app.api.recipes import app as recipes_router
from app.api.users import app as users_router

origins = ['*']

app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(email_router)
app.include_router(recipes_router)
app.include_router(users_router)


@app.get("/check_db_connection")
def check_connection():
    return {"connection_status": check_db_connection()}
