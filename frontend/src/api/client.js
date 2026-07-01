import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({ baseURL: BASE_URL });

export const fetchEvents = (params) =>
  api.get('/api/events', { params }).then((r) => r.data);

export const fetchEvent = (id) =>
  api.get(`/api/events/${id}`).then((r) => r.data);

export const fetchDepartments = (lang) =>
  api.get('/api/departments', { params: { lang } }).then((r) => r.data.departments);

export const fetchStats = () =>
  api.get('/api/stats').then((r) => r.data);

export const patchTranslation = (id, updates, apiKey) =>
  api.patch(`/api/admin/events/${id}`, updates, {
    headers: { 'X-API-Key': apiKey },
  }).then((r) => r.data);

export const triggerRefresh = (apiKey) =>
  api.post('/api/admin/refresh', {}, {
    headers: { 'X-API-Key': apiKey },
  }).then((r) => r.data);
