# MarkNote Summary API

基于 FastAPI 的多模态会议内容总结服务，支持文本、图片、用户笔记输入，集成 LLM（如 OpenAI GPT-4），支持 S3 图片拉取、图片上传、日志、Swagger 文档、异常处理、配置分离、自动化测试等。

## 主要特性
- 多模态输入：支持会议文本、图片、用户笔记等多种信息源
- LLM 调用：支持多模型、多 API 地址配置，支持自定义 prompt
- S3 图片拉取与本地图片上传
- 日志分级与自动切分
- Swagger 文档（/swagger）
- 配置分离，敏感信息集中于 .env
- 自动化测试覆盖主要接口
- 结果自动存储至 MySQL

## 快速开始

### 1. 克隆项目
```bash
git clone <your-repo-url>
cd marknote-summary-demo
```

### 2. 安装依赖
建议使用 Python 3.12。
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
请复制 `.env.example` 为 `.env`，并根据实际情况填写：
- OpenAI/LLM API KEY、API URL、模型名
- MySQL 连接信息
- AWS S3 相关配置（如需图片拉取）

**注意：.env 文件包含敏感信息，请勿提交到 git 仓库。**

### 4. 初始化数据库
首次运行前请确保 MySQL 已启动，并执行：
```python
from database.mysql_client import init_db
init_db()
```
或直接运行服务，首次请求时会自动建表。

### 5. 启动服务
```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### 6. 访问接口文档
- Swagger: http://localhost:8080/swagger
- Redoc:   http://localhost:8080/redoc

## 主要接口

### 会议内容总结
`POST /mark_note/summary`
- 支持多模态输入，自动调用 LLM 生成摘要并存储到数据库
- 详见接口文档

### 全文+标注笔记总结
`POST /mark_note/full_text`
- 支持全文与多段标注笔记，自动分段并多级 LLM 汇总
- 支持自定义 prompt

### 图片上传
`POST /upload_image`
- 支持 multipart/form-data 上传图片，保存到 images 目录

## 目录结构
```
marknote-summary-demo/
├── main.py                # FastAPI 启动入口
├── marknote/
│   ├── api.py             # 主要业务接口
│   ├── full_text.py       # 全文+标注笔记接口
│   ├── images.py          # 图片处理相关
│   ├── config.py          # 配置加载
│   ├── prompt_template.py # Prompt 模板
│   └── ...
├── database/
│   └── mysql_client.py    # MySQL 连接与操作
├── images/                # 图片上传目录
├── static/                # 静态资源
├── logs/                  # 日志目录
├── .env                   # 环境变量配置（需手动创建）
├── requirements.txt       # 依赖
├── Dockerfile             # 容器化部署
└── README.md
```

## 注意事项
- `.env` 文件必须手动创建并正确配置，否则服务无法正常启动。
- 日志、图片、静态资源目录会自动创建。
- 建议使用 Docker 部署，详见 Dockerfile。

## License
MIT
