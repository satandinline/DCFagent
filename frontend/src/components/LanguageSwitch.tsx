import { Segmented } from 'antd';
import { useTranslation } from 'react-i18next';
import { useStore } from '@/store/useStore';
import type { Language } from '@/types';

const options = [
  { label: '中文', value: 'zh' as Language },
  { label: 'EN', value: 'en' as Language },
];

export default function LanguageSwitch() {
  const { i18n } = useTranslation();
  const { language, setLanguage } = useStore();

  const handleChange = (value: string | number) => {
    const lang = value as Language;
    setLanguage(lang);
    i18n.changeLanguage(lang);
  };

  return (
    <Segmented
      size="small"
      options={options}
      value={language}
      onChange={handleChange}
    />
  );
}
