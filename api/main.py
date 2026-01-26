# КРИТИЧНО: Применяем патчи для Python 3.14 ДО ЛЮБЫХ импортов FastAPI/Pydantic
import bot.patches  # noqa: F401

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from api.routes import webhooks, app as app_routes, admin as admin_routes, settings as settings_routes
from bot.services.supabase_client import get_supabase
from bot.config import settings
from aiogram import Bot
from datetime import datetime
from bot.tasks.sync import run_periodic_sync
import os
import logging
import asyncio
logger = logging.getLogger(__name__)



app = FastAPI(title="Cosmetology Loyalty API")

# Настройка CORS для доступа с телефона через ngrok
# ВАЖНО: allow_credentials=True несовместим с allow_origins=["*"]
# Для ngrok и Telegram Web App используем allow_origins=["*"] без credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все источники (для ngrok и Telegram)
    allow_credentials=False,  # Должно быть False при allow_origins=["*"]
    allow_methods=["*"],  # Разрешаем все методы
    allow_headers=["*"],  # Разрешаем все заголовки
    expose_headers=["*"],  # Разрешаем доступ ко всем заголовкам ответа
)

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request, call_next):
    # Логируем детальную информацию о запросе
    origin = request.headers.get("origin", "no-origin")
    user_agent = request.headers.get("user-agent", "no-ua")
    referer = request.headers.get("referer", "no-referer")
    client_host = request.client.host if request.client else "unknown"
    
    logger.info(f"Request: {request.method} {request.url.path}")
    logger.info(f"  From: {client_host}")
    logger.info(f"  Origin: {origin}")
    logger.info(f"  User-Agent: {user_agent[:100] if len(user_agent) > 100 else user_agent}")
    logger.info(f"  Referer: {referer}")
    logger.info(f"  Headers: {dict(request.headers)}")
    
    response = await call_next(request)
    
    # Добавляем CORS заголовки вручную для отладки
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    
    logger.info(f"Response: {response.status_code} for {request.url.path}")
    return response

# Раздача статических файлов для Mini App (РЕГИСТРИРУЕМ ПЕРВЫМ!)
webapp_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "webapp"))

if os.path.exists(webapp_path):
    # Регистрируем маршруты для webapp ПЕРЕД другими маршрутами
    @app.get("/webapp")
    @app.get("/webapp/")
    async def webapp_index():
        """Главная страница Mini App"""
        logger.info(f"WebApp request received. Path: {webapp_path}")
        index_path = os.path.join(webapp_path, "index.html")
        logger.info(f"Index path exists: {os.path.exists(index_path)}, path: {index_path}")
        if os.path.exists(index_path):
            logger.info("Returning index.html")
            return FileResponse(index_path, media_type="text/html")
        logger.error(f"WebApp index.html not found at {index_path}")
        return {"error": "WebApp index.html not found", "path": webapp_path}
    
    @app.get("/webapp/styles.css")
    async def webapp_css():
        css_path = os.path.join(webapp_path, "styles.css")
        if os.path.exists(css_path):
            return FileResponse(css_path, media_type="text/css")
        return {"error": "CSS not found"}
    
    @app.get("/webapp/script.js")
    async def webapp_js():
        js_path = os.path.join(webapp_path, "script.js")
        if os.path.exists(js_path):
            return FileResponse(js_path, media_type="application/javascript")
        return {"error": "JS not found"}
    
    # Монтируем статические файлы для остальных ресурсов
    app.mount("/webapp/assets", StaticFiles(directory=webapp_path), name="webapp-assets")
    
    # Раздача логотипа
    @app.get("/webapp/cveti.png")
    async def webapp_logo():
        """Логотип студии"""
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cveti.png")
        if os.path.exists(logo_path):
            return FileResponse(logo_path, media_type="image/png")
        return {"error": "Logo not found"}
    
    # Обработка favicon.ico (чтобы не было 404)
    @app.get("/favicon.ico")
    async def favicon():
        """Favicon для браузера"""
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cveti.png")
        if os.path.exists(logo_path):
            return FileResponse(logo_path, media_type="image/png")
        # Возвращаем пустой ответ вместо 404
        from fastapi.responses import Response
        return Response(status_code=204)
    
    # Страница регистрации для YCLIENTS
    @app.get("/yclients/register")
    async def yclients_register():
        """Страница регистрации для YCLIENTS интеграции"""
        register_path = os.path.join(webapp_path, "register.html")
        if os.path.exists(register_path):
            logger.info("Returning registration page")
            return FileResponse(register_path, media_type="text/html")
        logger.error(f"Registration page not found at {register_path}")
        return {"error": "Registration page not found", "path": register_path}

# Подключаем маршруты API (после webapp)
app.include_router(webhooks.router)
app.include_router(app_routes.router)
app.include_router(admin_routes.router)
app.include_router(settings_routes.router)

@app.get("/")
async def root():
    index_path = os.path.join(webapp_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "API is running", "version": "1.0.0"}

@app.get("/health")
async def health():
    """Health check endpoint для мониторинга"""
    try:
        # Проверяем подключение к БД
        supabase_client = get_supabase()
        await supabase_client.select("users", limit=1)
        db_status = "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "error"
    
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Глобальный Bot экземпляр для рассылок и уведомлений
_broadcast_bot: Bot = None

async def check_scheduled_broadcasts_periodically():
    """Периодически проверяет запланированные рассылки"""
    while True:
        try:
            await admin_routes.check_scheduled_broadcasts()
        except Exception as e:
            logger.error(f"Error in scheduled broadcasts check: {e}", exc_info=True)
        # Проверяем каждые 60 секунд
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    
    global _broadcast_bot
    try:
        # Создаем Bot экземпляр для рассылок
        _broadcast_bot = Bot(token=settings.BOT_TOKEN)
        # Устанавливаем Bot в модулях
        admin_routes.set_broadcast_bot(_broadcast_bot)
        webhooks.set_notification_bot(_broadcast_bot)
        logger.info("Broadcast bot initialized")
        
        # Запускаем периодическую проверку запланированных рассылок
        asyncio.create_task(check_scheduled_broadcasts_periodically())
        logger.info("Scheduled broadcasts checker started")
        
        # Запускаем периодическую синхронизацию с YClients
        asyncio.create_task(run_periodic_sync())
        logger.info("Periodic YClients sync task started")
        
    except Exception as e:
        logger.error(f"Error initializing broadcast bot: {e}", exc_info=True)
        

@app.on_event("shutdown")
async def shutdown_event():
    """Закрываем соединения при завершении приложения"""
    
    global _broadcast_bot
    try:
        # Закрываем Bot экземпляр
        if _broadcast_bot:
            await _broadcast_bot.session.close()
            logger.info("Broadcast bot closed")
            
    except Exception as e:
        logger.error(f"Error closing broadcast bot: {e}")
        
    
    try:
        supabase_client = get_supabase()
        await supabase_client.close()
        logger.info("Supabase client closed")
        
    except Exception as e:
        logger.error(f"Error closing Supabase client: {e}")
        
