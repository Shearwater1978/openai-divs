import pandas as pd
from typing import Dict, List, Union
import numpy as np

def merge_accounts(all_data: Dict[str, Dict[str, pd.DataFrame]]) -> pd.DataFrame:
    """
    Объединяет все данные из раздела 'Trades' всех счетов в один стандартизированный DataFrame.
    """
    
    df_list: List[pd.DataFrame] = []
    
    # 1. Сбор только раздела 'Trades'
    for account_key, sections in all_data.items():
        if 'Trades' in sections and not sections['Trades'].empty:
            df = sections['Trades'].copy()
            df['Account'] = account_key  
            df_list.append(df)
            
    if df_list:
        unified_trades = pd.concat(df_list, ignore_index=True)
        
        # 2. Инициализация критических колонок, если они отсутствуют после объединения (чтобы избежать KeyError в следующих шагах)
        # Это должно происходить, только если парсер не нашел колонку, но лучше гарантировать их существование.
        CRITICAL_COLS = ['Currency', 'Quantity', 'Proceeds', 'Date/Time', 'Symbol', 'Action']
        for col in CRITICAL_COLS:
            if col not in unified_trades.columns:
                print(f"WARNING: Critical column '{col}' is missing. Initializing with NaN/Default.")
                # Инициализируем отсутствующие колонки, чтобы предотвратить сбои.
                if col in ['Quantity', 'Proceeds']:
                    unified_trades[col] = np.nan
                elif col in ['Date/Time']:
                    unified_trades[col] = pd.NaT
                else: # Currency, Symbol, Action
                    unified_trades[col] = ''
        
        # 3. Фильтрация RUB
        if 'Currency' in unified_trades.columns:
            EXCLUDED_CURRENCIES = ['RUB'] 
            excluded_rub_trades = unified_trades[unified_trades['Currency'].isin(EXCLUDED_CURRENCIES)].copy()
            
            if not excluded_rub_trades.empty:
                print(f"WARNING: Excluding {len(excluded_rub_trades)} trades involving unsupported currencies ({', '.join(EXCLUDED_CURRENCIES)}) from tax calculation.")
                
            unified_trades = unified_trades[~unified_trades['Currency'].isin(EXCLUDED_CURRENCIES)]
        
        # 4. Приводим к правильному типу
        
        # Quantity и Proceeds
        unified_trades['Quantity'] = pd.to_numeric(unified_trades['Quantity'], errors='coerce')
        unified_trades['Proceeds'] = pd.to_numeric(unified_trades['Proceeds'], errors='coerce')

        # Date/Time
        unified_trades['Date/Time'] = pd.to_datetime(unified_trades['Date/Time'], errors='coerce')
        
        # 5. Очистка от строк с NaN в ключевых полях
        
        # Теперь, когда все колонки гарантированно существуют, мы можем безопасно очищать по ним
        required_subset_for_dropna = ['Date/Time', 'Quantity', 'Proceeds', 'Currency', 'Symbol', 'Action']
        
        # Удаляем строки, где нет данных в ключевых столбцах
        unified_trades.dropna(subset=required_subset_for_dropna, inplace=True)
        
        if unified_trades.empty:
            print("ERROR: All trade records were dropped after cleaning (likely missing critical data). Cannot proceed.")
            return pd.DataFrame() # Возвращаем пустой DataFrame, если все удалено
        
        # 6. Добавляем колонки для расчетов
        unified_trades['PLN_Rate'] = 0.0
        unified_trades['Proceeds_PLN'] = 0.0
        unified_trades['Cost_PLN'] = 0.0
        unified_trades['P/L_PLN'] = 0.0
        unified_trades['Matched_Buy_Date'] = pd.NaT 

        unified_trades.sort_values(by=['Date/Time'], inplace=True)
        
        return unified_trades
    
    return pd.DataFrame()