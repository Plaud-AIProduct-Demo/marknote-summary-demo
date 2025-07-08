import logging
from fastapi import APIRouter
from pydantic import BaseModel, Field
from enum import Enum
import requests
from marknote.config import get_llm_config
from marknote.database.mysql_client import insert_mark_note_summary
from marknote.api import call_llm_api

router = APIRouter()

class Scenario(str, Enum):
    meeting = "meeting"

class MarkType(str, Enum):
    time = "time"
    text = "text"
    image = "image"

class MarkNoteSummaryRequest(BaseModel):
    summary_id: str = Field(..., description="摘要ID")
    scenario: Scenario = Field(..., description="场景，如meeting")
    language: str = Field(..., description="语言，如chinese, english等")
    mark_time: int = Field(..., description="标记时间")
    time_range: int = Field(..., description="时间范围")
    content: str = Field(..., description="转写内容")
    prompt: str = Field(None, description="自定义提示内容, 可选")
    mark_type: MarkType = Field(..., description="标记类型: time, text, image")
    image_url: list = Field(None, description="图片的地址列表, 仅image类型需要")
    notes: str = Field(None, description="用户笔记内容, 仅text类型需要")

def parse_meeting_content(mark_time: int, time_range: int, content: str) -> str:
    """解析会议内容，返回窗口内的文本"""
    parsed_lines = []
    for line in content.strip().split('\n'):
        if not line:
            continue
        time_start = line.find('[')
        time_end = line.find(']', time_start)
        speaker_start = line.find('[', time_end + 1)
        speaker_end = line.find(']', speaker_start)
        if -1 in (time_start, time_end, speaker_start, speaker_end):
            continue
        time_text = line[time_start+1:time_end]
        speaker = line[speaker_start+1:speaker_end]
        text_content = line[speaker_end+1:].strip()
        try:
            start, end = map(int, time_text.split('-'))
        except ValueError:
            continue
        parsed_lines.append({
            "start": start,
            "end": end,
            "speaker": speaker,
            "content": text_content
        })
    window_start = mark_time - time_range
    window_end = mark_time + time_range
    window_results = [f"{line['speaker']}: {line['content']}" for line in parsed_lines if line["end"] >= window_start and line["start"] <= window_end]
    return window_start, window_end, "\n".join(window_results)

def build_prompt(llm_cfg, prompt, meeting_content, language, image_content=None, user_notes=None):
    logging.info(f"image_content: {image_content}, user_notes: {user_notes}")
    if prompt is None:
        prompt = llm_cfg["prompt_template"]
    if image_content is None:
        image_content = []
    if user_notes is None:
        user_notes = ""
    if "{{meeting_content}}" not in prompt or "{{language}}" not in prompt:
        logging.error("Prompt template must contain {{meeting_content}} and {{language}} placeholders")
        raise ValueError("Prompt template must contain {{meeting_content}} and {{language}} placeholders")
    format_prompt = prompt.replace("{{meeting_content}}", meeting_content).replace("{{language}}", language)
    format_prompt = format_prompt.replace("{{user_notes}}", user_notes)
    # format_prompt = format_prompt.replace("{{image_content}}", ", ".join(image_content) if image_content else "")
    return format_prompt

@router.post("/mark_note/summary")
def mark_note_summary(request: MarkNoteSummaryRequest):
    import logging
    try:
        llm_cfg = get_llm_config(request.scenario)
        api_url = llm_cfg["api_url"]
        model = llm_cfg["model"]
        api_key = llm_cfg["api_key"]
        user_notes = None
        image_url = None
        if request.mark_type == MarkType.image:
            if not request.image_url or not isinstance(request.image_url, list):
                logging.error("image type must provide image_url as a list")
                return {"error": "image type must provide image_url as a list"}
            image_url = request.image_url
        elif request.mark_type == MarkType.text:
            user_notes = request.notes
        # try:
            # window_start, window_end, meeting_content = parse_meeting_content(request.mark_time, request.time_range, request.content)
        # except Exception as e:
        #     logging.error(f"Meeting content parsing failed: {str(e)}")
        #     return {"error": f"Meeting content parsing failed: {str(e)}"}
        try:
            format_prompt = build_prompt(
                llm_cfg,
                request.prompt,
                request.content,
                request.language,
                image_content=image_url,
                user_notes=user_notes
            )
        except Exception as e:
            logging.error(f"Prompt build failed: {str(e)}")
            return {"error": f"Prompt build failed: {str(e)}"}
        try:
            logging.info(f"Calling LLM API: {api_url} with model: {model}")
            logging.info(f"Prompt content: {format_prompt}")
            llm_response = call_llm_api(format_prompt, image_url, model, api_key, api_url)
            logging.info(f"LLM API response: {llm_response}")
        except requests.RequestException as e:
            logging.error(f"LLM API request failed: {str(e)}")
            return {"error": f"LLM API request failed: {str(e)}"}
        except Exception as e:
            logging.error(f"LLM API call exception: {str(e)}")
            return {"error": f"LLM API call exception: {str(e)}"}
        # 存储到MySQL
        try:
            insert_mark_note_summary({
                "summary_id": request.summary_id,
                "scenario": request.scenario.value,
                "language": request.language,
                "mark_time": request.mark_time,
                "time_range": request.time_range,
                "content": request.content,
                "prompt": format_prompt,
                "mark_type": request.mark_type.value,
                "image_url": ",".join(image_url) if image_url else None,
                "user_notes": user_notes,
                "mark_note": llm_response,
                # "start_time": window_start,
                # "end_time": window_end
            })
        except Exception as e:
            logging.error(f"Failed to insert summary to MySQL: {str(e)}")
        result = {
            "received": request.model_dump(),
            "llm_summary": llm_response,
            # "start_time": window_start,
            # "end_time": window_end,
        }
        callback_url = "http://127.0.0.1:8080/mark_note/callback"
        callback_data = {
            "summary_id": request.summary_id,
            "mark_time": request.mark_time
        }
        try:
            requests.post(callback_url, json=callback_data, timeout=3)
        except Exception as e:
            logging.error(f"Callback failed: {str(e)}")
            result["callback_error"] = f"Callback failed: {str(e)}"
        return result
    except Exception as e:
        logging.error(f"Internal server error: {str(e)}")
        return {"error": f"Internal server error: {str(e)}"}


