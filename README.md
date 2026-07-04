# 本地财经情报网站

一个本地运行的财经情报工具，面向刚开始投资的用户：聚合可信公开来源，保留原文链接，用规则和可选 OpenAI API 做摘要、分类与量化打分。系统只做信息整理、风险提示和不确定性说明，不提供买卖建议。

## 功能

- 今日看板：按重要性汇总公告、财报、政策和全球宏观事件。
- 板块主题：默认跟踪 AI、新能源、半导体、医药、军工、消费。
- 关注列表：手动维护股票代码和公司名。
- 事件详情：展示来源、发布时间、原文链接、摘要、评分和新手解释。
- 设置页：配置 OpenAI API Key、采集频率、主题关键词和来源开关。

## 可信来源

第一版内置免费公开源配置：

- 巨潮资讯、上交所、深交所、北交所等 A 股披露入口。
- HKEXnews 港股公告入口。
- SEC EDGAR API 美股披露入口。
- 中国人民银行、证监会、国务院、Fed、ECB、SEC 等政策和监管入口。

部分官方网站没有稳定 RSS 或公开 API，采集器会以“可失败不阻断”的方式记录失败原因。生产使用时请遵守各网站 robots、访问频率和服务条款。

## 启动

后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

前端：

```powershell
cd frontend
pnpm install
pnpm dev
```

浏览器打开 `http://localhost:5173`。前端默认请求 `http://localhost:8000/api`。

## 公开部署（个人使用）

推荐最小公开版：一个 Docker Web 服务同时托管前端和后端，网站公开只读，刷新、设置和关注列表修改用 `ADMIN_TOKEN` 保护。

默认 `render.yaml` 使用 Render 免费 Web 服务，不配置持久磁盘。这样通常不需要先绑卡，但 SQLite 数据库保存在临时目录，服务重启或重新部署后历史数据可能丢失。先用它跑通最省心；如果以后想长期保存历史数据，再升级到付费磁盘或外部数据库。

### Render 部署

1. 把仓库推到 GitHub。
2. 在 Render 新建 Blueprint，选择这个仓库里的 `render.yaml`。
3. 在环境变量里设置：
   - `OPENAI_API_KEY`：你的 OpenAI API Key。
   - `USER_AGENT`：建议改成包含你邮箱的标识，方便官方站点联系。
   - `ADMIN_TOKEN`：Render 会自动生成，也可以手动设置一段长随机字符串。
4. 部署完成后打开 Render 给你的网址。
5. 进入网站“设置”，把 `ADMIN_TOKEN` 填进“管理员令牌”，之后就能手动刷新、改关注列表和保存设置。

### 其他 Docker 平台

支持任意能运行 Docker 的平台。如果想长期保留 SQLite 数据，需要持久化 `/data`；如果只想免费试用，可以省略 volume，并把 `DATABASE_PATH` 设为 `/tmp/intel.db`。

```bash
docker build -t finance-intel .
docker run -p 8000:8000 -v finance-intel-data:/data \
  -e ADMIN_TOKEN="change-this-long-token" \
  -e OPENAI_API_KEY="sk-..." \
  finance-intel
```

访问 `http://localhost:8000`。线上部署时把平台提供的网址作为公开入口即可。

## OpenAI 配置

后端支持两种方式：

- 在 `backend/.env` 设置 `OPENAI_API_KEY` 和可选 `OPENAI_MODEL`。
- 在网站设置页保存 API Key。该 Key 只保存在本地 SQLite 数据库，不提交到 Git。

没有 OpenAI Key 时，系统使用规则评分和模板摘要，便于离线预览。

## 验证

```powershell
cd backend
python -m unittest discover tests
```

```powershell
cd frontend
pnpm build
```
