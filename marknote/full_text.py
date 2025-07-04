import logging
from fastapi import APIRouter
from pydantic import BaseModel, Field
from marknote.api import call_llm_api
from marknote.config import get_llm_config
from typing import List
from marknote.prompt_template import SEGMENT_SUMMARY_PROMPT, MERGE_MARKNOTE_PROMPT, FINAL_MARKNOTE_PROMPT
import concurrent.futures

router = APIRouter()

class MarkNoteItem(BaseModel):
    start_time: int = Field(..., description="开始时间")
    end_time: int = Field(..., description="结束时间")
    content: str = Field(..., description="内容")
    note_id: str = Field(..., description="note_id")

class FullTextRequest(BaseModel):
    prompt: str = Field(None, description="自定义提示内容, 可选")
    full_text: str = Field(..., description="完整文本")
    mark_notes: List[MarkNoteItem] = Field(..., description="标注笔记列表")

@router.post("/mark_note/full_text")
def mark_note_full_text(request: FullTextRequest):
    try:
        # 1. 切分 full_text 为片段
        lines = [line for line in request.full_text.strip().split('\n') if line]
        llm_cfg = get_llm_config("meeting")
        model = llm_cfg["model"]
        api_key = llm_cfg["api_key"]
        api_url = llm_cfg["api_url"]
        summary_objects = []
        # 2. 对每个片段用 LLM 进行 summary
        for line in lines:
            # 解析时间戳
            time_start = line.find('[')
            time_end = line.find(']', time_start)
            speaker_start = line.find('[', time_end + 1)
            speaker_end = line.find(']', speaker_start)
            if -1 in (time_start, time_end, speaker_start, speaker_end):
                continue
            time_text = line[time_start+1:time_end]
            try:
                start, end = map(int, time_text.split('-'))
            except ValueError:
                continue
            text_content = line[speaker_end+1:].strip()
            # LLM summary for this segment
            # prompt = SEGMENT_SUMMARY_PROMPT.replace("{{segment}}", text_content)
            # segment_summary = call_llm_api(prompt, None, model, api_key, api_url)
            summary_objects.append({
                "start_time": start,
                "end_time": end,
                "summary": text_content
            })
        # 3. 遍历 mark_notes，合并 summary_object 区间内容，不执行summary
        marknote_merge_inputs = []
        for note in request.mark_notes:
            merged_summaries = [obj["summary"] for obj in summary_objects if obj["start_time"] >= note.start_time and obj["end_time"] <= note.end_time]
            merged_text = "\n".join(merged_summaries)
            marknote_merge_inputs.append({
                "note": note,
                "merged_text": merged_text
            })
        prompt = None
        if request.prompt is None:
            prompt = MERGE_MARKNOTE_PROMPT
        # 4. 多线程并发对合并后的内容执行 summary
        marknote_results = []
        def summarize_merged(item):
            # LLM summary for merged + marknote content
            replaced_prompt = prompt.replace("{{meeting_summaries}}", item["merged_text"]).replace("{{key_note}}", item["note"].content)
            merged_summary = call_llm_api(replaced_prompt, None, model, api_key, api_url)
            return {
                "start_time": item["note"].start_time,
                "end_time": item["note"].end_time,
                "summary": merged_summary
            }
        with concurrent.futures.ThreadPoolExecutor() as executor:
            marknote_results = list(executor.map(summarize_merged, marknote_merge_inputs))
        # 5. 汇总所有 marknote_results，要求 LLM 输出中必须包含每个 mark_note 的内容，并在对应内容后加标记
        all_summaries = "\n".join([item["summary"] for item in marknote_results])
        # 构造标记说明
        mark_tags = []
        for note in request.mark_notes:
            tag = f'[#{{ "type": "mark", "value": {{"start_time":{note.start_time}, "end_time":{note.end_time}, "note_id": "{note.note_id}"}}}}#]'
            mark_tags.append({"content": note.content, "tag": tag})
        # 构造 LLM prompt，要求每个 mark_note 的内容必须在最终 summary 中出现，并在其后加上唯一标记
        mark_tags_str = "\n".join([f'- {item["content"]} {item["tag"]}' for item in mark_tags])
        final_prompt = FINAL_MARKNOTE_PROMPT.replace("{{section_summaries}}", all_summaries).replace("{{mark_tags}}", mark_tags_str)
        final_summary = call_llm_api(final_prompt, None, model, api_key, api_url)
        return {
            "marknote_results": marknote_results,
            "final_summary": final_summary
        }
    except Exception as e:
        logging.error(f"Full text summary failed: {str(e)}")
        return {"error": f"Full text summary failed: {str(e)}"}
