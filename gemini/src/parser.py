import pandas as pd
import io
import numpy as np
from typing import Dict, List, Set, Tuple, Optional 
import warnings

# --- КОНСТАНТЫ ISO 4217 ---
ISO_4217_CODES = {
    'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'HKD', 'SGD', 'NZD', 
    'KRW', 'INR', 'RUB', 'BRL', 'MXN', 'ZAR', 'PLN', 'CZK', 'HUF', 'ILS', 'TRY', 
    'SEK', 'NOK', 'DKK', 'SAR', 'KWD', 'AED', 'QAR', 'THB', 'MYR', 'IDR', 'PHP',
    'VND', 'CLP', 'COP', 'PEN', 'ARS', 'EGP', 'TWD'
}

class StatementParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.delimiter = ','

    def _determine_section_boundaries(self, lines: List[str]) -> Dict[str, Tuple[int, int]]:
        """Определяет начальную и конечную строку для каждого раздела."""
        
        all_report_sections = [
            "Trades", "Dividends", "Transfers", "Deposits & Withdrawals",
            "Change in Dividend Accruals", "Financial Instrument Information",
            "Codes", "Notes/Legal Notes", "Cash Report" 
        ]
        
        section_starts = {}
        for i, line in enumerate(lines):
            try:
                section_name = line.split(self.delimiter)[0].strip()
            except IndexError:
                continue
                
            if section_name in all_report_sections and section_name not in section_starts:
                section_starts[section_name] = i
        
        sorted_starts = sorted(section_starts.items(), key=lambda item: item[1])
        
        final_boundaries = {}
        relevant_sections = ["Trades", "Dividends", "Transfers", "Deposits & Withdrawals", "Change in Dividend Accruals"]
        
        for i in range(len(sorted_starts)):
            section_name, start = sorted_starts[i]
            
            if section_name not in relevant_sections:
                continue 

            if i + 1 < len(sorted_starts):
                end = sorted_starts[i+1][1]
            else:
                end = len(lines)
            
            final_boundaries[section_name] = (start, end)
            
        return final_boundaries


    def _clean_column_names(self, column_series: pd.Series) -> List[str]:
        """Очищает имена столбцов от пустых значений и дубликатов."""
        cleaned_cols = [str(col) if pd.notna(col) else '' for col in column_series]
        
        final_names = []
        for i, name in enumerate(cleaned_cols):
            stripped_name = name.strip()
            
            if stripped_name == '':
                final_names.append(f'Unnamed_{i}')
            else:
                final_names.append(stripped_name)
        
        return final_names

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Гарантирует, что все критические столбцы имеют правильное имя, используя принудительное сопоставление по индексу."""
        column_mapping = {}
        raw_columns = list(df.columns)
        
        # Шаг 1: Агрессивное сопоставление по названию для СТАНДАРТНЫХ полей (те, которые не ломаются)
        for col in raw_columns:
            cleaned_col = col.replace('.', '').replace('/', '').replace(' ', '').strip().lower()
            
            # --- СТАНДАРТНЫЕ/ВСПОМОГАТЕЛЬНЫЕ ПОЛЯ ---
            if cleaned_col in ['datadiscriminator', 'levelofdata', 'levelofdetail']:
                column_mapping[col] = 'DataDiscriminator'
            elif 'basis' in cleaned_col:
                column_mapping[col] = 'Basis'
            
            # Стандартные сопоставления для Trade-полей (если они не попадают в нестандартный формат)
            elif cleaned_col in ['action', 'buy/sell', 'buysell', 'code', 'transactiontype']:
                column_mapping[col] = 'Action'
            elif cleaned_col in ['symbol', 'assetsymbol', 'tickersymbol', 'underlyingsymbol', 'futuresymbol']:
                column_mapping[col] = 'Symbol'
            elif 'assetcategory' in cleaned_col:
                column_mapping[col] = 'Asset Category'

        # Шаг 2: Принудительное сопоставление по индексу (КЛЮЧЕВЫЕ ПОЛЯ)
        
        # Если DataFrame имеет достаточно столбцов (ваш отчет имеет 16+), используем индексацию
        if len(raw_columns) > 10:
            
            # Сопоставление по индексу (Считая с 0):
            # Эти индексы основаны на вашем DEBUG RAW COLUMNS.
            index_map = [
                (0, 'Action'),          # Trades
                (4, 'Currency'),        # USD/CAD
                (5, 'Symbol'),          # AFL/MFC
                (6, 'Date/Time'),       # Дата/Время
                (7, 'Quantity'),        # 1/2
                (9, 'Proceeds'),        # -54.47/-47.9
                (3, 'Asset Category'),  # Stocks
            ]
            
            for index, target_name in index_map:
                if index < len(raw_columns):
                    original_name = raw_columns[index]
                    
                    # Принудительно назначаем имя, перезаписывая, если оно было найдено Шагом 1
                    # (это гарантирует, что мы возьмем колонку по правильному индексу)
                    column_mapping[original_name] = target_name

        
        if not column_mapping:
             return df 

        df.rename(columns=column_mapping, inplace=True)
        
        # DEBUG: Проверка после нормализации
        key_cols = {'Action', 'Currency', 'Quantity', 'Proceeds', 'Date/Time', 'Symbol'}
        for col in key_cols:
             if col not in df.columns:
                 if not df.empty and any(c in df.columns for c in ['Symbol', 'Action']):
                     print(f"DEBUG PARSER ERROR: After normalization, '{col}' column is missing in a potential trades section. Available columns: {list(df.columns)}")
        
        return df

    def parse_section(self, lines: List[str], start_row: int, end_row: int) -> Optional[pd.DataFrame]:
        """Парсит один раздел CSV в DataFrame."""
        if start_row >= end_row:
            return None

        header_row_index = start_row + 2
        
        if header_row_index >= end_row:
             return None 

        section_lines = lines[start_row:end_row]
        skip_rows_count = header_row_index - start_row
        
        try:
            csv_data = "\n".join(section_lines)
            data_io = io.StringIO(csv_data)

            df = pd.read_csv(
                data_io,
                header=skip_rows_count,
                sep=self.delimiter,
                encoding='utf-8',
                skipinitialspace=True,
                low_memory=False
            )
            
            df = df.dropna(how='all')
            df.columns = self._clean_column_names(df.columns)
            
            # --- ВЫВОД НЕОБРАБОТАННЫХ СТОЛБЦОВ ---
            section_name = lines[start_row].split(self.delimiter)[0].strip()
            if section_name == 'Trades':
                print(f"DEBUG RAW COLUMNS for {self.file_path}: {list(df.columns)}")
            # ------------------------------------
            
            df = self._normalize_columns(df)
            
            # Защита от отсутствия DataDiscriminator
            if 'DataDiscriminator' in df.columns:
                df = df[df['DataDiscriminator'].apply(lambda x: pd.isna(x) or x != 'Total')]
            
            if df.empty:
                return None
                
            return df
            
        except pd.errors.ParserError as e:
            print(f"Error parsing section: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during section parsing: {e}")
            return None

    def parse_statement(self) -> Tuple[Dict[str, pd.DataFrame], Set[str]]:
        """Парсит весь отчет IBKR."""
        
        parsed_data: Dict[str, pd.DataFrame] = {}
        discovered_currencies: Set[str] = set()

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Failed to read file {self.file_path}: {e}")
            return {}, set()

        boundaries = self._determine_section_boundaries(lines)
        
        for section_name, (start, end) in boundaries.items():
            df = self.parse_section(lines, start, end)
            
            if df is not None and not df.empty:
                parsed_data[section_name] = df
                print(f"Successfully parsed section {section_name}: {len(df)} records.")
                
                if 'Currency' in df.columns:
                    currencies = df['Currency'].dropna().unique()
                    discovered_currencies.update(c for c in currencies if c in ISO_4217_CODES)

        return parsed_data, discovered_currencies