import pandas as pd
import sys
import os
import json
from datetime import date, timedelta # <-- Добавлен timedelta
from typing import Dict, List, Set, Tuple

# --- КОНФИГУРАЦИЯ ---
DATA_DIR = "data" 
OUTPUT_DIR = "output" 

# Добавляем 'src' в системный путь для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__), 'src')) 

# ИМПОРТЫ
from src.parser import StatementParser
from src.data_merger import merge_accounts 
from src.nbp_api import NBPAPI
from src.tax_engine import TaxEngine 

# --- ГЛАВНАЯ ФУНКЦИЯ ---

def main():
    
    all_parsed_data = {}
    all_currencies = set()
    
    print("--- IBKR PIT-38 ANALYZER START ---")

    # 2. ПАРСИНГ ВСЕХ ФАЙЛОВ ИЗ DATA_DIR
    if not os.path.isdir(DATA_DIR):
        print(f"Error: Directory '{DATA_DIR}' not found. Please create it and place your CSV reports inside.")
        return

    # Итерация по всем CSV файлам в каталоге
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.csv'):
            input_file = os.path.join(DATA_DIR, filename)
            account_key = filename.replace('.csv', '') 
            
            print(f"Processing report: {filename}...")
            parser = StatementParser(input_file)
            
            parsed_data, discovered_currencies = parser.parse_statement()
            
            if parsed_data:
                all_parsed_data[account_key] = parsed_data
                all_currencies.update(discovered_currencies)
                
    if not all_parsed_data:
        print(f"Error: No CSV reports found in the '{DATA_DIR}' directory. Exiting.")
        return
        
    # 3. ОБЪЕДИНЕНИЕ И СТАНДАРТИЗАЦИЯ
    unified_trades = merge_accounts(all_parsed_data) # <-- data_merger.py фильтрует RUB
    
    # После фильтрации в data_merger.py, unified_trades может быть пустым
    if unified_trades.empty:
        print("No trade data available after merging (or all were filtered out). Exiting.")
        return

    # --- 1. ОПРЕДЕЛЕНИЕ ОБЩЕГО ДИАПАЗОНА ДАТ ---
    
    try:
        # Самая ранняя и самая поздняя дата сделок
        min_trade_date = unified_trades['Date/Time'].min().date()
        end_date = unified_trades['Date/Time'].max().date()
        
        # Добавляем запас в 3 дня к начальной дате для гарантии T-1 курса
        start_date = min_trade_date - timedelta(days=3)
        
    except Exception as e:
        print(f"ERROR: Failed to determine date range from trades ({e}). Using default 2021 period.")
        start_date = date(2021, 1, 1)
        end_date = date(2021, 12, 31)

    print(f"Reporting period (determined from trades): {start_date} to {end_date}")
    
    # 4. РАСЧЕТ КУРСОВ ВАЛЮТЫ (PLN)
    
    # ИСКЛЮЧАЕМ RUB, так как NBP не предоставляет курсы для этой валюты
    EXCLUDED_CURRENCIES = {'PLN', 'RUB'}
    
    # Определяем, какие валюты нужно конвертировать
    currencies_to_fetch = all_currencies - EXCLUDED_CURRENCIES
    print(f"DEBUG: Discovered foreign currencies: {currencies_to_fetch}")
    
    # Курс PLN/PLN = 1.0 
    all_rates = {'PLN': pd.DataFrame({'Rate_PLN_PLN': 1.0}, index=[0])}

    # Загружаем курсы для иностранных валют
    nbp_api = NBPAPI(start_date, end_date) # NBPAPI.fetch_rates разбивает запрос на части по 365 дней
    for currency in currencies_to_fetch:
        rates = nbp_api.fetch_rates(currency)
        if not rates.empty:
            all_rates[currency] = rates
            print(f"DEBUG: Successfully cached {len(rates)} rates for {currency}.")
        else:
            print(f"WARNING: Could not fetch rates for {currency}. Conversion calculations will fail.")
            
    # 5. НАЛОГОВЫЕ РАСЧЕТЫ (Tax Engine)
    print("\n--- НАЧАЛО НАЛОГОВОГО РАСЧЕТА ---")
    engine = TaxEngine(unified_trades, all_rates)
    final_report_df = engine.calculate_tax()
    
    if final_report_df.empty:
        print("Tax engine returned an empty report. Check for missing rates or data.")
        return

    # --- ФИНАЛЬНЫЙ ОТЧЕТ И ЭКСПОРТ В JSON ---
    print("\n--- ФИНАЛЬНЫЙ ОТЧЕТ (ИТОГОВЫЕ РАСЧЕТЫ) ---")
    
    # Расчет финальных сумм для PIT-38
    stocks_summary = final_report_df[final_report_df['Asset Category'] == 'Stocks'].agg({
        'Proceeds_PLN': 'sum',
        'Cost_PLN': 'sum',
        'P/L_PLN': 'sum'
    })
    
    forex_summary = final_report_df[final_report_df['Asset Category'] == 'Forex'].agg({
        'P/L_PLN': 'sum'
    })

    # Собираем финальный JSON-объект
    final_json_data = {
        "reporting_period": f"{start_date.isoformat()} to {end_date.isoformat()}",
        "summary_pit_38_pln": {
            "stocks_total": {
                "proceeds_pln": round(stocks_summary.loc['Proceeds_PLN'], 2),
                "cost_pln": round(stocks_summary.loc['Cost_PLN'], 2),
                "pl_pln": round(stocks_summary.loc['P/L_PLN'], 2)
            },
            "forex_total": {
                "pl_pln": round(forex_summary.loc['P/L_PLN'], 2) if 'P/L_PLN' in forex_summary else 0.0
            }
        },
        "details_by_trade": final_report_df[['Date/Time', 'Action', 'Symbol', 'Quantity', 'Proceeds', 'PLN_Rate', 'Proceeds_PLN', 'Cost_PLN', 'P/L_PLN', 'Matched_Buy_Date']].to_dict('records')
    }

    # Вывод в консоль
    json_output = json.dumps(final_json_data, indent=4, default=str, ensure_ascii=False)
    
    print("\n--- ФИНАЛЬНЫЙ JSON-ОТЧЕТ ДЛЯ PIT-38 ---")
    # print(json_output)
    
    # --- Сохранение в файл с использованием OUTPUT_DIR ---
    output_filename_base = f"pit_38_report_{start_date.year}.json"
    output_filepath = os.path.join(OUTPUT_DIR, output_filename_base)
    
    # Создаем каталог 'output', если он не существует
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(output_filepath, 'w', encoding='utf-8') as f:
        f.write(json_output)
        
    print(f"\nОтчет сохранен в файл: {output_filepath}")


if __name__ == "__main__":
    main()