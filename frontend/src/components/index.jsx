import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchEvents, fetchEvent, fetchDepartments, fetchStats, patchTranslation, triggerRefresh } from '../api/client';

// ============================================================
// LanguageToggle
// ============================================================
export function LanguageToggle({ i18n }) {
  const lang = i18n.language;
  const switchLang = (l) => {
    i18n.changeLanguage(l);
    localStorage.setItem('lang', l);
    document.documentElement.lang = l;
  };
  return (
    <div className="lang-toggle" role="group" aria-label="Language selector">
      <button
        id="lang-ja"
        className={`lang-toggle__btn ${lang === 'ja' ? 'active' : ''}`}
        onClick={() => switchLang('ja')}
        aria-pressed={lang === 'ja'}
      >🇯🇵 日本語</button>
      <button
        id="lang-en"
        className={`lang-toggle__btn ${lang === 'en' ? 'active' : ''}`}
        onClick={() => switchLang('en')}
        aria-pressed={lang === 'en'}
      >🇬🇧 English</button>
    </div>
  );
}

// ============================================================
// SearchBar
// ============================================================
export function SearchBar({ onSearch, defaultValue = '' }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState(defaultValue);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch(query.trim());
  };

  return (
    <form className="search-bar" role="search" onSubmit={handleSubmit}>
      <input
        id="search-input"
        className="search-bar__input"
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={t('search_placeholder')}
        aria-label={t('search_placeholder')}
      />
      <button id="search-btn" className="search-bar__btn" type="submit">
        🔍 {t('search_button')}
      </button>
    </form>
  );
}

// ============================================================
// FilterSidebar
// ============================================================
export function FilterSidebar({ filters, onChange, departments, stats, lang }) {
  const { t } = useTranslation();

  const resetFilters = () =>
    onChange({ date: '', department: '', target: '' });

  return (
    <aside className="sidebar" aria-label={t('filter_department')}>
      {/* Stats */}
      {stats && (
        <div className="stats-card">
          <div className="stats-item">
            <div className="stats-item__value">{stats.total_events ?? '—'}</div>
            <div className="stats-item__label">{lang === 'ja' ? '企画数' : 'Events'}</div>
          </div>
          <div className="stats-item">
            <div className="stats-item__value">{stats.departments ?? '—'}</div>
            <div className="stats-item__label">{lang === 'ja' ? '部局数' : 'Departments'}</div>
          </div>
          {stats.last_event_update && (
            <div className="stats-item" style={{ gridColumn: '1 / -1' }}>
              <div className="stats-item__label">
                {t('last_updated')}: {stats.last_event_update.slice(0, 10)}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Date filter */}
      <div className="filter-card">
        <div className="filter-card__title">{t('filter_date')}</div>
        <input
          id="filter-date"
          className="filter-input"
          type="date"
          value={filters.date}
          onChange={(e) => onChange({ ...filters, date: e.target.value })}
          aria-label={t('filter_date')}
        />
      </div>

      {/* Department filter */}
      <div className="filter-card">
        <div className="filter-card__title">{t('filter_department')}</div>
        <select
          id="filter-department"
          className="filter-select"
          value={filters.department}
          onChange={(e) => onChange({ ...filters, department: e.target.value })}
          aria-label={t('filter_department')}
        >
          <option value="">{t('filter_all')}</option>
          {departments.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
      </div>

      {/* Target audience filter */}
      <div className="filter-card">
        <div className="filter-card__title">{t('filter_target')}</div>
        <select
          id="filter-target"
          className="filter-select"
          value={filters.target}
          onChange={(e) => onChange({ ...filters, target: e.target.value })}
          aria-label={t('filter_target')}
        >
          <option value="">{t('filter_all')}</option>
          <option value={lang === 'ja' ? '一般市民' : 'General'}>{t('target_general')}</option>
          <option value={lang === 'ja' ? '小中高生' : 'K-12'}>{t('target_students')}</option>
          <option value={lang === 'ja' ? '大学生' : 'University'}>{t('target_university')}</option>
          <option value={lang === 'ja' ? '研究者' : 'Researcher'}>{t('target_researchers')}</option>
        </select>
      </div>

      <button id="filter-reset" className="filter-reset-btn" onClick={resetFilters}>
        ↺ {lang === 'ja' ? 'フィルターをリセット' : 'Reset filters'}
      </button>
    </aside>
  );
}

// ============================================================
// EventCard
// ============================================================
export function EventCard({ event, lang, onClick }) {
  const { t } = useTranslation();
  const title = lang === 'en' ? (event.title_en || event.title_ja) : event.title_ja;
  const desc  = lang === 'en' ? (event.description_en || event.description_ja) : event.description_ja;
  const dept  = lang === 'en' ? (event.department_en || event.department_ja) : event.department_ja;
  const target = lang === 'en' ? (event.target_audience_en || event.target_audience_ja) : event.target_audience_ja;

  const dateStr = event.date_start
    ? new Date(event.date_start).toLocaleDateString(lang === 'ja' ? 'ja-JP' : 'en-US', {
        month: 'long', day: 'numeric', weekday: 'short',
      })
    : null;

  return (
    <article
      className="event-card"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      aria-label={title}
    >
      <div className="event-card__body">
        {dept && <div className="event-card__dept">{dept}</div>}
        <h2 className="event-card__title">{title}</h2>
        {desc && <p className="event-card__desc">{desc}</p>}
        <div className="event-card__meta">
          {dateStr && <span className="badge badge--date">📅 {dateStr}</span>}
          {target && <span className="badge badge--target">👥 {target}</span>}
          <span className={`badge ${event.registration_required ? 'badge--required' : 'badge--registration'}`}>
            {event.registration_required ? `📝 ${t('registration_required')}` : `✅ ${t('registration_not_required')}`}
          </span>
        </div>
      </div>
      <div className="event-card__side">
        <span className="event-card__arrow" aria-hidden="true">→</span>
      </div>
    </article>
  );
}

// ============================================================
// EventDetail Modal
// ============================================================
export function EventDetail({ eventId, lang, onClose }) {
  const { t } = useTranslation();
  const [event, setEvent] = useState(null);

  useEffect(() => {
    if (!eventId) return;
    fetchEvent(eventId).then(setEvent).catch(console.error);
  }, [eventId]);

  useEffect(() => {
    const handler = (e) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  if (!event) return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="loading-state">
          <div className="loading-spinner" role="status" aria-label={t('loading')} />
        </div>
      </div>
    </div>
  );

  const title = lang === 'en' ? (event.title_en || event.title_ja) : event.title_ja;
  const desc  = lang === 'en' ? (event.description_en || event.description_ja) : event.description_ja;
  const dept  = lang === 'en' ? (event.department_en || event.department_ja) : event.department_ja;
  const venue = lang === 'en' ? (event.venue_en || event.venue_ja) : event.venue_ja;
  const target= lang === 'en' ? (event.target_audience_en || event.target_audience_ja) : event.target_audience_ja;
  const researchers = lang === 'en'
    ? (event.researchers_en?.length ? event.researchers_en : event.researchers)
    : event.researchers;

  const formatDate = (iso) => iso
    ? new Date(iso).toLocaleString(lang === 'ja' ? 'ja-JP' : 'en-US', {
        year: 'numeric', month: 'long', day: 'numeric',
        hour: '2-digit', minute: '2-digit'
      })
    : null;

  const dateStr = event.date_start
    ? `${formatDate(event.date_start)}${event.date_end ? ` – ${formatDate(event.date_end)}` : ''}`
    : null;

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label={title}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          {dept && <div className="modal__dept">{dept}</div>}
          <h1 className="modal__title">{title}</h1>
          <button id="modal-close" className="modal__close" onClick={onClose} aria-label={t('close')}>✕</button>
        </div>
        <div className="modal__body">
          {desc && <div className="modal__description">{desc}</div>}

          {dateStr && (
            <div className="modal__section">
              <span className="modal__label">{t('event_date')}</span>
              <span className="modal__value">📅 {dateStr}</span>
            </div>
          )}
          {venue && (
            <div className="modal__section">
              <span className="modal__label">{t('event_venue')}</span>
              <span className="modal__value">📍 {venue}</span>
            </div>
          )}
          {target && (
            <div className="modal__section">
              <span className="modal__label">{t('event_target')}</span>
              <span className="modal__value">👥 {target}</span>
            </div>
          )}
          {researchers?.length > 0 && (
            <div className="modal__section">
              <span className="modal__label">{t('event_researchers')}</span>
              <div className="modal__researchers">
                {researchers.map((r, i) => (
                  <span key={i} className="researcher-chip">👤 {r}</span>
                ))}
              </div>
            </div>
          )}
          <div className="modal__section">
            <span className="modal__label">{t('event_registration')}</span>
            <span className="modal__value">
              {event.registration_required
                ? `📝 ${t('registration_required')}`
                : `✅ ${t('registration_not_required')}`}
            </span>
          </div>
          {event.registration_url && (
            <div className="modal__section">
              <span className="modal__label">{lang === 'ja' ? '申込URL' : 'Apply'}</span>
              <a href={event.registration_url} target="_blank" rel="noopener noreferrer"
                 className="modal__value" style={{ color: 'var(--color-accent)' }}>
                🔗 {event.registration_url}
              </a>
            </div>
          )}
          {event.source_url && (
            <div className="modal__section">
              <span className="modal__label">{lang === 'ja' ? '出典' : 'Source'}</span>
              <a href={event.source_url} target="_blank" rel="noopener noreferrer"
                 className="modal__value" style={{ color: 'var(--color-accent)', fontSize: '0.82rem' }}>
                🌐 {event.source_url}
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Pagination
// ============================================================
export function Pagination({ page, total, limit, onPage }) {
  const { t } = useTranslation();
  const totalPages = Math.ceil(total / limit);
  if (totalPages <= 1) return null;
  return (
    <nav className="pagination" aria-label="Pagination">
      <button id="page-prev" className="pagination__btn" onClick={() => onPage(page - 1)} disabled={page <= 1}>
        ← {t('page_prev')}
      </button>
      <span className="pagination__info">{page} / {totalPages}</span>
      <button id="page-next" className="pagination__btn" onClick={() => onPage(page + 1)} disabled={page >= totalPages}>
        {t('page_next')} →
      </button>
    </nav>
  );
}

// ============================================================
// AdminPanel (translation editor)
// ============================================================
export function AdminPanel() {
  const { t } = useTranslation();
  const [apiKey, setApiKey] = useState(localStorage.getItem('admin_key') || '');
  const [authed, setAuthed] = useState(false);
  const [events, setEvents] = useState([]);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({});
  const [toast, setToast] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const login = () => {
    localStorage.setItem('admin_key', apiKey);
    setAuthed(true);
    fetchEvents({ limit: 100 }).then((r) => setEvents(r.items));
  };

  const logout = () => {
    localStorage.removeItem('admin_key');
    setAuthed(false);
    setApiKey('');
    setSelected(null);
  };

  const selectEvent = (ev) => {
    setSelected(ev);
    setForm({
      title_en: ev.title_en || '',
      venue_en: ev.venue_en || '',
      description_en: ev.description_en || '',
      target_audience_en: ev.target_audience_en || '',
      department_en: ev.department_en || '',
      researchers_en: Array.isArray(ev.researchers_en)
        ? ev.researchers_en.join(', ')
        : (ev.researchers_en || ''),
    });
  };

  const save = async () => {
    const updates = {
      ...form,
      researchers_en: form.researchers_en
        ? form.researchers_en.split(',').map((r) => r.trim()).filter(Boolean)
        : [],
    };
    try {
      await patchTranslation(selected.id, updates, apiKey);
      showToast(t('admin_saved'));
      // update local list
      setEvents((prev) =>
        prev.map((e) => e.id === selected.id ? { ...e, ...updates, translation_edited: 1 } : e)
      );
    } catch {
      showToast(t('admin_error'));
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const result = await triggerRefresh(apiKey);
      showToast(result.success ? '✅ 更新完了' : '❌ エラー: ' + result.error);
      if (result.success) fetchEvents({ limit: 100 }).then((r) => setEvents(r.items));
    } catch {
      showToast('❌ エラー');
    } finally {
      setRefreshing(false);
    }
  };

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  if (!authed) {
    return (
      <div className="admin-layout">
        <div className="admin-card">
          <h1 className="admin-card__title">🔑 {t('admin_title')}</h1>
          <div className="admin-form">
            <div className="admin-field">
              <label className="admin-field__label" htmlFor="admin-key-input">{t('admin_api_key')}</label>
              <input
                id="admin-key-input"
                className="admin-field__input"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && login()}
                placeholder="Enter admin API key"
              />
            </div>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button id="admin-login-btn" className="btn-primary" onClick={login}>{t('admin_login')}</button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-layout">
      <div className="admin-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h1 className="admin-card__title">📝 {t('admin_title')}</h1>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button id="admin-refresh-btn" className="btn-secondary" onClick={handleRefresh} disabled={refreshing}>
              {refreshing ? '⏳ 更新中...' : '🔄 今すぐクロール'}
            </button>
            <button id="admin-logout-btn" className="btn-secondary" onClick={logout}>{t('admin_logout')}</button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '1.5rem' }}>
          {/* Event list */}
          <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
            {events.map((ev) => (
              <div
                key={ev.id}
                id={`admin-event-${ev.id}`}
                className={`admin-event-row ${ev.translation_edited ? 'edited' : ''}`}
                onClick={() => selectEvent(ev)}
                role="button"
                tabIndex={0}
              >
                <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: '2px' }}>
                  #{ev.id} {ev.department_ja}
                  {ev.translation_edited ? ' ✏️' : ''}
                </div>
                <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{ev.title_ja}</div>
                {ev.title_en && (
                  <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>{ev.title_en}</div>
                )}
              </div>
            ))}
          </div>

          {/* Translation form */}
          {selected ? (
            <div className="admin-form">
              <div style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: '0.5rem' }}>
                編集中: <strong>{selected.title_ja}</strong>
              </div>

              {[
                { key: 'title_en', label: 'Title (EN)' },
                { key: 'department_en', label: 'Department (EN)' },
                { key: 'venue_en', label: 'Venue (EN)' },
                { key: 'target_audience_en', label: 'Target Audience (EN)' },
                { key: 'researchers_en', label: 'Researchers (EN, comma-separated)' },
              ].map(({ key, label }) => (
                <div key={key} className="admin-field">
                  <label className="admin-field__label" htmlFor={`admin-${key}`}>{label}</label>
                  <input
                    id={`admin-${key}`}
                    className="admin-field__input"
                    value={form[key] || ''}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  />
                </div>
              ))}

              <div className="admin-field">
                <label className="admin-field__label" htmlFor="admin-description-en">Description (EN)</label>
                <textarea
                  id="admin-description-en"
                  className="admin-field__textarea"
                  value={form.description_en || ''}
                  onChange={(e) => setForm({ ...form, description_en: e.target.value })}
                />
              </div>

              <button id="admin-save-btn" className="btn-primary" onClick={save}>{t('admin_save')}</button>
            </div>
          ) : (
            <div style={{ color: 'var(--color-text-muted)', padding: '2rem', textAlign: 'center' }}>
              ← 左のリストから企画を選んでください
            </div>
          )}
        </div>
      </div>

      {toast && <div className="toast" role="alert">{toast}</div>}
    </div>
  );
}
