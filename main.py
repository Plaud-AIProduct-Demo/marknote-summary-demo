import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime
from fastapi import FastAPI
from marknote.api import router as marknote_router
from marknote.full_text import router as full_text_router
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


# 日志配置
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)
log_time = datetime.now().strftime("%Y%m%d%H")
log_file = os.path.join(log_dir, f"marknote-{log_time}.log")

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(log_file, when="H", interval=1, backupCount=168, encoding="utf-8")
formatter = logging.Formatter("[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)
else:
    logger.handlers.clear()
    logger.addHandler(handler)

app = FastAPI(
    title="MarkNote Summary API",
    description="MarkNote 项目 API 文档，支持会议内容、图片、笔记等多模态总结能力。",
    version="1.0.0",
    docs_url="/swagger",
    redoc_url="/redoc"
)
app.include_router(marknote_router)
app.include_router(full_text_router)

@app.get("/")
def read_root():
    logging.info("Root endpoint accessed.")
    return {"message": "Hello, FastAPI with MarkNote!"}

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/favicon.ico")
def favicon():
    return FileResponse("static/favicon.ico")

if __name__ == "__main__":
    import uvicorn
    logging.info("Starting FastAPI app on 0.0.0.0:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)
