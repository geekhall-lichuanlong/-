# LangChain Geo Firecrawl Agent

一个基于 LangChain 的单智能体多 MCP 服务集成示例。项目在同一个 Agent 中集成高德地图 MCP 与 Firecrawl MCP，支持多轮对话、路径规划、POI 查询、天气查询、网页抓取、网页搜索、结构化抽取，并提供 Web UI、CLI 和 FastAPI 接口。

## 功能特性

- 单 Agent 统一调度多个 MCP 服务
- 高德地图 MCP：地理编码、逆地理编码、POI 检索、周边搜索、驾车/公交/步行/骑行路线、天气等
- Firecrawl MCP：网页搜索、网页抓取、站点爬取、结构化信息抽取
- 多轮对话记忆：基于 LangGraph checkpointer，通过 `thread_id` 保留上下文
- 流式输出：Web 页面通过 SSE 实时显示模型回答
- 结构化输出：可返回地点、路线、网页来源、建议动作和数据限制
- 三种使用方式：Web UI、命令行 CLI、HTTP API
- 默认使用 DeepSeek `deepseek-chat`，也可切换 LangChain 支持的其他模型

## 技术栈

- Python 3.11+
- LangChain
- LangGraph
- langchain-mcp-adapters
- FastAPI
- DeepSeek Chat Model
- AMap MCP Server
- Firecrawl MCP Server
- HTML/CSS/JavaScript

## 项目结构

```text
langchain_geo_firecrawl_agent/
├── pyproject.toml
├── README.md
├── .env.example
├── src/
│   └── geo_firecrawl_agent/
│       ├── agent.py              # LangChain Agent 与流式事件封装
│       ├── api.py                # FastAPI、SSE、静态页面路由
│       ├── cli.py                # 命令行入口
│       ├── config.py             # 环境变量配置
│       ├── mcp_config.py         # 高德与 Firecrawl MCP 连接配置
│       ├── model_factory.py      # 模型初始化，默认 DeepSeek
│       ├── schemas.py            # API 与结构化输出 schema
│       └── static/
│           ├── index.html
│           ├── styles.css
│           └── app.js
└── tests/
    └── test_mcp_config.py
```

## 前置条件

需要安装：

- Python 3.11 或更高版本
- Node.js 18 或更高版本，推荐 22+
- DeepSeek API Key
- 高德开放平台 Web 服务 Key
- Firecrawl API Key

高德 Key 需要选择服务平台为 `Web 服务`。

## 安装

Windows PowerShell：

```powershell
cd langchain_geo_firecrawl_agent
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[deepseek]"
Copy-Item .env.example .env
```

macOS / Linux：

```bash
cd langchain_geo_firecrawl_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[deepseek]"
cp .env.example .env
```

## 环境变量

编辑 `.env`：

```text
AGENT_MODEL=deepseek:deepseek-chat
DEEPSEEK_API_KEY=your_deepseek_api_key

ENABLE_AMAP=true
AMAP_TRANSPORT=http
AMAP_MAPS_API_KEY=your_amap_web_service_key
AMAP_MCP_URL=

ENABLE_FIRECRAWL=true
FIRECRAWL_TRANSPORT=stdio
FIRECRAWL_API_KEY=your_firecrawl_api_key
FIRECRAWL_MCP_URL=http://localhost:3000/mcp

DEFAULT_THREAD_ID=demo
```

注意：不要提交 `.env` 文件到 Git。仓库里只保留 `.env.example`。

## 启动 Web UI

```powershell
uvicorn geo_firecrawl_agent.api:app --host 127.0.0.1 --port 8000
```

打开浏览器：

```text
http://127.0.0.1:8000
```

页面能力：

- 输入自然语言问题
- 实时流式显示回答
- 设置或新建 `thread_id`
- 清空当前线程记忆
- 开关结构化输出
- 查看本轮调用的 MCP 工具
- 查看结构化 JSON 结果

示例问题：

```text
我从上海虹桥站去外滩，帮我规划地铁和驾车方案，并搜索网页整理外滩开放时间和游玩注意事项。
```

## CLI 使用

普通对话：

```powershell
geo-firecrawl-chat --thread-id travel-demo
```

结构化输出：

```powershell
geo-firecrawl-chat --thread-id travel-demo --structured
```

## HTTP API

### 健康检查

```http
GET /health
```

### 工具列表

```http
GET /tools
```

### 普通对话

```http
POST /chat
Content-Type: application/json

{
  "message": "查一下杭州西湖附近适合亲子的 POI，并抓取网页整理门票和开放时间",
  "thread_id": "u1",
  "structured": true
}
```

### 流式对话

```http
POST /chat/stream
Content-Type: application/json

{
  "message": "我从上海虹桥站去外滩，帮我规划路线",
  "thread_id": "u1",
  "structured": true
}
```

返回格式为 Server-Sent Events：

```text
event: meta
data: {"thread_id":"u1"}

event: token
data: {"type":"token","text":"你好"}

event: tool_start
data: {"type":"tool_start","name":"maps_direction_driving"}

event: final
data: {"type":"final","answer":"...","tool_calls":["..."],"structured_response":{...}}
```

### 清空线程记忆

```http
POST /threads/clear
Content-Type: application/json

{
  "thread_id": "u1"
}
```

## PowerShell API 示例

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/chat `
  -ContentType application/json `
  -Body '{"message":"查一下杭州西湖附近适合亲子的 POI，并抓取网页整理门票和开放时间","thread_id":"u1","structured":true}'
```

## MCP 配置说明

默认配置中：

- 高德 MCP 使用 HTTP Streamable 方式
- Firecrawl MCP 使用 stdio 方式，由 `npx -y firecrawl-mcp` 启动

高德默认 URL：

```text
https://mcp.amap.com/mcp?key=<AMAP_MAPS_API_KEY>
```

Firecrawl stdio：

```powershell
npx -y firecrawl-mcp
```

如果你想改用 Firecrawl HTTP 模式，需要先单独启动 Firecrawl MCP：

```powershell
$env:HTTP_STREAMABLE_SERVER="true"
$env:FIRECRAWL_API_KEY="fc-..."
npx -y firecrawl-mcp
```

然后设置：

```text
FIRECRAWL_TRANSPORT=http
FIRECRAWL_MCP_URL=http://localhost:3000/mcp
```

## 模型配置

默认模型：

```text
AGENT_MODEL=deepseek:deepseek-chat
```

不要使用：

```text
AGENT_MODEL=deepseek:deepseek-reasoner
```

原因是本项目需要模型进行 MCP 工具调用，`deepseek-chat` 更适合 tool calling 场景。

如果需要切换到 OpenAI：

```powershell
pip install -e ".[openai]"
```

并设置：

```text
AGENT_MODEL=openai:gpt-4.1-mini
OPENAI_API_KEY=your_openai_api_key
```

## 测试

安装开发依赖：

```powershell
pip install -e ".[deepseek,dev]"
```

运行测试：

```powershell
pytest -q
```

## 常见问题

### Windows 下 `python -m venv .venv` 没有生成虚拟环境

可能是 `python` 指向 Windows Store 占位程序。改用：

```powershell
py -3.12 -m venv .venv
```

### PowerShell 无法执行 `Activate.ps1`

运行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### DeepSeek 报 tool_calls 消息不完整

这通常是流式请求中途被打断后，同一个 `thread_id` 留下了不完整工具调用历史。解决方法：

- 在网页中点击“清空当前线程”
- 或调用 `POST /threads/clear`
- 或换一个新的 `thread_id`

### Firecrawl MCP 启动失败

确认 Node.js 和 npx 可用：

```powershell
node --version
npx --version
```

然后确认 `.env` 中已配置：

```text
FIRECRAWL_API_KEY=your_firecrawl_api_key
```

## 安全说明

- 不要提交 `.env`
- 不要把 DeepSeek、高德或 Firecrawl Key 写入 README、代码或测试文件
- 如果 Key 曾经暴露，建议在对应平台控制台重新生成

## 许可证

可按你的项目需要选择 MIT、Apache-2.0 或其他许可证。
