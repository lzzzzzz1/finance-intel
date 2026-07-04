import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  BarChart3,
  BookOpen,
  CheckCircle2,
  ExternalLink,
  Globe2,
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
        {active === "themes" && <Themes events={filteredEvents} themes={themes} />}
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

function Dashboard({ events, sources, stats, selected, onSelect }) {
  return (
    <section className="dashboard-grid">
      <div className="metrics">
        <Metric icon={BookOpen} label="事件" value={stats.event_count || events.length} />
        <Metric icon={Star} label="关注" value={stats.watch_count || 0} />
        <Metric icon={Tags} label="主题" value={stats.theme_count || 0} />
        <Metric icon={Globe2} label="来源" value={sources.length || 12} />
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

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="metric">
      <Icon size={18} />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EventCard({ event, active, onClick }) {
  return (
    <button className={`event-card ${active ? "selected" : ""}`} onClick={onClick}>
      <div className="event-head">
        <span>{event.source_name}</span>
        <span>{event.region}</span>
      </div>
      <strong>{event.title}</strong>
      <p>{event.summary}</p>
      <div className="chips">
        {(event.themes || []).slice(0, 3).map((theme) => (
          <span key={theme}>{theme}</span>
        ))}
        <span>{event.category}</span>
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
  if (!event) return null;
  return (
    <article className="detail">
      <div className="detail-top">
        <span className="trust"><CheckCircle2 size={16} />可信度 {event.confidence_score}</span>
        <a href={event.source_url} target="_blank" rel="noreferrer">
          原文 <ExternalLink size={15} />
        </a>
      </div>
      <h2>{event.title}</h2>
      <p className="meta">{event.source_name} · {event.published_at || "未知时间"} · {event.category}</p>
      <h3>新手解释</h3>
      <p>{event.novice_explanation}</p>
      <h3>关键数字</h3>
      <div className="chips">
        {(event.key_numbers || []).length ? event.key_numbers.map((item) => <span key={item}>{item}</span>) : <span>暂无抽取</span>}
      </div>
      <h3>注意事项</h3>
      <ul>
        {(event.caveats || []).map((item) => <li key={item}>{item}</li>)}
      </ul>
      <p className="disclaimer">{event.disclaimer}</p>
    </article>
  );
}

function Themes({ events, themes }) {
  return (
    <section className="theme-grid">
      {(themes.length ? themes : [{ name: "新能源", keywords: ["储能", "光伏"] }]).map((theme) => {
        const related = events.filter((event) => (event.themes || []).includes(theme.name));
        return (
          <div className="theme-block" key={theme.name}>
            <div className="section-title">
              <h2>{theme.name}</h2>
              <span>{related.length} 条</span>
            </div>
            <div className="chips">{(theme.keywords || []).map((keyword) => <span key={keyword}>{keyword}</span>)}</div>
            {related.slice(0, 4).map((event) => <EventCard key={event.id} event={event} />)}
          </div>
        );
      })}
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
