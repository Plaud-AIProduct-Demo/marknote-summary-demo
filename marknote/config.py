import os
from .prompt_template import MEETING_SUMMARY_PROMPT_V3
from dotenv import load_dotenv

# 在模块加载时自动加载.env
load_dotenv()

def get_aws_s3_config():
    return {
        "bucket": os.getenv("S3_BUCKET", "your-bucket"),
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "region_name": os.getenv("AWS_REGION"),
    }

def get_llm_config(scenario: str):
    """
    根据 scenario 返回 LLM 的 api_url、model、api_key、prompt_template
    """
    api_url = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
    model = os.getenv("BASE_MODEL", "gpt-4o")
    api_key = os.getenv("MODEL_API_KEY", "")
    if scenario == "meeting":
        return {
            "api_url": api_url,
            "model": model,
            "api_key": api_key,
            "prompt_template": MEETING_SUMMARY_PROMPT_V3,
        }
    return {
        "api_url": api_url,
        "model": model,
        "api_key": api_key,
        "prompt_template": MEETING_SUMMARY_PROMPT_V3,
    }
