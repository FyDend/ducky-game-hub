from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from services.catalog_service import migrate_json_to_sqlite
from routers import catalog, downloads, system, emulator, gamepad

app = FastAPI(title="Ducky Game Hub Bridge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.include_router(catalog.router)
app.include_router(downloads.router)
app.include_router(system.router)
app.include_router(emulator.router)
app.include_router(gamepad.router)

# Montar store_front estático
app.mount("/store_front", StaticFiles(directory="/app/store_front"), name="store_front")

@app.on_event("startup")
def startup_event():
    migrate_json_to_sqlite()