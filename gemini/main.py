import os
import pandas as pd
import json 
from collections import defaultdict
from datetime import datetime
from src.parser import StatementParser
from src.data_merger import merge_accounts
from src.nbp_rates import NBPFetcher
from src.tax_engine import TaxEngine

# --- КОНФИГУРАЦИЯ ---
DATA_DIR = 'data'
START_YEAR = 2021
END_YEAR = 2022
# --- ПУТИ ВЫВОДА ---
OUTPUT_DIR = 'output' # Папка для сохранения
OUTPUT_FILENAME = 'final_tax_report.json' # Имя файла
OUTPUT_FULL_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME) # Полный путь
# -----------------------------

def main():
    print("--- IBKR PIT-38 ANALYZER START ---")
    
    all_raw_data = defaultdict(dict)
    all_currencies = set()
    
    # 1. Сбор и парсинг всех отчетов
    report_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    
    for filename in report_files:
        file_path = os.path.join(DATA_DIR, filename)
        
        # Получаем ключ аккаунта (предполагаем, что он в имени файла, например U7701359)
        account_key = filename.split('_')[0] 
        
        print(f"Processing report: {filename}...")
        
        parser = StatementParser(file_path)
        parsed_sections, discovered_currencies = parser.parse_statement()
        
        all_raw_data[account_key].update(parsed_sections)
        all_currencies.update(discovered_currencies)
        
    # 2. Объединение и нормализация данных
    unified_trades_df = merge_accounts(all_raw_data)
    
    if unified_trades_df.empty:
        print("FATAL ERROR: No valid trades or transfers found after merging. Exiting.")
        return

    # Определяем период для загрузки курсов
    if not unified_trades_df['Date/Time'].empty:
        reporting_start_date = unified_trades_df['Date/Time'].min().date()
        reporting_end_date = unified_trades_df['Date/Time'].max().date()
        print(f"Reporting period (determined from trades): {reporting_start_date} to {reporting_end_date}")
    else:
        print("WARNING: Could not determine reporting period from trades.")
        return
        
    # 3. Загрузка курсов NBP (T-1)
    
    # Исключаем PLN, так как курс 1.0
    foreign_currencies = all_currencies - {'PLN'}
    print(f"DEBUG: Discovered foreign currencies: {foreign_currencies}")
    
    nbp_fetcher = NBPFetcher(foreign_currencies)
    all_rates = nbp_fetcher.fetch_all_rates(reporting_start_date, reporting_end_date)
    
    # 4. Расчет налога (FIFO, конвертация)
    print("\n--- НАЧАЛО НАЛОГОВОГО РАСЧЕТА ---")
    tax_engine = TaxEngine(unified_trades_df, all_rates)
    final_report_df = tax_engine.calculate_tax()
    
    if final_report_df.empty:
        print("FATAL ERROR: Tax calculation returned empty data. Exiting.")
        return

    # DEBUG: Проверка наличия всех колонок перед сохранением
    print(f"DEBUG FINAL COLUMNS: {list(final_report_df.columns)}")
    
    # 5. Генерация финального отчета
    print("\n--- ФИНАЛЬНЫЙ ОТЧЕТ (ИТОГОВЫЕ РАСЧЕТЫ) ---")
    
    # Фильтруем только акции для суммирования P/L
    stocks_summary = final_report_df[final_report_df['Asset Category'] == 'Stocks'].agg({
        'Proceeds_PLN': 'sum',
        'Cost_PLN': 'sum',
        'P/L_PLN': 'sum'
    })

    print(f"\nСводка по акциям ({START_YEAR}-{END_YEAR}):")
    print(f"  Продажи (PLN): {stocks_summary['Proceeds_PLN']:.2f}")
    print(f"  Себестоимость (PLN): {stocks_summary['Cost_PLN']:.2f}")
    print(f"  Прибыль/Убыток (PLN): {stocks_summary['P/L_PLN']:.2f}")
    
    # --- СЕКЦИЯ СОХРАНЕНИЯ JSON (ИСПРАВЛЕНИЕ ОШИБКИ ТИПА И ПУТИ) ---
    
    # 1. Принудительно преобразуем объекты дат и времени в строки для корректной JSON-сериализации.
    final_report_df['Date/Time'] = final_report_df['Date/Time'].dt.strftime('%Y-%m-%dT%H:%M:%S')
    final_report_df['Matched_Buy_Date'] = final_report_df['Matched_Buy_Date'].astype(str)
    
    # 2. Преобразуем DataFrame в список словарей
    final_data_list = final_report_df.to_dict(orient='records')
    
    # 3. Гарантируем существование папки output
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 4. Сохраняем в файл, используя полный путь
    with open(OUTPUT_FULL_PATH, 'w', encoding='utf-8') as f:
        json.dump(final_data_list, f, indent=4, ensure_ascii=False)
        
    print(f"\nОтчет успешно сохранен в: {OUTPUT_FULL_PATH}")


if __name__ == "__main__":
    main()