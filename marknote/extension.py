from fastapi import APIRouter
from pydantic import BaseModel, Field
from marknote.api import call_llm_api
from marknote.config import get_llm_config
from marknote.prompt_template import EXTENSION_PROMPT

router = APIRouter()

class ExtensionRequest(BaseModel):
    user_note: str = Field(..., description="用户笔记，需要扩写的内容")
    prompt: str = Field(None, description="自定义扩写提示词，可选")

@router.post("/mark_note/extension")
def extension(request: ExtensionRequest):
    try:
        llm_cfg = get_llm_config("meeting")
        model = llm_cfg["model"]
        api_key = llm_cfg["api_key"]
        api_url = llm_cfg["api_url"]
        if request.prompt:
            if "{{user_note}}" not in request.prompt:
                return {"error": "自定义prompt必须包含{{user_note}}占位符"}
            prompt = request.prompt
        else:
            prompt = EXTENSION_PROMPT
        replaced_prompt = prompt.replace("{{user_note}}", request.user_note)
        extended_text = call_llm_api(replaced_prompt, None, model, api_key, api_url)
        return {"extended_text": extended_text}
    except Exception as e:
        return {"error": f"扩写失败: {str(e)}"}
