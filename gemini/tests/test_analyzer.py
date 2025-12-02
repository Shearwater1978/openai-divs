import pandas as pd
import pytest
from datetime import date, datetime
from collections import deque
from unittest.mock import MagicMock, patch

# Импортируем классы из исходных модулей
from src.parser import StatementParser
from src.data_merger import DataMerger, COL_DATE, COL_AMOUNT, COL_QUANTITY
from src.tax_engine import TaxEngine, TaxLot

# --- 1. МОКИРОВАНИЕ ЗАВИСИМОСТЕЙ ---
# Создаем фиктивный курс обмена для тестов.
FX_RATE_MOCK = 4.0
# Фиктивный CSV-контент
MOCK_CSV_CONTENT = """
Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,Comm/Fee,Proceeds,Basis
Trades,Data,Order,Stocks,USD,AAPL,2021-01-05 09:30:00,100,"100.00","0.50","10000.00","10000.50"
Trades,Data,Order,Stocks,USD,GOOGL,2021-02-10 10:00:00,"-50","2000.00","1.00","-100000.00","-100001.00"
Trades,Data,Order,Stocks,USD,MSFT,2021-03-01 11:00:00,50,"250.00","0.25","12500.00","12500.25"
Trades,Data,Order,Stocks,USD,AAPL,2021-12-01 12:00:00,5,"150.00","0.10","750.00","750.10"
Cash Report,Header,DataDiscriminator,Currency,Description,Amount,Type
Cash Report,Data,Payment,USD,Dividend Paid,10.00,WHT
Dividends,Header,DataDiscriminator,Currency,Symbol,Date/Time,Gross Amount,Payment Date
Dividends,Data,Payment,USD,AAPL,2021-05-15 09:00:00,20.00,2021-05-16
Dividends,Total,Total,,,,,,,
"""

# --- 2. ФИКТУРЫ И ХЕЛПЕРЫ ---

@pytest.fixture
def mock_fx_provider():
    """Мокирует поставщика курсов, возвращая константный курс."""
    provider = MagicMock()
    # Мокируем get_compliant_rate, чтобы всегда возвращал 4.0
    provider.get_compliant_rate.return_value = FX_RATE_MOCK
    return provider

@pytest.fixture
def mock_parsed_data(tmp_path):
    """Имитирует парсинг, возвращая чистый DataFrame Trades."""
    
    # 1. Создаем фиктивный CSV-файл
    csv_file = tmp_path / "mock_statement.csv"
    csv_file.write_text(MOCK_CSV_CONTENT, encoding='utf-8')

    # 2. Парсим только секцию Trades (для тестов TaxEngine)
    trades_df = pd.DataFrame({
        'DataDiscriminator': ['Order', 'Order', 'Order', 'Order'],
        'Asset Category': ['Stocks', 'Stocks', 'Stocks', 'Stocks'],
        'Currency': ['USD', 'USD', 'USD', 'USD'],
        'Symbol': ['AAPL', 'GOOGL', 'MSFT', 'AAPL'],
        'Date/Time': ['2021-01-05 09:30:00', '2021-02-10 10:00:00', '2021-03-01 11:00:00', '2021-12-01 12:00:00'],
        'Quantity': ['100', '-50', '50', '5'], # <-- Изначально строки для тестирования data_merger.py
        'T. Price': ['100.00', '2000.00', '250.00', '150.00'],
        'Comm/Fee': ['0.50', '1.00', '0.25', '0.10'],
        'Proceeds': ['10000.00', '-100000.00', '12500.00', '750.00'],
        'Basis': ['10000.50', '100001.00', '12500.25', '750.10'],
    })
    
    # Парсим секцию Dividends
    dividends_df = pd.DataFrame({
        'DataDiscriminator': ['Payment'],
        'Currency': ['USD'],
        'Symbol': ['AAPL'],
        'Date/Time': [datetime(2021, 5, 15)],
        'Gross Amount': [20.00],
        'Payment Date': [datetime(2021, 5, 16)],
    })

    # Имитируем выходные данные parser.py
    return [{'Trades': trades_df, 'Dividends': dividends_df}]

# --- 3. КЛАСС ТЕСТОВ ---

class TestPipeline:

    def test_data_merger_type_coercion_and_action_creation(self, mock_parsed_data):
        """Тестирует критически важные исправления: преобразование типов и создание колонки 'Action'."""
        
        merger = DataMerger(mock_parsed_data)
        unified_trades, _ = merger.merge_accounts()

        # 1. Проверка преобразования типов (COL_QUANTITY должен быть float)
        assert unified_trades[COL_QUANTITY].dtype == 'float64', "Quantity должна быть float."
        assert unified_trades[COL_AMOUNT].dtype == 'float64', "Proceeds должна быть float."
        
        # 2. Проверка создания колонки 'Action'
        actions = unified_trades['Action'].tolist()
        
        # BUY (Proceeds > 0) -> SELL (Proceeds < 0)
        # 10000.00 (BUY) -> 10000.00 (SELL)
        # -100000.00 (SELL) -> -100000.00 (BUY)
        # 12500.00 (BUY) -> 12500.00 (SELL)
        # 750.00 (BUY) -> 750.00 (SELL)
        
        # Внимание: В IBKR Proceeds для покупки положительный, если это Cash. Для stocks proceeds - выручка.
        # Если Proceeds > 0 -> SELL (деньги пришли)
        # Если Proceeds < 0 -> BUY (деньги ушли)

        # Проверяем, что наша логика (SELL, BUY, SELL, SELL) корректна
        expected_actions = ['SELL', 'BUY', 'SELL', 'SELL']
        
        # В фиктивном DataFrame:
        # 1. Proceeds: 10000.00 (Cash In) -> SELL
        # 2. Proceeds: -100000.00 (Cash Out) -> BUY
        # 3. Proceeds: 12500.00 (Cash In) -> SELL
        # 4. Proceeds: 750.00 (Cash In) -> SELL

        assert actions == expected_actions, "Колонка 'Action' создана некорректно."
        assert unified_trades.iloc[1]['Action'] == 'BUY', "Вторая сделка должна быть покупкой."

    def test_tax_engine_fifo_and_serialization(self, mock_parsed_data, mock_fx_provider):
        """Тестирует логику FIFO и корректную сериализацию нереализованных лотов."""
        
        merger = DataMerger(mock_parsed_data)
        unified_trades, unified_dividends = merger.merge_accounts()
        engine = TaxEngine(unified_trades, unified_dividends, mock_fx_provider)
        
        # Запускаем расчет
        dataset = engine.get_golden_dataset()
        
        # --- Проверка Unrealized Lots (Cost Basis) ---
        
        # Ожидаем, что GOOGL (вторая сделка) - это BUY, но в логах она BUY, а в данных SELL (Proceeds < 0).
        # Пересортированная таблица: 
        # 1. AAPL BUY (100) - Date 2021-01-05 (Proceeds: 10000.00 -> SELL)
        # 2. GOOGL SELL (50) - Date 2021-02-10 (Proceeds: -100000.00 -> BUY) <-- ЭТО НАША ПОКУПКА 
        # 3. MSFT BUY (50) - Date 2021-03-01 (Proceeds: 12500.00 -> SELL)
        # 4. AAPL BUY (5) - Date 2021-12-01 (Proceeds: 750.00 -> SELL)

        # В этом тесте: GOOGL (50 акций) - единственная покупка, которая должна попасть в unrealized_lots.
        unrealized = dataset['unrealized_lots']
        
        assert 'GOOGL' in unrealized, "GOOGL должен быть в нереализованных лотах."
        assert len(unrealized['GOOGL']) == 1, "Должен быть только один лот GOOGL."
        
        lot = unrealized['GOOGL'][0]
        
        # Проверка сериализации всех новых полей
        assert lot['quantity_remaining'] == 50.0, "Количество GOOGL должно быть 50."
        assert lot['cost_currency'] == 100001.00, "Стоимость в валюте должна быть Basis."
        assert lot['currency'] == 'USD', "Валюта должна быть USD."
        
        # Проверка расчета PLN (Basis 100001.00 * Rate 4.0)
        expected_pln_cost = 100001.00 * FX_RATE_MOCK
        assert lot['cost_pln'] == expected_pln_cost, "Расчет стоимости в PLN некорректен."

    def test_parser_section_isolation(self, tmp_path):
        """Тестирует изоляцию секции 'Trades' с игнорированием последующих секций."""
        
        csv_file = tmp_path / "complex_report.csv"
        csv_file.write_text(MOCK_CSV_CONTENT, encoding='utf-8')
        
        parser = StatementParser(str(csv_file))
        parsed_data, _ = parser.parse_statement()
        
        # Проверяем, что секция Trades существует
        assert 'Trades' in parsed_data
        
        trades_df = parsed_data['Trades']
        
        # 1. Проверяем, что лишние строки (Total) удалены
        # Исходный файл содержит 4 строки Trades Data + 1 строка Dividends Data
        assert len(trades_df) == 4, "Trades DataFrame должен содержать только 4 строки Order."
        
        # 2. Проверяем, что строки из других секций (Cash Report/Dividends) не попали
        assert 'Dividends' in parsed_df, "Раздел Dividends должен быть отделен."
        assert len(parsed_df['Dividends']) == 1, "Раздел Dividends должен содержать 1 строку Payment."