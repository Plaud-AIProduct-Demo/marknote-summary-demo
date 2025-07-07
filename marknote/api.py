import logging
import requests

def call_llm_api(prompt: str, image_url: str, model: str, api_key: str, api_url: str) -> str:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    if image_url is not None:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
        }
    else:
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    if image_url is None:
        payload["messages"][0]["content"] = str(prompt)
    logging.info(f"Payload for LLM API: {payload}")
    resp = requests.post(api_url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if "choices" in data and data["choices"]:
        return data["choices"][0]["message"]["content"]
    return str(data)
