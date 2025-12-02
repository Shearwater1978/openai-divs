import pandas as pd
from typing import Dict, List, Union
import numpy as np

def merge_accounts(all_data: Dict[str, Dict[str, pd.DataFrame]]) -> pd.DataFrame:
    """
    Объединяет все данные из разделов 'Trades' и 'Transfers' всех счетов
    в один стандартизированный DataFrame, нормализует имена столбцов и определяет Action (BUY/SELL).
    """
    
    df_trade_list: List[pd.DataFrame] = []
    df_transfer_list: List[pd.DataFrame] = []
    
    # 1. Сбор и нормализация Trades и Transfers
    for account_key, sections in all_data.items():
        
        # Сбор Trades
        if 'Trades' in sections and not sections['Trades'].empty:
            df = sections['Trades'].copy()
            df['Account'] = account_key  
            df_trade_list.append(df)
            
        # Сбор Transfers (для начального остатка/себестоимости)
        if 'Transfers' in sections and not sections['Transfers'].empty:
            df = sections['Transfers'].copy()
            df['Account'] = account_key  
            df['Action'] = 'TRANSFER'  # Временно помечаем как TRANSFER
            # В Transfers часто отсутствует Proceeds, заполним нулем
            if 'Proceeds' not in df.columns:
                 df['Proceeds'] = 0.0
            df_transfer_list.append(df)


    # 2. Объединение Trades и Transfers
    unified_df_list = []
    if df_transfer_list:
        unified_transfers = pd.concat(df_transfer_list, ignore_index=True)
        unified_df_list.append(unified_transfers)
        
    if df_trade_list:
        unified_trades = pd.concat(df_trade_list, ignore_index=True)
        unified_df_list.append(unified_trades)

    if not unified_df_list:
        print("No trade or transfer data available after merging. Exiting.")
        return pd.DataFrame()
        
    unified_data = pd.concat(unified_df_list, ignore_index=True)
    
    # 3. Инициализация критических колонок, если они отсутствуют после объединения
    CRITICAL_COLS = ['Currency', 'Quantity', 'Proceeds', 'Date/Time', 'Symbol', 'Action']
    for col in CRITICAL_COLS:
        if col not in unified_data.columns:
            print(f"WARNING: Critical column '{col}' is missing. Initializing with NaN/Default.")
            if col in ['Quantity', 'Proceeds']:
                unified_data[col] = 0.0 # Используем 0.0 для Proceeds/Quantity в transfers
            elif col in ['Date/Time']:
                unified_data[col] = pd.NaT
            else: # Currency, Symbol, Action
                unified_data[col] = ''
    
    # 4. Фильтрация RUB
    EXCLUDED_CURRENCIES = ['RUB'] 
    if 'Currency' in unified_data.columns:
        unified_data = unified_data[~unified_data['Currency'].isin(EXCLUDED_CURRENCIES)]
    
    # 5. Приводим к правильному типу
    
    unified_data['Quantity'] = pd.to_numeric(unified_data['Quantity'], errors='coerce')
    unified_data['Proceeds'] = pd.to_numeric(unified_data['Proceeds'], errors='coerce')

    if 'Date/Time' in unified_data.columns:
        unified_data['Date/Time'] = pd.to_datetime(unified_data['Date/Time'], errors='coerce')
    
    # --- КОРРЕКЦИЯ: НОРМАЛИЗАЦИЯ ПОЛЯ ACTION (Trades + Transfers) ---
    def determine_action(row):
        action = row['Action']
        proceeds = row['Proceeds']
        quantity = row['Quantity']

        # 1. Обработка TRANSFER (для начального остатка)
        if isinstance(action, str) and 'transfer' in action.lower():
            # Inflow (Quantity > 0) должен стать BUY
            if quantity > 0:
                return 'BUY'
            # Outflow (Quantity < 0) должен стать SELL (хотя это обычно не облагается налогом)
            elif quantity < 0:
                return 'SELL'
            return action # Сохраняем TRANSFER, если Quantity = 0

        # 2. Обработка Trades (как раньше: по знаку Proceeds)
        elif isinstance(action, str) and 'trades' in action.lower():
            if proceeds > 0:
                return 'SELL'  
            elif proceeds < 0:
                return 'BUY'   
        
        # 3. Обработка пустых действий
        elif pd.isna(action) and proceeds != 0:
            if proceeds > 0:
                return 'SELL'  
            elif proceeds < 0:
                return 'BUY'   
                
        return action

    # Применяем функцию для определения Action
    unified_data['Action'] = unified_data.apply(determine_action, axis=1)
    # ----------------------------------------------------

    # 6. Очистка от строк с NaN в ключевых полях
    required_subset_for_dropna = ['Date/Time', 'Quantity', 'Proceeds', 'Currency', 'Symbol', 'Action']
    # Применяем очистку к unified_data
    unified_data.dropna(subset=required_subset_for_dropna, inplace=True)
    
    if unified_data.empty:
        print("ERROR: All trade and transfer records were dropped after cleaning. Cannot proceed.")
        return pd.DataFrame()
        
    # 7. Добавляем колонки для расчетов
    unified_data['PLN_Rate'] = 0.0
    unified_data['Proceeds_PLN'] = 0.0
    unified_data['Cost_PLN'] = 0.0
    unified_data['P/L_PLN'] = 0.0
    unified_data['Matched_Buy_Date'] = pd.NaT 

    # 8. Сортировка (ВАЖНО: Transfers должны быть раньше Trades)
    unified_data.sort_values(by=['Date/Time'], inplace=True)
    
    return unified_data