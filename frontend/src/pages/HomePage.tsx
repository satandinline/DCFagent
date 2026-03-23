import { useNavigate } from 'react-router-dom';
import { Button, Typography } from 'antd';
import {
  FileSearchOutlined,
  CalculatorOutlined,
  HeatMapOutlined,
  RobotOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { Title, Paragraph } = Typography;

const featureIcons = [
  <FileSearchOutlined key="extract" />,
  <CalculatorOutlined key="dcf" />,
  <HeatMapOutlined key="sensitivity" />,
  <RobotOutlined key="narrative" />,
];

const featureKeys = ['auto_extract', 'dcf_model', 'sensitivity', 'ai_narrative'] as const;

export default function HomePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div className="relative overflow-hidden">
      {/* Animated gradient background */}
      <div className="absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/2 w-[200%] h-[200%] animate-[gradientShift_12s_ease_infinite] bg-[length:200%_200%] bg-gradient-to-br from-primary-500/10 via-accent-light/10 to-primary-300/10 dark:from-primary-900/30 dark:via-accent-dark/20 dark:to-primary-700/20" />
      </div>

      {/* Hero Section */}
      <section className="flex flex-col items-center justify-center text-center pt-16 pb-20 px-4 md:pt-24 md:pb-28">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-6 rounded-full bg-primary-500/10 dark:bg-primary-300/15 border border-primary-500/20 dark:border-primary-300/25">
          <CalculatorOutlined className="text-primary-500 dark:text-primary-300 text-sm" />
          <span className="text-xs font-medium text-primary-700 dark:text-primary-300 tracking-wide">
            AI-Powered Valuation
          </span>
        </div>

        <Title
          level={1}
          className="!mb-4 !leading-tight"
          style={{
            fontSize: 'clamp(2rem, 5vw, 3.5rem)',
            fontWeight: 800,
            background: 'linear-gradient(135deg, #1a365d 0%, #2b6cb0 40%, #d69e2e 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}
        >
          {t('home.hero_title')}
        </Title>

        <Paragraph className="!text-lg md:!text-xl !text-gray-500 dark:!text-gray-400 max-w-2xl !mb-3">
          {t('home.subtitle')}
        </Paragraph>

        <Paragraph className="!text-sm md:!text-base !text-gray-400 dark:!text-gray-500 max-w-xl !mb-10">
          {t('home.description')}
        </Paragraph>

        <Button
          type="primary"
          size="large"
          icon={<ArrowRightOutlined />}
          onClick={() => navigate('/analysis')}
          className="!h-12 !px-8 !text-base !font-semibold !rounded-xl hover:!scale-105 transition-transform"
          style={{
            background: 'linear-gradient(135deg, #2b6cb0, #3182ce)',
            boxShadow: '0 4px 20px rgba(43, 108, 176, 0.35)',
          }}
        >
          {t('home.cta')}
        </Button>
      </section>

      {/* Feature Cards */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 pb-16 px-2">
        {featureKeys.map((key, idx) => (
          <div
            key={key}
            className="group relative p-6 rounded-2xl border border-white/60 dark:border-white/10
                       bg-white/50 dark:bg-white/5 backdrop-blur-lg
                       shadow-card hover:shadow-card-hover
                       transition-all duration-300 hover:-translate-y-1 cursor-default"
          >
            <div className="flex items-center justify-center w-12 h-12 mb-4 rounded-xl bg-primary-500/10 dark:bg-primary-300/15 text-primary-500 dark:text-primary-300 text-2xl group-hover:scale-110 transition-transform">
              {featureIcons[idx]}
            </div>
            <h3 className="text-base font-semibold mb-2 text-gray-800 dark:text-gray-100">
              {t(`home.features.${key}.title`)}
            </h3>
            <p className="text-sm leading-relaxed text-gray-500 dark:text-gray-400">
              {t(`home.features.${key}.description`)}
            </p>
            {/* Hover glow */}
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary-500/0 to-accent/0 group-hover:from-primary-500/5 group-hover:to-accent/5 transition-all duration-300 pointer-events-none" />
          </div>
        ))}
      </section>

      {/* Inline keyframes */}
      <style>{`
        @keyframes gradientShift {
          0%, 100% { transform: translate(0, 0) rotate(0deg); }
          33%      { transform: translate(-5%, 5%) rotate(1deg); }
          66%      { transform: translate(5%, -3%) rotate(-1deg); }
        }
      `}</style>
    </div>
  );
}
