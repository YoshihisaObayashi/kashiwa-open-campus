import ja from './ja.json';
import en from './en.json';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

i18n
  .use(initReactI18next)
  .init({
    resources: { ja: { translation: ja }, en: { translation: en } },
    lng: localStorage.getItem('lang') || 'ja',
    fallbackLng: 'ja',
    interpolation: { escapeValue: false },
  });

export default i18n;
