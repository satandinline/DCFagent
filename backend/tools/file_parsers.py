"""
File Parser Tools for DCF Valuation Agent
Supports parsing various file types: PDF, Excel, Word, CSV, JSON, XML, etc.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import time
import json

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.tools.base import (
    BaseTool, ToolCategory, ToolResult, FileType,
    ToolParameter, ToolCapability
)

logger = logging.getLogger(__name__)


# =============================================================================
# PDF Parser Tool
# =============================================================================

class PDFParserTool(BaseTool):
    """
    Tool for extracting text and data from PDF files
    Supports financial reports, annual reports, etc.
    """
    
    @property
    def name(self) -> str:
        return "pdf_parser"
    
    @property
    def description(self) -> str:
        return "从PDF文件中提取文本和数据，特别适合财务报告、年报、招股说明书等金融文档"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE_PARSER
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.PARSE_PDF]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="file_path",
                type="string",
                description="PDF文件的完整路径",
                required=True
            ),
            ToolParameter(
                name="extract_tables",
                type="boolean",
                description="是否提取表格数据",
                required=False,
                default=True
            ),
            ToolParameter(
                name="pages",
                type="string",
                description="要提取的页面范围，如'1-5'或'all'",
                required=False,
                default="all"
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        file_path = kwargs.get('file_path')
        extract_tables = kwargs.get('extract_tables', True)
        pages = kwargs.get('pages', 'all')
        
        try:
            import pdfplumber
            import pymupdf
            
            extracted_data = {
                'text': '',
                'tables': [],
                'metadata': {},
                'page_count': 0
            }
            
            # Get metadata
            with pymupdf.open(file_path) as doc:
                extracted_data['page_count'] = len(doc)
                extracted_data['metadata'] = {
                    'title': doc.metadata.get('title', ''),
                    'author': doc.metadata.get('author', ''),
                    'subject': doc.metadata.get('subject', ''),
                    'creator': doc.metadata.get('creator', '')
                }
            
            # Extract text and tables
            with pdfplumber.open(file_path) as pdf:
                all_text = []
                
                for i, page in enumerate(pdf.pages):
                    # Check page range
                    if pages != 'all':
                        try:
                            start, end = map(int, pages.split('-'))
                            if i + 1 < start or i + 1 > end:
                                continue
                        except:
                            pass
                    
                    # Extract text
                    page_text = page.extract_text() or ''
                    all_text.append(page_text)
                    
                    # Extract tables
                    if extract_tables:
                        page_tables = page.extract_tables()
                        for table in page_tables:
                            if table:
                                extracted_data['tables'].append({
                                    'page': i + 1,
                                    'data': table
                                })
                
                extracted_data['text'] = '\n\n'.join(all_text)
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data=extracted_data,
                metadata={
                    'file_path': file_path,
                    'file_type': 'pdf',
                    'pages_extracted': pages
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"PDF parsing error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Excel Parser Tool
# =============================================================================

class ExcelParserTool(BaseTool):
    """
    Tool for extracting data from Excel files (.xlsx, .xls)
    Supports financial models, data tables, etc.
    """
    
    @property
    def name(self) -> str:
        return "excel_parser"
    
    @property
    def description(self) -> str:
        return "从Excel文件中提取数据，支持财务模型、数据表格、多sheet工作簿等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE_PARSER
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.PARSE_EXCEL]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="file_path",
                type="string",
                description="Excel文件的完整路径",
                required=True
            ),
            ToolParameter(
                name="sheet_name",
                type="string",
                description="要读取的工作表名称，为空则读取所有工作表",
                required=False,
                default=None
            ),
            ToolParameter(
                name="header_row",
                type="integer",
                description="表头所在行号（0-based），为None则无表头",
                required=False,
                default=0
            ),
            ToolParameter(
                name="max_rows",
                type="integer",
                description="最大读取行数，0表示不限制",
                required=False,
                default=0
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        file_path = kwargs.get('file_path')
        sheet_name = kwargs.get('sheet_name')
        header_row = kwargs.get('header_row', 0)
        max_rows = kwargs.get('max_rows', 0)
        
        try:
            import openpyxl
            
            extracted_data = {
                'sheets': {},
                'sheet_names': [],
                'metadata': {}
            }
            
            # Get workbook metadata
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            extracted_data['sheet_names'] = wb.sheetnames
            
            # Get first sheet metadata
            if wb.sheetnames:
                first_sheet = wb[wb.sheetnames[0]]
                extracted_data['metadata'] = {
                    'total_sheets': len(wb.sheetnames),
                    'first_sheet_rows': first_sheet.max_row,
                    'first_sheet_cols': first_sheet.max_column
                }
            
            # Read sheets
            sheets_to_read = [sheet_name] if sheet_name else wb.sheetnames
            
            for name in sheets_to_read:
                if name not in wb.sheetnames:
                    continue
                
                ws = wb[name]
                rows_data = []
                
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    if max_rows > 0 and i >= max_rows:
                        break
                    rows_data.append(list(row))
                
                # Convert to list of dicts if header exists
                if header_row is not None and header_row >= 0 and len(rows_data) > header_row:
                    headers = rows_data[header_row]
                    data_rows = rows_data[header_row + 1:]
                    rows_as_dicts = []
                    for row in data_rows:
                        row_dict = {}
                        for j, header in enumerate(headers):
                            if j < len(row):
                                header_key = str(header) if header else f"col_{j}"
                                row_dict[header_key] = row[j]
                        rows_as_dicts.append(row_dict)
                    extracted_data['sheets'][name] = {
                        'headers': headers,
                        'data': rows_as_dicts,
                        'row_count': len(rows_as_dicts)
                    }
                else:
                    extracted_data['sheets'][name] = {
                        'data': rows_data,
                        'row_count': len(rows_data)
                    }
            
            wb.close()
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data=extracted_data,
                metadata={
                    'file_path': file_path,
                    'file_type': 'excel',
                    'sheets_read': len(sheets_to_read)
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Excel parsing error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Word Parser Tool
# =============================================================================

class WordParserTool(BaseTool):
    """
    Tool for extracting text from Word documents (.docx, .doc)
    Supports reports, documents, etc.
    """
    
    @property
    def name(self) -> str:
        return "word_parser"
    
    @property
    def description(self) -> str:
        return "从Word文档中提取文本，支持.docx和.doc格式的报告和文档"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE_PARSER
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.PARSE_WORD]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="file_path",
                type="string",
                description="Word文档的完整路径",
                required=True
            ),
            ToolParameter(
                name="extract_tables",
                type="boolean",
                description="是否提取表格数据",
                required=False,
                default=True
            ),
            ToolParameter(
                name="extract_images",
                type="boolean",
                description="是否提取图像描述",
                required=False,
                default=False
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        file_path = kwargs.get('file_path')
        extract_tables = kwargs.get('extract_tables', True)
        extract_images = kwargs.get('extract_images', False)
        
        try:
            from docx import Document
            
            doc = Document(file_path)
            
            extracted_data = {
                'text': '',
                'paragraphs': [],
                'tables': [],
                'metadata': {},
                'styles': set()
            }
            
            # Extract paragraphs
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    extracted_data['paragraphs'].append({
                        'text': text,
                        'style': para.style.name if para.style else 'Normal'
                    })
                    extracted_data['styles'].add(para.style.name if para.style else 'Normal')
            
            # Combine all text
            extracted_data['text'] = '\n'.join(p['text'] for p in extracted_data['paragraphs'])
            
            # Extract tables
            if extract_tables:
                for i, table in enumerate(doc.tables):
                    table_data = []
                    for row in table.rows:
                        row_data = [cell.text.strip() for cell in row.cells]
                        table_data.append(row_data)
                    extracted_data['tables'].append({
                        'index': i,
                        'data': table_data,
                        'rows': len(table_data),
                        'cols': len(table_data[0]) if table_data else 0
                    })
            
            # Extract document properties
            core_props = doc.core_properties
            extracted_data['metadata'] = {
                'title': core_props.title or '',
                'author': core_props.author or '',
                'subject': core_props.subject or '',
                'created': str(core_props.created) if core_props.created else None,
                'modified': str(core_props.modified) if core_props.modified else None,
                'paragraph_count': len(extracted_data['paragraphs']),
                'table_count': len(extracted_data['tables'])
            }
            
            extracted_data['styles'] = list(extracted_data['styles'])
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data=extracted_data,
                metadata={
                    'file_path': file_path,
                    'file_type': 'word'
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Word parsing error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# CSV Parser Tool
# =============================================================================

class CSVParserTool(BaseTool):
    """
    Tool for reading and parsing CSV files
    Supports financial data, historical prices, etc.
    """
    
    @property
    def name(self) -> str:
        return "csv_parser"
    
    @property
    def description(self) -> str:
        return "读取和解析CSV文件，适合金融数据、历史股价等表格数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE_PARSER
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.PARSE_CSV]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="file_path",
                type="string",
                description="CSV文件的完整路径",
                required=True
            ),
            ToolParameter(
                name="delimiter",
                type="string",
                description="分隔符，默认逗号",
                required=False,
                default=","
            ),
            ToolParameter(
                name="has_header",
                type="boolean",
                description="第一行是否为表头",
                required=False,
                default=True
            ),
            ToolParameter(
                name="encoding",
                type="string",
                description="文件编码，默认utf-8",
                required=False,
                default="utf-8"
            ),
            ToolParameter(
                name="max_rows",
                type="integer",
                description="最大读取行数，0表示不限制",
                required=False,
                default=0
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        file_path = kwargs.get('file_path')
        delimiter = kwargs.get('delimiter', ',')
        has_header = kwargs.get('has_header', True)
        encoding = kwargs.get('encoding', 'utf-8')
        max_rows = kwargs.get('max_rows', 0)
        
        try:
            import csv
            
            extracted_data = {
                'headers': [],
                'rows': [],
                'row_count': 0,
                'metadata': {}
            }
            
            with open(file_path, 'r', encoding=encoding, newline='') as f:
                reader = csv.reader(f, delimiter=delimiter)
                
                rows = list(reader)
                total_rows = len(rows)
                
                if has_header and rows:
                    extracted_data['headers'] = rows[0]
                    data_rows = rows[1:]
                else:
                    data_rows = rows
                
                # Apply max_rows
                if max_rows > 0:
                    data_rows = data_rows[:max_rows]
                
                # Convert to list of dicts if has header
                if has_header and extracted_data['headers']:
                    for row in data_rows:
                        row_dict = {}
                        for j, header in enumerate(extracted_data['headers']):
                            if j < len(row):
                                row_dict[header] = row[j]
                        extracted_data['rows'].append(row_dict)
                else:
                    extracted_data['rows'] = data_rows
                
                extracted_data['row_count'] = len(extracted_data['rows'])
                extracted_data['metadata'] = {
                    'total_rows': total_rows,
                    'has_header': has_header,
                    'columns': len(extracted_data['headers']) if has_header else (len(data_rows[0]) if data_rows else 0)
                }
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data=extracted_data,
                metadata={
                    'file_path': file_path,
                    'file_type': 'csv'
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"CSV parsing error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# JSON Parser Tool
# =============================================================================

class JSONParserTool(BaseTool):
    """
    Tool for reading and parsing JSON files
    Supports configuration files, API responses, etc.
    """
    
    @property
    def name(self) -> str:
        return "json_parser"
    
    @property
    def description(self) -> str:
        return "读取和解析JSON文件，支持配置文件、API响应等结构化数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE_PARSER
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.PARSE_JSON]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="file_path",
                type="string",
                description="JSON文件的完整路径",
                required=True
            ),
            ToolParameter(
                name="key_path",
                type="string",
                description="要提取的JSON路径，如'data.results[0].name'",
                required=False,
                default=None
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        file_path = kwargs.get('file_path')
        key_path = kwargs.get('key_path')
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Navigate to key_path if specified
            if key_path:
                keys = key_path.replace('[', '.').replace(']', '').split('.')
                for key in keys:
                    if key.isdigit() and isinstance(data, list):
                        index = int(key)
                        data = data[index] if index < len(data) else None
                    elif isinstance(data, dict):
                        data = data.get(key)
                    else:
                        data = None
                    if data is None:
                        break
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data=data,
                metadata={
                    'file_path': file_path,
                    'file_type': 'json',
                    'key_path': key_path
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"JSON parsing error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# XML Parser Tool
# =============================================================================

class XMLParserTool(BaseTool):
    """
    Tool for reading and parsing XML files
    Supports financial reports, SEC filings, etc.
    """
    
    @property
    def name(self) -> str:
        return "xml_parser"
    
    @property
    def description(self) -> str:
        return "读取和解析XML文件，支持财务报告、SEC文件等结构化数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE_PARSER
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.PARSE_XML]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="file_path",
                type="string",
                description="XML文件的完整路径",
                required=True
            ),
            ToolParameter(
                name="xpath",
                type="string",
                description="XPATH表达式，用于提取特定元素",
                required=False,
                default=None
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        file_path = kwargs.get('file_path')
        xpath = kwargs.get('xpath')
        
        try:
            import xml.etree.ElementTree as ET
            
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            if xpath:
                elements = root.findall(xpath)
                data = [elem.text if elem.text else elem.attrib for elem in elements]
            else:
                # Convert entire tree to dict
                data = self._element_to_dict(root)
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data=data,
                metadata={
                    'file_path': file_path,
                    'file_type': 'xml',
                    'root_tag': root.tag
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"XML parsing error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )
    
    def _element_to_dict(self, element) -> dict:
        """Convert XML element to dictionary"""
        result = {}
        if element.attrib:
            result['@attributes'] = element.attrib
        if element.text and element.text.strip():
            result['text'] = element.text.strip()
        for child in element:
            child_data = self._element_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        return result


# =============================================================================
# Universal File Parser Tool
# =============================================================================

class UniversalFileParserTool(BaseTool):
    """
    Universal file parser that automatically detects file type and parses accordingly
    Simplifies tool selection for workflows
    """
    
    @property
    def name(self) -> str:
        return "universal_file_parser"
    
    @property
    def description(self) -> str:
        return "通用文件解析器，自动识别文件类型（PDF/Excel/Word/CSV/JSON/XML）并解析"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE_PARSER
    
    @property
    def capabilities(self) -> List[str]:
        return [
            ToolCapability.PARSE_PDF,
            ToolCapability.PARSE_EXCEL,
            ToolCapability.PARSE_WORD,
            ToolCapability.PARSE_CSV,
            ToolCapability.PARSE_JSON,
            ToolCapability.PARSE_XML
        ]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="file_path",
                type="string",
                description="要解析的文件路径",
                required=True
            ),
            ToolParameter(
                name="file_type_hint",
                type="string",
                description="文件类型提示：pdf, excel, word, csv, json, xml, auto（自动检测）",
                required=False,
                default="auto"
            )
        ]
        
        # Initialize specific parsers
        self._parsers = {
            'pdf': PDFParserTool(),
            'excel': ExcelParserTool(),
            'word': WordParserTool(),
            'csv': CSVParserTool(),
            'json': JSONParserTool(),
            'xml': XMLParserTool()
        }
    
    def execute(self, **kwargs) -> ToolResult:
        file_path = kwargs.get('file_path')
        file_type_hint = kwargs.get('file_type_hint', 'auto').lower()
        
        # Detect file type
        if file_type_hint == 'auto':
            file_type = self._detect_file_type(file_path)
        else:
            file_type = file_type_hint
        
        # Get appropriate parser
        parser = self._parsers.get(file_type)
        if not parser:
            return ToolResult(
                success=False,
                error=f"Unsupported file type: {file_type}",
                tool_name=self.name
            )
        
        # Execute with appropriate parser
        return parser.execute(file_path=file_path)
    
    def _detect_file_type(self, file_path: str) -> str:
        """Auto-detect file type from extension"""
        ext = Path(file_path).suffix.lower().replace('.', '')
        
        type_map = {
            'pdf': 'pdf',
            'xlsx': 'excel',
            'xls': 'excel',
            'docx': 'word',
            'doc': 'word',
            'csv': 'csv',
            'json': 'json',
            'xml': 'xml'
        }
        
        return type_map.get(ext, 'unknown')


# =============================================================================
# Register all file parser tools
# =============================================================================

def register_file_parser_tools():
    """Register all file parser tools to the global registry"""
    from backend.tools.registry import tool_registry
    
    tools = [
        PDFParserTool(),
        ExcelParserTool(),
        WordParserTool(),
        CSVParserTool(),
        JSONParserTool(),
        XMLParserTool(),
        UniversalFileParserTool()
    ]
    
    for tool in tools:
        tool_registry.register(tool)
    
    return tools
