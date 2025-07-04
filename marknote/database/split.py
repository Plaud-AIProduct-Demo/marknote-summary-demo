import re
from typing import List
import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

MODEL_PREFIX_TO_MODEL = {
    "gpt4-turbo": "gpt-4",
    "gpt4o": "gpt-4o",
}

def count_tokens(text: str, model_name: str = 'gpt-4o') -> int:
    """统计文本的token数，自动适配模型。"""
    token_model_name = model_name
    for model_prefix, model in MODEL_PREFIX_TO_MODEL.items():
        if token_model_name.startswith(model_prefix):
            token_model_name = model
            break
    token_enc = tiktoken.encoding_for_model(token_model_name)
    tokens = token_enc.encode(text)
    return len(tokens)

def split_text_by_tokens(text: str, max_tokens: int = 5000, model_name: str = 'gpt-4o') -> List[str]:
    """
    按最大token数切分文本，返回分段列表。
    """
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        model_name=model_name,
        chunk_size=max_tokens,
        chunk_overlap=0,
    )
    return splitter.split_text(text)
