import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import './i18n/index.js';
import './style.css';
import {
  LanguageToggle, SearchBar, FilterSidebar,
  EventCard, EventDetail, Pagination, AdminPanel
} from './components/index.jsx';
import { fetchEvents, fetchDepartments, fetchStats } from './api/client.js';
import i18n from './i18n/index.js';

const isAdminRoute = () => window.location.pathname === '/admin';

export default function App() {
  const { t } = useTranslation();
  const lang = i18n.language;

  // Admin page
  if (isAdminRoute()) {
    return (
      <>
        <Header />
        <AdminPanel />
      </>
    );
  }

  return (
    <>
      <Header />
      <SearchPage lang={lang} t={t} />
    </>
  );
}

// ============================================================
// Header
// ============================================================
function Header() {
  const { t } = useTranslation();
  return (
    <header className="header" role="banner">
      <div className="header__logo">
        <div className="header__title">🎓 {t('site_title')}</div>
        <div className="header__subtitle">
          {t('open_campus_year')} — {t('site_subtitle')}
        </div>
      </div>
      <div className="header__actions">
        <LanguageToggle i18n={i18n} />
        <a id="admin-link" href="/admin" className="header__admin-link">⚙️ Admin</a>
      </div>
    </header>
  );
}

// ============================================================
// SearchPage
// ============================================================
function SearchPage({ lang, t }) {
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState({ date: '', department: '', target: '' });
  const [page, setPage] = useState(1);
  const [result, setResult] = useState({ total: 0, items: [], page: 1, limit: 15 });
  const [departments, setDepartments] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState(null);

  const LIMIT = 15;

  const load = useCallback(async (q, f, p) => {
    setLoading(true);
    try {
      const params = {
        q: q || undefined,
        date: f.date || undefined,
        department: f.department || undefined,
        target: f.target || undefined,
        lang,
        page: p,
        limit: LIMIT,
      };
      const data = await fetchEvents(params);
      setResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [lang]);

  // Initial load and on filter changes
  useEffect(() => { load(query, filters, page); }, [lang, page]);
  useEffect(() => { setPage(1); load(query, filters, 1); }, [filters]);

  useEffect(() => {
    fetchDepartments(lang).then(setDepartments).catch(() => {});
    fetchStats().then(setStats).catch(() => {});
  }, [lang]);

  const handleSearch = (q) => {
    setQuery(q);
    setPage(1);
    load(q, filters, 1);
  };

  const handleFilterChange = (f) => setFilters(f);

  return (
    <div className="app-layout">
      <FilterSidebar
        filters={filters}
        onChange={handleFilterChange}
        departments={departments}
        stats={stats}
        lang={lang}
      />

      <main className="main-content" role="main" id="main">
        <SearchBar onSearch={handleSearch} defaultValue={query} />

        {!loading && (
          <div className="results-info" aria-live="polite">
            {t('results_count', { count: result.total })}
          </div>
        )}

        {loading ? (
          <div className="loading-state" aria-live="polite">
            <div className="loading-spinner" role="status" aria-label={t('loading')} />
            <div>{t('loading')}</div>
          </div>
        ) : result.items.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state__icon">🔍</div>
            <div>{t('no_results')}</div>
          </div>
        ) : (
          <>
            <div className="events-grid" role="feed" aria-label={t('results_count', { count: result.total })}>
              {result.items.map((ev) => (
                <EventCard
                  key={ev.id}
                  event={ev}
                  lang={lang}
                  onClick={() => setSelectedId(ev.id)}
                />
              ))}
            </div>
            <Pagination
              page={page}
              total={result.total}
              limit={LIMIT}
              onPage={setPage}
            />
          </>
        )}
      </main>

      {selectedId && (
        <EventDetail
          eventId={selectedId}
          lang={lang}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}
