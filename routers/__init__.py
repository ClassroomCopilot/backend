from .database.admin import router as admin_router

def include_routers(app):
    app.include_router(admin_router, prefix="/admin", tags=["admin"])
