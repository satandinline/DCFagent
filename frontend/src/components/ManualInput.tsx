import { useEffect } from 'react';
import { Form, Input, InputNumber, Card, Button, Space, App } from 'antd';
import { useTranslation } from 'react-i18next';
import { useStore } from '@/store/useStore';
import type { FinancialData } from '@/types';

const defaultValues: Partial<FinancialData> = {
  company_name: '',
  ticker: '',
  currency: 'CNY',
  fiscal_year: new Date().getFullYear() - 1,
  revenue: 0,
  revenue_growth: 5,      // 百分比格式
  operating_income: 0,
  operating_margin: 15,   // 百分比格式
  net_income: 0,
  depreciation_amortization: 0,
  capital_expenditure: 0,
  change_in_working_capital: 0,
  total_debt: 0,
  cash_and_equivalents: 0,
  shares_outstanding: 0,
  tax_rate: 25,           // 百分比格式
  beta: 1.0,
  risk_free_rate: 3,      // 百分比格式
  market_return: 9,       // 百分比格式
  cost_of_debt: 5,        // 百分比格式
  current_stock_price: 0,
};

interface FieldDef {
  name: keyof FinancialData;
  type: 'text' | 'number';
  min?: number;
  max?: number;
  step?: number;
  suffix?: string;  // 单位后缀
  addonAfter?: string;
}

const sections: { titleKey: string; fields: FieldDef[] }[] = [
  {
    titleKey: 'company_info',
    fields: [
      { name: 'company_name', type: 'text' },
      { name: 'ticker', type: 'text' },
      { name: 'currency', type: 'text' },
      { name: 'fiscal_year', type: 'number', min: 1990, max: 2100, step: 1 },
    ],
  },
  {
    titleKey: 'revenue',
    fields: [
      { name: 'revenue', type: 'number', min: 0, suffix: '万' },
      { name: 'revenue_growth', type: 'number', min: -100, max: 1000, step: 0.1, addonAfter: '%' },
      { name: 'operating_income', type: 'number', suffix: '万' },
      { name: 'operating_margin', type: 'number', min: -100, max: 100, step: 0.1, addonAfter: '%' },
      { name: 'net_income', type: 'number', suffix: '万' },
    ],
  },
  {
    titleKey: 'capital_structure',
    fields: [
      { name: 'depreciation_amortization', type: 'number', min: 0, suffix: '万' },
      { name: 'capital_expenditure', type: 'number', min: 0, suffix: '万' },
      { name: 'change_in_working_capital', type: 'number', suffix: '万' },
    ],
  },
  {
    titleKey: 'debt_and_equity',
    fields: [
      { name: 'total_debt', type: 'number', min: 0, suffix: '万' },
      { name: 'cash_and_equivalents', type: 'number', min: 0, suffix: '万' },
      { name: 'shares_outstanding', type: 'number', min: 0, suffix: '万股' },
    ],
  },
  {
    titleKey: 'market_data',
    fields: [
      { name: 'tax_rate', type: 'number', min: 0, max: 100, step: 0.1, addonAfter: '%' },
      { name: 'beta', type: 'number', min: 0, max: 5, step: 0.01 },
      { name: 'risk_free_rate', type: 'number', min: 0, max: 20, step: 0.01, addonAfter: '%' },
      { name: 'market_return', type: 'number', min: 0, max: 30, step: 0.01, addonAfter: '%' },
      { name: 'cost_of_debt', type: 'number', min: 0, max: 30, step: 0.01, addonAfter: '%' },
      { name: 'current_stock_price', type: 'number', min: 0, suffix: '元' },
    ],
  },
];

const sectionTitles: Record<string, string> = {
  company_info: 'analysis.fields.company_name',
  revenue: 'analysis.fields.revenue',
  capital_structure: 'analysis.fields.depreciation_amortization',
  debt_and_equity: 'analysis.fields.total_debt',
  market_data: 'analysis.fields.beta',
};

export default function ManualInput() {
  const { t } = useTranslation();
  const { financialData, setFinancialData } = useStore();
  const [form] = Form.useForm<FinancialData>();
  const { message } = App.useApp();

  useEffect(() => {
    if (financialData) {
      form.setFieldsValue(financialData);
    }
  }, [financialData, form]);

  const handleValuesChange = (_: unknown, allValues: FinancialData) => {
    setFinancialData(allValues);
  };

  const handleSubmit = () => {
    form.validateFields().then((values) => {
      setFinancialData(values);
      message.success(t('common.success'));
    });
  };

  const handleReset = () => {
    form.setFieldsValue(defaultValues as FinancialData);
    setFinancialData(defaultValues as FinancialData);
  };

  return (
    <>
      {/* 单位说明提示 */}
      <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
        <p className="text-sm text-amber-800 dark:text-amber-200 m-0">
          {t('analysis.manual.unit_hint')}
        </p>
      </div>
      
      <Form
        form={form}
        layout="vertical"
        initialValues={financialData ?? defaultValues}
        onValuesChange={handleValuesChange}
        className="space-y-4"
      >
      {sections.map((section) => (
        <Card
          key={section.titleKey}
          title={t(sectionTitles[section.titleKey])}
          size="small"
          className="shadow-sm"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-6">
            {section.fields.map((field) => (
              <Form.Item
                key={field.name}
                name={field.name}
                label={t(`analysis.fields.${field.name}`)}
                rules={
                  field.name === 'company_name'
                    ? [{ required: true, message: t('common.error') }]
                    : undefined
                }
              >
                {field.type === 'text' ? (
                  <Input />
                ) : field.addonAfter ? (
                  <Space.Compact className="!w-full">
                    <InputNumber
                      className="!w-full"
                      min={field.min}
                      max={field.max}
                      step={field.step}
                    />
                    <Input
                      className="!w-14 text-center"
                      value={field.addonAfter}
                      disabled
                      readOnly
                    />
                  </Space.Compact>
                ) : field.suffix ? (
                  <Space.Compact className="!w-full">
                    <InputNumber
                      className="!w-full"
                      min={field.min}
                      max={field.max}
                      step={field.step}
                    />
                    <Input
                      className="!w-16 text-center"
                      value={field.suffix}
                      disabled
                      readOnly
                    />
                  </Space.Compact>
                ) : (
                  <InputNumber
                    className="!w-full"
                    min={field.min}
                    max={field.max}
                    step={field.step}
                  />
                )}
              </Form.Item>
            ))}
          </div>
        </Card>
      ))}

      <div className="flex gap-3 pt-2">
        <Button type="primary" onClick={handleSubmit}>
          {t('common.save')}
        </Button>
        <Button onClick={handleReset}>{t('common.reset')}</Button>
      </div>
      </Form>
    </>
  );
}
