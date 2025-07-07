import logging
from fastapi import APIRouter
from pydantic import BaseModel, Field
from marknote.mark_note import call_llm_api
from marknote.config import get_llm_config
from typing import List
from marknote.prompt_template import SEGMENT_SUMMARY_PROMPT, MERGE_MARKNOTE_PROMPT, FINAL_MARKNOTE_PROMPT_V2
import concurrent.futures
import tiktoken

router = APIRouter()

TIKTOKEN_MODEL = "gpt-4o"

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
            summary_objects.append({
                "start_time": start,
                "end_time": end,
                "summary": line
            })
        summary_objects.sort(key=lambda x: x["start_time"])
        sorted_mark_notes = sorted(request.mark_notes, key=lambda x: x.start_time)
        # 合并所有与 mark_note 区间有重叠的 summary_object
        merged_list = []
        used = [False] * len(summary_objects)
        for note in sorted_mark_notes:
            merged_texts = []
            min_start, max_end = None, None
            for idx, so in enumerate(summary_objects):
                # 判断是否有重叠
                if so["end_time"] >= note.start_time and so["start_time"] <= note.end_time:
                    merged_texts.append(so["summary"])
                    used[idx] = True
                    # 计算区间并集
                    if min_start is None or so["start_time"] < min_start:
                        min_start = so["start_time"]
                    if max_end is None or so["end_time"] > max_end:
                        max_end = so["end_time"]
            if merged_texts:
                merged_list.append({
                    "note": note.content,
                    "merged_text": "\n".join(merged_texts),
                    "start_time": min_start if min_start is not None else note.start_time,
                    "end_time": max_end if max_end is not None else note.end_time
                })
        # 非 mark_note 区间的 summary_object 直接放入新列表
        for idx, so in enumerate(summary_objects):
            if not used[idx]:
                merged_list.append({
                    "note": None,
                    "merged_text": so["summary"],
                    "start_time": so["start_time"],
                    "end_time": so["end_time"]
                })
        # 保持顺序（按 start_time 排序）
        merged_list.sort(key=lambda x: x["start_time"] if x.get("start_time") is not None else 0)
        logging.info(f"Received {len(lines)} lines of full text for processing.")
        merged_list = merge_segments_by_token_count(merged_list)
        logging.info(f"Processed {len(merged_list)} merged segments from full text.")
        # 4. 多线程并发对合并后的内容执行 summary
        marknote_results = []
        def summarize_merged(item):
            if item["note"] is not None:
                # LLM summary for merged + marknote content
                replaced_prompt = MERGE_MARKNOTE_PROMPT.replace("{{meeting_summaries}}", item["merged_text"]).replace("{{key_note}}", item["note"])
                merged_summary = call_llm_api(replaced_prompt, None, model, api_key, api_url)
                return {
                    "summary": merged_summary
                }
            else:
                replaced_prompt = SEGMENT_SUMMARY_PROMPT.replace("{{meeting_summaries}}", item["merged_text"])
                merged_summary = call_llm_api(replaced_prompt, None, model, api_key, api_url)
                return {
                    "start_time": None,
                    "end_time": None,
                    "summary": merged_summary
                }
        with concurrent.futures.ThreadPoolExecutor() as executor:
            marknote_results = list(executor.map(summarize_merged, merged_list))
        prompt = None
        if request.prompt is None:
            prompt = FINAL_MARKNOTE_PROMPT_V2
        else:
            prompt = request.prompt
        # 5. 汇总所有 marknote_results，要求 LLM 输出中必须包含每个 mark_note 的内容，并在对应内容后加标记
        all_summaries = "\n".join([item["summary"] for item in marknote_results])
        # 构造标记说明
        mark_tags = []
        for note in request.mark_notes:
            tag = f'[#{{ "type": "mark", "value": {{"start_time":{note.start_time}, "end_time":{note.end_time}, "note_id": "{note.note_id}"}}}}#]'
            mark_tags.append({"content": note.content, "tag": tag})
        mark_tags_str = "\n".join([f'- {item["content"]} {item["tag"]}' for item in mark_tags])
        logging.info(f"mark_tags_str: {mark_tags_str}")
        final_prompt = prompt.replace("{{section_summaries}}", all_summaries).replace("{{mark_notes}}", mark_tags_str)
        final_summary = call_llm_api(final_prompt, None, model, api_key, api_url)
        return {
            "marknote_results": marknote_results,
            "final_summary": final_summary
        }
    except Exception as e:
        logging.error(f"Full text summary failed: {str(e)}")
        return {"error": f"Full text summary failed: {str(e)}"}

def merge_segments_by_token_count(merged_list, max_tokens=5000):
    """
    遍历 merged_list，累计 token 数，直到超过 max_tokens 时，将当前累计的片段合并为一个新片段。
    合并后 note 设为所有被合并的 note 的字符串合并（用换行拼接），如无 note 则为 None。
    merged_list 中的 item["note"] 已经是 string 或 None。
    使用 tiktoken 统计 token 数。
    """
    encoding = tiktoken.encoding_for_model(TIKTOKEN_MODEL)
    def count_tokens(text):
        return len(encoding.encode(text))

    result = []
    buffer = []
    notes = []
    token_sum = 0
    for item in merged_list:
        tokens = count_tokens(item["merged_text"])
        if token_sum + tokens > max_tokens and buffer:
            note_str = "\n".join([n for n in notes if n]) if notes else None
            result.append({
                "note": note_str,
                "merged_text": "\n".join(buffer)
            })
            buffer = []
            notes = []
            token_sum = 0
        buffer.append(item["merged_text"])
        if item["note"]:
            if isinstance(item["note"], list):
                notes.extend([n for n in item["note"] if n])
            else:
                notes.append(item["note"])
        token_sum += tokens
    if buffer:
        note_str = "\n".join([n for n in notes if n]) if notes else None
        result.append({
            "note": note_str,
            "merged_text": "\n".join(buffer)
        })
    return result
