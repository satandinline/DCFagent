import { useState } from 'react';
import { Upload, Form, InputNumber, Input, Button, Card, App, Spin, Space } from 'antd';
import { InboxOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useStore } from '@/store/useStore';
import { uploadPDF } from '@/services/api';
import type { FinancialData } from '@/types';
import type { UploadFile, UploadProps } from 'antd/es/upload';

const { Dragger } = Upload;

// 百分比字段列表
const percentFields: (keyof FinancialData)[] = ['revenue_growth', 'operating_margin', 'tax_rate', 'risk_free_rate', 'market_return', 'cost_of_debt'];

// 将百分比字段从后端返回的小数格式转换为前端显示的百分比格式
const convertPercentFieldsToDisplay = (data: FinancialData): FinancialData => {
  const converted = { ...data };
  for (const field of percentFields) {
    if (converted[field] != null && typeof converted[field] === 'number') {
      (converted as Record<string, number | string | undefined>)[field] = converted[field] * 100;
    }
  }
  return converted;
};

// 字段配置，包含单位后缀
interface FieldConfig {
  name: keyof FinancialData;
  suffix?: string;  // 单位后缀
  isPercent?: boolean;  // 是否是百分比
}

const fieldConfigs: FieldConfig[] = [
  // 公司信息
  { name: 'company_name' },
  { name: 'ticker' },
  { name: 'currency' },
  { name: 'fiscal_year' },
  // 收入相关
  { name: 'revenue', suffix: '万' },
  { name: 'revenue_growth', isPercent: true },
  { name: 'operating_income', suffix: '万' },
  { name: 'operating_margin', isPercent: true },
  { name: 'net_income', suffix: '万' },
  // 资本结构
  { name: 'depreciation_amortization', suffix: '万' },
  { name: 'capital_expenditure', suffix: '万' },
  { name: 'change_in_working_capital', suffix: '万' },
  // 债务与权益
  { name: 'total_debt', suffix: '万' },
  { name: 'cash_and_equivalents', suffix: '万' },
  { name: 'shares_outstanding', suffix: '万股' },
  // 市场数据
  { name: 'tax_rate', isPercent: true },
  { name: 'beta' },
  { name: 'risk_free_rate', isPercent: true },
  { name: 'market_return', isPercent: true },
  { name: 'cost_of_debt', isPercent: true },
  { name: 'current_stock_price', suffix: '元' },
];

export default function FileUpload() {
  const { t } = useTranslation();
  const { setFinancialData, setExtractedText, setLoading, setError } = useStore();
  const { message } = App.useApp();

  const [uploading, setUploading] = useState(false);
  const [extracted, setExtracted] = useState<FinancialData | null>(null);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [form] = Form.useForm<FinancialData>();
  
  // RAG parameters
  const [companyName, setCompanyName] = useState('');
  const [ticker, setTicker] = useState('');

  const handleUpload = async (file: File) => {
    setUploading(true);
    setLoading(true);
    setError('');
    try {
      console.log('开始上传文件:', file.name);
      const response = await uploadPDF(
        file,
        companyName || undefined,
        ticker || undefined,
        true,  // useRag
        true   // useWebSearch
      );
      console.log('上传响应:', response);
      if (response.success && response.financial_data) {
        console.log('解析后的财务数据:', response.financial_data);
        // 转换百分比字段为显示格式
        const displayData = convertPercentFieldsToDisplay(response.financial_data);
        setExtracted(displayData);
        setFinancialData(displayData);
        form.setFieldsValue(displayData);
        if (response.extracted_text) {
          setExtractedText(response.extracted_text);
        }
        message.success(t('upload.upload_success'));
      } else {
        const errMsg = response.error ?? t('common.error');
        setError(errMsg);
        message.error(errMsg);
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : t('common.error');
      setError(errMsg);
      message.error(errMsg);
    } finally {
      setUploading(false);
      setLoading(false);
    }
  };

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.pdf',
    fileList,
    beforeUpload(file) {
      setFileList([file as UploadFile]);
      handleUpload(file);
      return false;
    },
    onRemove() {
      setFileList([]);
      setExtracted(null);
      setFinancialData(null);
      form.resetFields();
    },
  };

  const handleFormChange = (_: unknown, allValues: FinancialData) => {
    // 将百分比字段转换为显示格式（已在form中输入的是百分比格式，这里确保一致性）
    setFinancialData(allValues);
  };

  const fieldGroups: { title: string; fields: (keyof FinancialData)[] }[] = [
    {
      title: t('analysis.fields.company_name'),
      fields: ['company_name', 'ticker', 'currency', 'fiscal_year'],
    },
    {
      title: t('analysis.fields.revenue'),
      fields: ['revenue', 'revenue_growth', 'operating_income', 'operating_margin', 'net_income'],
    },
    {
      title: t('analysis.fields.depreciation_amortization'),
      fields: ['depreciation_amortization', 'capital_expenditure', 'change_in_working_capital'],
    },
    {
      title: t('analysis.fields.total_debt'),
      fields: ['total_debt', 'cash_and_equivalents', 'shares_outstanding'],
    },
    {
      title: t('analysis.fields.beta'),
      fields: ['tax_rate', 'beta', 'risk_free_rate', 'market_return', 'cost_of_debt', 'current_stock_price'],
    },
  ];

  const stringFields = new Set<string>(['company_name', 'ticker', 'currency']);

  // 根据字段名获取配置
  const getFieldConfig = (fieldName: string): FieldConfig | undefined => {
    return fieldConfigs.find(f => f.name === fieldName);
  };

  return (
    <div className="space-y-6">
      <Card>
        {/* RAG Input Section */}
        <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <h4 className="text-sm font-semibold mb-3 text-gray-700 dark:text-gray-300">
            {t('upload.rag_title')}
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('upload.company_name')}
              </label>
              <Input
                placeholder={t('upload.company_name_placeholder')}
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                disabled={uploading}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('upload.ticker_optional')}
              </label>
              <Input
                placeholder={t('upload.ticker_placeholder')}
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                disabled={uploading}
              />
              <p className="text-xs text-gray-500 mt-1">
                {t('upload.ticker_hint')}
              </p>
            </div>
          </div>
        </div>
        
        <Dragger {...uploadProps} disabled={uploading}>
          <Spin spinning={uploading}>
            <p className="ant-upload-drag-icon">
              {extracted ? (
                <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
              ) : (
                <InboxOutlined style={{ fontSize: 48 }} />
              )}
            </p>
            <p className="ant-upload-text">{t('analysis.upload.drag_text')}</p>
            <p className="ant-upload-hint">{t('analysis.upload.hint')}</p>
          </Spin>
        </Dragger>
      </Card>

      {extracted && (
        <Card title={t('analysis.upload.title')} className="animate-fade-in">
          <Form
            form={form}
            layout="vertical"
            initialValues={extracted}
            onValuesChange={handleFormChange}
          >
            {fieldGroups.map((group) => (
              <div key={group.title} className="mb-6">
                <h4 className="text-base font-semibold mb-3 text-gray-700 dark:text-gray-300 border-b pb-2">
                  {group.title}
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-6">
                  {group.fields.map((field) => {
                    const config = getFieldConfig(field);
                    const suffix = config?.suffix || (config?.isPercent ? '%' : undefined);
                    
                    return (
                    <Form.Item key={field} name={field} label={t(`analysis.fields.${field}`)}>
                      {stringFields.has(field) ? (
                        <Input />
                      ) : suffix ? (
                        <Space.Compact className="!w-full">
                          <InputNumber className="!w-full" />
                          <Input
                            className="!w-16 text-center"
                            value={suffix}
                            disabled
                            readOnly
                          />
                        </Space.Compact>
                      ) : (
                        <InputNumber className="!w-full" />
                      )}
                    </Form.Item>
                    );
                  })}
                </div>
              </div>
            ))}
            <Form.Item>
              <Button
                type="primary"
                onClick={() => {
                  const values = form.getFieldsValue(true);
                  setFinancialData(values);
                  message.success(t('common.success'));
                }}
              >
                {t('common.save')}
              </Button>
            </Form.Item>
          </Form>
        </Card>
      )}
    </div>
  );
}
