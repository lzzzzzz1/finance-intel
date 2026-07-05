import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  FileText,
  ExternalLink,
  LayoutDashboard,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Star,
  Tags,
} from "lucide-react";
import "./styles.css";

const DEFAULT_API_BASE = import.meta.env.PROD ? "/api" : "http://localhost:8000/api";
const apiBase = import.meta.env.VITE_API_BASE || DEFAULT_API_BASE;
const isStaticMode = import.meta.env.PROD && !import.meta.env.VITE_API_BASE;
const staticDataUrl = `${import.meta.env.BASE_URL}data/dashboard.json`;

const tabs = [
  { id: "dashboard", label: "今日看板", icon: LayoutDashboard },
  { id: "themes", label: "板块主题", icon: Tags },
  { id: "watchlist", label: "关注列表", icon: Star },
  { id: "settings", label: "设置", icon: Settings },
];

const demoEvents = [
  {
    id: 0,
    title: "示例：央行发布政策信息，提示关注流动性与实体经济支持",
    source_name: "示例可信源",
    source_url: "https://www.pbc.gov.cn/",
    published_at: new Date().toISOString(),
    category: "policy",
    region: "CN",
    themes: ["消费", "新能源"],
    tickers: [],
    summary: "后端尚未采集数据时显示的示例事件。",
    novice_explanation: "启动后端并点击刷新，即可从本地 SQLite 读取真实采集记录。",
    importance_score: 72,
    sentiment_score: 12,
    risk_score: 38,
    confidence_score: 70,
    key_numbers: [],
    caveats: ["示例数据不代表真实新闻。"],
    disclaimer: "本工具仅用于信息整理与学习，不构成投资建议。",
  },
];

function scoreClass(value, neutral = false) {
  if (neutral) return value >= 0 ? "score positive" : "score negative";
  if (value >= 75) return "score high";
  if (value >= 45) return "score mid";
  return "score low";
}

function sentimentLabel(score = 0) {
  if (score >= 25) return "偏正面";
  if (score <= -25) return "偏负面";
  return "中性/待观察";
}

function riskLabel(score = 0) {
  if (score >= 70) return "高风险";
  if (score >= 40) return "中等风险";
  return "低到中等风险";
}

function impactLabel(event) {
  const themes = (event?.themes || []).slice(0, 2).join("、");
  const tickers = (event?.tickers || []).slice(0, 2).join("、");
  if (tickers) return `优先关注 ${tickers} 的后续公告和价格反应。`;
  if (themes) return `可能影响 ${themes} 相关板块的短期预期。`;
  return "主要用于判断宏观、政策或公司基本面的边际变化。";
}

function splitReadableText(text) {
  return String(text || "")
    .split(/\n+|(?<=。)/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 5);
}

function numberHint(item) {
  const text = String(item || "");
  const [value, context] = text.split("｜");
  let label = "需要结合原文口径判断";
  if (value?.includes("%")) label = "比例变化，重点看同比/环比和基数";
  if (value?.includes("亿元") || value?.includes("亿美元")) label = "金额规模，重点看是否持续、是否一次性";
  if (value?.includes("万股")) label = "股份数量，重点看增减持或回购目的";
  return { value: value || text, context: context || label, label };
}

function App() {
  const [active, setActive] = useState("dashboard");
  const [events, setEvents] = useState(demoEvents);
  const [sources, setSources] = useState([]);
  const [stats, setStats] = useState({ event_count: 0, watch_count: 0, theme_count: 0 });
  const [selected, setSelected] = useState(demoEvents[0]);
  const [themes, setThemes] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [status, setStatus] = useState(isStaticMode ? "GitHub Pages 静态看板" : "等待连接后端");
  const [query, setQuery] = useState("");
  const [adminToken, setAdminToken] = useState(() => localStorage.getItem("adminToken") || "");

  async function api(path, options) {
    if (isStaticMode) {
      throw new Error("static mode does not support API writes");
    }
    const method = options?.method || "GET";
    const headers = { "Content-Type": "application/json", ...(options?.headers || {}) };
    if (method !== "GET" && adminToken) {
      headers["X-Admin-Token"] = adminToken;
    }
    const response = await fetch(`${apiBase}${path}`, {
      ...options,
      headers,
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  }

  function saveAdminToken(value) {
    setAdminToken(value);
    localStorage.setItem("adminToken", value);
  }

  async function loadAll() {
    try {
      if (isStaticMode) {
        const response = await fetch(staticDataUrl, { cache: "no-store" });
        if (!response.ok) throw new Error("static data not found");
        const dashboard = await response.json();
        setEvents(dashboard.events?.length ? dashboard.events : demoEvents);
        setSources(dashboard.sources || []);
        setStats(dashboard.stats || {});
        setThemes(dashboard.themes || []);
        setWatchlist(dashboard.watchlist || []);
        setSelected(dashboard.events?.[0] || demoEvents[0]);
        const generated = dashboard.generated_at ? new Date(dashboard.generated_at).toLocaleString("zh-CN") : "尚未生成";
        setStatus(`静态数据已加载，生成时间：${generated}`);
        return;
      }
      const [dashboard, themeData, watchData] = await Promise.all([
        api("/dashboard"),
        api("/themes"),
        api("/watchlist"),
      ]);
      setEvents(dashboard.events.length ? dashboard.events : demoEvents);
      setSources(dashboard.sources || []);
      setStats(dashboard.stats || {});
      setThemes(themeData);
      setWatchlist(watchData);
      setSelected(dashboard.events[0] || demoEvents[0]);
      setStatus("已连接本地后端");
    } catch (error) {
      setStatus("未连接后端，当前为界面预览");
    }
  }

  async function refreshSources() {
    if (isStaticMode) {
      setStatus("GitHub Pages 版本由 GitHub Actions 定时刷新；也可以在仓库 Actions 页面手动运行。");
      return;
    }
    setStatus("正在刷新公开来源");
    try {
      const result = await api("/refresh", { method: "POST" });
      setStatus(`刷新完成：新增 ${result.inserted} 条，失败源 ${result.failed} 个`);
      await loadAll();
    } catch (error) {
      setStatus("刷新失败，请检查后端和网络");
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  const filteredEvents = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    if (!keyword) return events;
    return events.filter((event) => {
      const text = `${event.title} ${event.summary} ${(event.themes || []).join(" ")} ${(event.tickers || []).join(" ")}`.toLowerCase();
      return text.includes(keyword);
    });
  }, [events, query]);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={26} />
          <div>
            <strong>财经情报</strong>
            <span>可信公开源</span>
          </div>
        </div>
        <nav>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button key={tab.id} className={active === tab.id ? "active" : ""} onClick={() => setActive(tab.id)} title={tab.label}>
                <Icon size={18} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
        <div className="notice">
          <AlertTriangle size={16} />
          <span>仅供学习和信息整理，不构成投资建议。</span>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{tabs.find((tab) => tab.id === active)?.label}</h1>
            <p>{status}</p>
          </div>
          <div className="top-actions">
            <label className="search">
              <Search size={17} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索股票、板块、事件" />
            </label>
            <button className="primary" onClick={refreshSources}>
              <RefreshCw size={17} />
              {isStaticMode ? "更新说明" : "刷新"}
            </button>
          </div>
        </header>

        {active === "dashboard" && (
          <Dashboard events={filteredEvents} sources={sources} stats={stats} selected={selected} onSelect={setSelected} />
        )}
        {active === "themes" && <Themes events={filteredEvents} themes={themes} selected={selected} onSelect={setSelected} />}
        {active === "watchlist" && <Watchlist watchlist={watchlist} reload={loadAll} api={api} events={filteredEvents} hasAdminToken={Boolean(adminToken)} isStaticMode={isStaticMode} />}
        {active === "settings" && (
          <SettingsPanel
            sources={sources}
            themes={themes}
            api={api}
            reload={loadAll}
            adminToken={adminToken}
            setAdminToken={saveAdminToken}
            isStaticMode={isStaticMode}
          />
        )}
      </main>
    </div>
  );
}

function Dashboard({ events, selected, onSelect }) {
  const highRiskCount = events.filter((event) => (event.risk_score || 0) >= 70).length;
  return (
    <section className="dashboard-grid">
      <div className="brief-strip">
        <strong>{events.length} 条重点</strong>
        <span>{highRiskCount} 条高风险</span>
        <span>按重要性排序</span>
      </div>
      <div className="event-list">
        {events.map((event) => (
          <EventCard key={`${event.id}-${event.title}`} event={event} active={selected?.id === event.id} onClick={() => onSelect(event)} />
        ))}
      </div>
      <EventDetail event={selected} />
    </section>
  );
}

function EventCard({ event, active, onClick }) {
  const themes = (event.themes || []).slice(0, 2);
  return (
    <button type="button" className={`event-card ${active ? "selected" : ""}`} onClick={onClick} aria-pressed={Boolean(active)}>
      <div className="event-head">
        <span>{event.source_name}</span>
        <span>{event.category}</span>
      </div>
      <strong>{event.title}</strong>
      <div className="chips">
        {themes.map((theme) => (
          <span key={theme}>{theme}</span>
        ))}
        {!themes.length && <span>{event.region}</span>}
      </div>
      <div className="score-row">
        <span className={scoreClass(event.importance_score)}>重要 {event.importance_score}</span>
        <span className={scoreClass(event.sentiment_score, true)}>情绪 {event.sentiment_score}</span>
        <span className={scoreClass(event.risk_score)}>风险 {event.risk_score}</span>
      </div>
    </button>
  );
}

function EventDetail({ event }) {
  const [readingMode, setReadingMode] = useState("brief");
  if (!event) return null;
  const explanationParts = splitReadableText(event.novice_explanation);
  const keyNumbers = (event.key_numbers || []).map(numberHint);
  const readingSections = event.reading_sections || [];
  const evidenceSnippets = event.evidence_snippets || [];
  const bodyPreview = String(event.body || "").slice(0, readingMode === "full" ? 3600 : 900);
  return (
    <article className="detail">
      <div className="detail-top">
        <span className="trust"><CheckCircle2 size={16} />AI可信度 {event.confidence_score}</span>
        <a href={event.source_url} target="_blank" rel="noreferrer">
          官网原文 <ExternalLink size={15} />
        </a>
      </div>
      <h2>{event.title}</h2>
      <p className="meta">{event.source_name} · {event.published_at || "未知时间"} · {event.category}</p>

      <section className="ai-read">
        <div className="ai-read-title">
          <FileText size={18} />
          <h3>AI速读</h3>
        </div>
        <p className="ai-summary">{event.summary || "暂无摘要，建议点击官网原文核对完整内容。"}</p>
        <div className="ai-grid">
          <div>
            <span>可能影响</span>
            <strong>{impactLabel(event)}</strong>
          </div>
          <div>
            <span>情绪判断</span>
            <strong>{sentimentLabel(event.sentiment_score)}</strong>
          </div>
          <div>
            <span>风险提示</span>
            <strong>{riskLabel(event.risk_score)}</strong>
          </div>
        </div>
      </section>

      <div className="section-title compact-title">
        <div>
          <h3>站内阅读</h3>
        </div>
        <div className="segmented">
          <button type="button" className={readingMode === "brief" ? "active" : ""} onClick={() => setReadingMode("brief")}>精简</button>
          <button type="button" className={readingMode === "full" ? "active" : ""} onClick={() => setReadingMode("full")}>完整</button>
        </div>
      </div>
      {readingSections.length ? (
        <div className="reading-sections">
          {readingSections.map((section) => (
            <section key={`${section.title}-${section.content}`}>
              <strong>{section.title}</strong>
              <p>{section.content}</p>
            </section>
          ))}
        </div>
      ) : (
        <p className="article-preview">{bodyPreview || "暂无可展示正文，请打开官网原文核对。"}</p>
      )}
      {readingMode === "full" && readingSections.length > 0 && <p className="article-preview">{bodyPreview}</p>}

      <h3>证据摘录</h3>
      <div className="evidence-list">
        {evidenceSnippets.length ? evidenceSnippets.map((item) => <blockquote key={item}>{item}</blockquote>) : <div className="empty-state">暂无可自动定位的证据片段，请打开官网原文核对。</div>}
      </div>

      <h3>新手解释</h3>
      <div className="explain-list">
        {explanationParts.length ? explanationParts.map((item) => <p key={item}>{item}</p>) : <p>暂无更详细解释，请优先核对官网原文。</p>}
      </div>
      <h3>关键数字怎么读</h3>
      <div className="number-grid">
        {keyNumbers.length ? keyNumbers.map((item) => (
          <div className="number-card" key={`${item.value}-${item.context}`}>
            <strong>{item.value}</strong>
            <span>{item.context}</span>
            <small>{item.label}</small>
          </div>
        )) : <div className="empty-state">这条内容暂时没有抽取到关键数字，重点看事件本身、监管口径和后续公告。</div>}
      </div>
      {(event.caveats || []).length > 0 && <p className="disclaimer">{event.caveats[0]} {event.disclaimer}</p>}
    </article>
  );
}

function DetailPlaceholder({ themeName }) {
  return (
    <article className="detail detail-placeholder">
      <div className="ai-read-title">
        <FileText size={18} />
        <h3>等待事件</h3>
      </div>
      <h2>{themeName || "当前板块"}暂无匹配报告</h2>
      <p>
        这个板块当前没有匹配到已采集事件。可以换一个板块、清空搜索词，或者点击刷新获取新的公开来源。
      </p>
      <p className="hint">没有来源时不会生成结论，避免把旧事件误认为当前板块内容。</p>
    </article>
  );
}

function Themes({ events, themes, selected, onSelect }) {
  const themeList = useMemo(() => (
    themes.length ? themes : [{ name: "新能源", keywords: ["储能", "光伏"] }]
  ), [themes]);
  const [activeTheme, setActiveTheme] = useState("全部");
  const themeSummaries = useMemo(() => {
    const baseThemes = [
      { name: "全部", keywords: ["所有已采集事件"], relatedOverride: events },
      { name: "未分类", keywords: ["暂未命中行业关键词"], relatedOverride: events.filter((event) => !(event.themes || []).length) },
      ...themeList,
    ];
    return baseThemes.map((theme) => {
      const related = theme.relatedOverride || events.filter((event) => (event.themes || []).includes(theme.name));
      const avgImportance = related.length
        ? Math.round(related.reduce((sum, event) => sum + (event.importance_score || 0), 0) / related.length)
        : 0;
      const maxRisk = related.length ? Math.max(...related.map((event) => event.risk_score || 0)) : 0;
      return { ...theme, related, avgImportance, maxRisk };
    });
  }, [events, themeList]);
  const currentTheme = themeSummaries.find((theme) => theme.name === activeTheme) || themeSummaries[0];
  const currentEvents = currentTheme?.related || [];
  const detailEvent = currentEvents.find((event) => event.id === selected?.id) || currentEvents[0] || null;

  useEffect(() => {
    if (!themeSummaries.some((theme) => theme.name === activeTheme)) {
      setActiveTheme(themeSummaries[0]?.name || "");
    }
  }, [activeTheme, themeSummaries]);

  function selectTheme(theme) {
    setActiveTheme(theme.name);
    if (theme.related[0]) {
      onSelect(theme.related[0]);
    }
  }

  return (
    <section className="themes-layout">
      <div className="theme-rail">
        {themeSummaries.map((theme) => (
          <button
            type="button"
            className={`theme-pill ${activeTheme === theme.name ? "active" : ""}`}
            key={theme.name}
            onClick={() => selectTheme(theme)}
          >
            <div>
              <strong>{theme.name}</strong>
              <span>{theme.related.length} 条 · 重要 {theme.avgImportance || "-"}</span>
            </div>
            <small>最高风险 {theme.maxRisk || "-"}</small>
          </button>
        ))}
      </div>
      <div className="theme-block">
        <div className="section-title">
          <div>
            <h2>{currentTheme?.name || "板块"}</h2>
            <p className="hint">{(currentTheme?.keywords || []).slice(0, 8).join("、") || "暂无关键词"}</p>
          </div>
          <span>{currentEvents.length} 条</span>
        </div>
        <div className="theme-events">
          {currentEvents.length ? currentEvents.map((event) => (
            <EventCard key={event.id} event={event} active={detailEvent?.id === event.id} onClick={() => onSelect(event)} />
          )) : <div className="empty-state">当前搜索条件下，这个板块暂时没有匹配事件。</div>}
        </div>
      </div>
      {detailEvent ? <EventDetail event={detailEvent} /> : <DetailPlaceholder themeName={currentTheme?.name} />}
    </section>
  );
}

function Watchlist({ watchlist, reload, api, events, hasAdminToken, isStaticMode }) {
  const [form, setForm] = useState({ ticker: "", name: "", market: "CN", notes: "" });
  async function save(event) {
    event.preventDefault();
    await api("/watchlist", { method: "POST", body: JSON.stringify(form) });
    setForm({ ticker: "", name: "", market: "CN", notes: "" });
    await reload();
  }
  async function remove(ticker) {
    await api(`/watchlist/${ticker}`, { method: "DELETE" });
    await reload();
  }
  return (
    <section className="two-column">
      <form className="panel" onSubmit={save}>
        <h2>添加关注</h2>
        {isStaticMode && <p className="hint">GitHub Pages 版本是只读看板；关注列表需要以后通过仓库配置或本地后端维护。</p>}
        {!isStaticMode && !hasAdminToken && <p className="hint">公开部署后需要先在设置页填写管理员令牌，才能修改关注列表。</p>}
        <input disabled={isStaticMode} value={form.ticker} onChange={(e) => setForm({ ...form, ticker: e.target.value })} placeholder="股票代码，如 600519" required />
        <input disabled={isStaticMode} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="公司名称" required />
        <select disabled={isStaticMode} value={form.market} onChange={(e) => setForm({ ...form, market: e.target.value })}>
          <option value="CN">A股</option>
          <option value="HK">港股</option>
          <option value="US">美股</option>
        </select>
        <textarea disabled={isStaticMode} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="关注理由" />
        <button disabled={isStaticMode} className="primary">保存</button>
      </form>
      <div className="panel">
        <h2>当前关注</h2>
        {watchlist.map((item) => (
          <div className="watch-row" key={item.ticker}>
            <div><strong>{item.ticker}</strong><span>{item.name} · {item.market}</span></div>
            <button onClick={() => remove(item.ticker)}>移除</button>
          </div>
        ))}
        <h2>关联事件</h2>
        {events.filter((event) => (event.tickers || []).some((ticker) => watchlist.some((w) => w.ticker === ticker))).slice(0, 5).map((event) => <EventCard key={event.id} event={event} />)}
      </div>
    </section>
  );
}

function SettingsPanel({ sources, themes, api, reload, adminToken, setAdminToken, isStaticMode }) {
  const [settings, setSettings] = useState({ collect_interval_minutes: 180, openai_api_key: "" });
  async function saveSettings(event) {
    event.preventDefault();
    await api("/settings", { method: "PUT", body: JSON.stringify(settings) });
    await reload();
  }
  return (
    <section className="two-column">
      <form className="panel" onSubmit={saveSettings}>
        <h2>{isStaticMode ? "GitHub Pages 设置" : "部署设置"}</h2>
        {isStaticMode && (
          <p className="hint">
            当前是不绑卡的静态版本。数据由 GitHub Actions 定时生成，不能在网页里直接保存设置或刷新后端。
          </p>
        )}
        {!isStaticMode && (
          <>
            <label>管理员令牌</label>
            <input type="password" value={adminToken} onChange={(e) => setAdminToken(e.target.value)} placeholder="部署环境里的 ADMIN_TOKEN" />
            <p className="hint">公开网站只读内容对外开放；刷新、设置和关注列表修改会携带这个令牌。</p>
          </>
        )}
        <label>采集间隔（分钟）</label>
        <input disabled={isStaticMode} type="number" min="15" max="1440" value={settings.collect_interval_minutes} onChange={(e) => setSettings({ ...settings, collect_interval_minutes: Number(e.target.value) })} />
        <label>OpenAI API Key</label>
        <input disabled={isStaticMode} type="password" value={settings.openai_api_key} onChange={(e) => setSettings({ ...settings, openai_api_key: e.target.value })} placeholder="sk-..." />
        <button disabled={isStaticMode} className="primary">保存设置</button>
      </form>
      <div className="panel source-panel">
        <h2>可信来源状态</h2>
        {sources.map((source) => (
          <div className="source-row" key={source.id}>
            <BarChart3 size={16} />
            <div>
              <strong>{source.name}</strong>
              <span>{source.region} · {source.category} · {source.last_status || "未检查"}</span>
            </div>
          </div>
        ))}
        <h2>主题关键词</h2>
        <div className="chips">{themes.flatMap((theme) => theme.keywords || []).slice(0, 30).map((keyword) => <span key={keyword}>{keyword}</span>)}</div>
      </div>
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);
