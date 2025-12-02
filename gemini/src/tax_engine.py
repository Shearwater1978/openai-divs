import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta, date 
import numpy as np
import warnings

class TaxEngine:
    def __init__(self, unified_trades: pd.DataFrame, all_rates: Dict[str, pd.DataFrame]):
        self.unified_trades = unified_trades
        self.all_rates = all_rates
        self.stock_history = {} # История покупок для FIFO

    def _apply_fifo(self, row: pd.Series) -> pd.Series:
        """Реализует логику FIFO (First In, First Out) для продаж."""
        
        symbol = row['Symbol']
        action = row['Action']
        quantity = row['Quantity']
        proceeds = row['Proceeds']
        currency = row['Currency']

        if action == 'BUY':
            if symbol not in self.stock_history:
                self.stock_history[symbol] = []
            
            # --- КОРРЕКЦИЯ: Обработка Transfers с нулевой ценой ---
            cost_value = proceeds if pd.notna(proceeds) and proceeds != 0 else 0.0
            
            # Сохраняем покупку: (дата, количество, стоимость, валюта)
            self.stock_history[symbol].append({
                'date': row['Date/Time'],
                'qty': quantity,
                'cost': cost_value, 
                'currency': currency
            })
            
            # Для BUY P/L = 0
            row['P/L_PLN'] = 0.0
            
            # Если Proceeds_PLN не 0, берем его как Cost_PLN. Иначе (для Transfers) Cost_PLN = 0.0
            if row['Proceeds_PLN'] != 0.0:
                 row['Cost_PLN'] = abs(row['Proceeds_PLN']) 
            else:
                 row['Cost_PLN'] = 0.0
                 
            row['Cost_Basis_Missing'] = False
            return row

        elif action == 'SELL':
            if symbol not in self.stock_history or not self.stock_history[symbol]:
                warnings.warn(
                    f"WARNING: Sale of {symbol} on {row['Date/Time'].date()} has no matching BUY history. "
                    f"Full Proceeds will be taxed. REVIEW MANUALLY."
                )
                
                # Если истории нет, устанавливаем флаг и рассчитываем P/L как Proceeds (худший сценарий)
                row['Cost_PLN'] = 0.0
                row['P/L_PLN'] = row['Proceeds_PLN']
                row['Matched_Buy_Date'] = pd.NaT
                row['Cost_Basis_Missing'] = True # <-- Устанавливаем флаг
                return row
            
            remaining_qty = quantity # Количество, которое нужно продать
            total_cost_pln = 0.0
            matched_dates = []
            
            # Идем по старым покупкам (FIFO)
            while remaining_qty > 0 and self.stock_history[symbol]:
                buy_record = self.stock_history[symbol][0]
                
                match_qty = min(remaining_qty, buy_record['qty'])
                
                # Коэффициент, который мы используем из этой покупки
                qty_ratio = match_qty / buy_record['qty']
                
                # Стоимость в валюте покупки (Proceeds покупки всегда отрицателен или 0.0 для Transfer)
                cost_in_buy_currency = abs(buy_record['cost']) * qty_ratio
                
                # Получаем курс для даты покупки (T-1 от даты покупки)
                buy_rate = self.get_rate(buy_record['currency'], buy_record['date'])
                
                if buy_rate is None:
                    warnings.warn(f"WARNING: Missing BUY rate for {symbol} on {buy_record['date'].date()}. Cost component will be zeroed.")
                    cost_pln = 0.0
                else:
                    cost_pln = cost_in_buy_currency * buy_rate
                
                total_cost_pln += cost_pln
                
                # Обновляем остаток
                buy_record['qty'] -= match_qty
                remaining_qty -= match_qty
                
                # Собираем дату покупки, с которой сопоставлена продажа
                matched_dates.append(buy_record['date'].date())
                
                # Удаляем полностью использованную покупку
                if buy_record['qty'] <= 0.0001: 
                    self.stock_history[symbol].pop(0)

            # Сохраняем самую старую дату покупки
            row['Matched_Buy_Date'] = matched_dates[0] if matched_dates else pd.NaT
            row['Cost_Basis_Missing'] = False 
            
            # P/L = Proceeds_PLN (от продажи) - Total_Cost_PLN (от покупок)
            row['Cost_PLN'] = total_cost_pln
            row['P/L_PLN'] = row['Proceeds_PLN'] - total_cost_pln 
            return row
            
        row['Cost_Basis_Missing'] = False 
        return row
        
    def get_rate(self, currency: str, trade_date: datetime) -> Optional[float]:
        """Ищет курс на день, предшествующий сделке (T-1)."""
        
        if currency == 'PLN':
            return 1.0 

        rates_df = self.all_rates.get(currency)
        if rates_df is None or rates_df.empty:
            return None

        # 1. Дата для поиска - день, предшествующий сделке (T-1)
        search_date_dt = trade_date.date() - timedelta(days=1)
        
        # 2. Преобразуем в Timestamp для совместимости с индексом rates_df
        search_date = pd.Timestamp(search_date_dt)

        # Используем .loc[:search_date] для поиска последнего курса
        try:
            # Ищем самый последний курс ДО или В указанную дату поиска
            rate_series = rates_df.loc[:search_date].iloc[-1]
            rate = rate_series[f'Rate_PLN_{currency}']
            
            return rate if pd.notna(rate) else None
        
        except IndexError:
            return None
        except KeyError:
            return None
        except Exception:
            return None
            
    def calculate_tax(self) -> pd.DataFrame:
        """Конвертирует все сделки в PLN и применяет FIFO."""
        
        # --- ФИЛЬТРАЦИЯ ДАННЫХ ---
        if 'Action' not in self.unified_trades.columns:
            print("ERROR: 'Action' column not found in unified trades data. Cannot calculate tax.")
            return pd.DataFrame()
            
        # Фильтруем пустые значения в ключевых колонках
        trades_for_processing = self.unified_trades.dropna(
            subset=['Action', 'Quantity', 'Proceeds', 'Date/Time']
        ).copy()
        
        if trades_for_processing.empty:
            print("WARNING: No valid trades found after filtering for processing.")
            return pd.DataFrame()
        # ----------------------------------------------------
        
        # 1. Конвертация в PLN
        trades_for_processing['PLN_Rate'] = trades_for_processing.apply(
            lambda row: self.get_rate(row['Currency'], row['Date/Time']), 
            axis=1
        )
        
        trades_for_processing['Proceeds_PLN'] = np.where(
            trades_for_processing['PLN_Rate'].notna(),
            trades_for_processing['Proceeds'] * trades_for_processing['PLN_Rate'],
            0.0
        )
        
        # Инициализация колонки для отметки отсутствующей себестоимости
        trades_for_processing['Cost_Basis_Missing'] = False
        
        # 2. Применение FIFO
        final_trades_df = trades_for_processing.apply(self._apply_fifo, axis=1)
        
        # --- ФИНАЛЬНЫЙ ШАГ: ЯВНАЯ ФИЛЬТРАЦИЯ СТОЛБЦОВ ДЛЯ JSON ---
        # Включаем Asset Category для поддержки main.py и Cost_Basis_Missing для JSON.
        FINAL_COLUMNS = [
            'Date/Time', 'Action', 'Symbol', 'Quantity', 'Proceeds', 'Currency', 
            'Asset Category',      
            'PLN_Rate', 'Proceeds_PLN', 'Cost_PLN', 'P/L_PLN', 
            'Matched_Buy_Date', 
            'Cost_Basis_Missing', # <-- ГАРАНТИЯ ВКЛЮЧЕНИЯ В JSON
            'Account'
        ]
        
        # Используем .reindex, чтобы создать DataFrame только с нужными колонками
        final_trades_df = final_trades_df.reindex(columns=FINAL_COLUMNS)
        
        return final_trades_df