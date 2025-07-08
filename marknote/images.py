import os
import shutil
import base64
import boto3
from fastapi import UploadFile, File, APIRouter, Body
from fastapi.responses import JSONResponse
from marknote.api import call_llm_api
from marknote.config import get_aws_s3_config, get_llm_config
from marknote.prompt_template import IMAGE_PROMPT
from pydantic import BaseModel, Field

router = APIRouter()

class ImageSummaryRequest(BaseModel):
    image_url: str = Field(..., description="图片的URL地址")
    user_context: str = Field(None, description="可选，用户补充的图片分析目标或场景")
    language: str = Field(..., description="输出语言，如zh, en等")
    prompt: str = Field(None, description="可选，自选prompt")

@router.post("/image/summary")
def image_summary(request: ImageSummaryRequest):
    """
    接收图片URL、输出语言和可选上下文，通过大模型提取图片关键信息。
    """
    try:
        llm_cfg = get_llm_config("meeting")
        model = llm_cfg["model"]
        api_key = llm_cfg["api_key"]
        api_url = llm_cfg["api_url"]
        # 构造标准 prompt
        if request.prompt:
            prompt = request.prompt
        else:
            prompt = IMAGE_PROMPT
        if request.user_context is not None:
            prompt = prompt.replace("{{user_context}}", request.user_context or "")
        prompt = prompt.replace("{{language}}", request.language)
        summary = call_llm_api(prompt, [request.image_url], model, api_key, api_url)
        return {"summary": summary}
    except Exception as e:
        return {"error": f"图片内容提取失败: {str(e)}"}

def fetch_image_from_s3(s3_key: str) -> str:
    aws_cfg = get_aws_s3_config()
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=aws_cfg["aws_access_key_id"],
        aws_secret_access_key=aws_cfg["aws_secret_access_key"],
        region_name=aws_cfg["region_name"]
    )
    local_path = f"/tmp/{os.path.basename(s3_key)}"
    s3_client.download_file(aws_cfg["bucket"], s3_key, local_path)
    return local_path

def encode_image(image_path: str) -> str:
    """将图片文件编码为Base64字符串"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def upload_image(file: UploadFile = File(...)):
    """上传图片，保存到 images 目录，返回相对路径"""
    images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")
    os.makedirs(images_dir, exist_ok=True)
    file_ext = os.path.splitext(file.filename)[-1]
    save_name = file.filename
    save_path = os.path.join(images_dir, save_name)
    # 防止重名覆盖
    idx = 1
    while os.path.exists(save_path):
        save_name = f"{os.path.splitext(file.filename)[0]}_{idx}{file_ext}"
        save_path = os.path.join(images_dir, save_name)
        idx += 1
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    rel_path = f"images/{save_name}"
    return JSONResponse(content={"image_path": rel_path})

def image_path_to_base64(rel_path: str) -> str:
    """根据图片相对路径，将图片转为base64字符串"""
    abs_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), rel_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"图片文件不存在: {abs_path}")
    with open(abs_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

