import { useState } from 'react';
import { Upload, Form, InputNumber, Input, Button, Card, message, Spin } from 'antd';
import { InboxOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { useStore } from '@/store/useStore';
import { uploadPDF } from '@/services/api';
import type { FinancialData } from '@/types';
import type { UploadFile, UploadProps } from 'antd/es/upload';

const { Dragger } = Upload;

export default function FileUpload() {
  const { t } = useTranslation();
  const { setFinancialData, setExtractedText, setLoading, setError } = useStore();

  const [uploading, setUploading] = useState(false);
  const [extracted, setExtracted] = useState<FinancialData | null>(null);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [form] = Form.useForm<FinancialData>();

  const handleUpload = async (file: File) => {
    setUploading(true);
    setLoading(true);
    setError('');
    try {
      const response = await uploadPDF(file);
      if (response.success && response.financial_data) {
        setExtracted(response.financial_data);
        setFinancialData(response.financial_data);
        form.setFieldsValue(response.financial_data);
        if (response.extracted_text) {
          setExtractedText(response.extracted_text);
        }
        message.success(t('common.success'));
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

  return (
    <div className="space-y-6">
      <Card>
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
                  {group.fields.map((field) => (
                    <Form.Item key={field} name={field} label={t(`analysis.fields.${field}`)}>
                      {stringFields.has(field) ? (
                        <Input />
                      ) : (
                        <InputNumber className="!w-full" />
                      )}
                    </Form.Item>
                  ))}
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
