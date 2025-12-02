# --- src/nbp_rates.py ---
import requests
import pandas as pd
from datetime import date, timedelta
from typing import Optional, Set, Dict

# Переименован в NBPFetcher, чтобы соответствовать main.py
class NBPFetcher: 
    """
    Класс для загрузки курсов валют Национального банка Польши (NBP).
    """

    def __init__(self, foreign_currencies: Set[str]):
        # Убираем start_date/end_date из __init__, так как они передаются в fetch_all_rates
        self.foreign_currencies = foreign_currencies

    def _fetch_currency_rates_in_period(self, currency: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Запрашивает курсы валюты NBP для заданного периода (максимум 365 дней).
        """
        BASE_URL = "http://api.nbp.pl/api/exchangerates/rates/a"
        
        url = f"{BASE_URL}/{currency}/{start_date.isoformat()}/{end_date.isoformat()}/"
        
        try:
            # Отключаем печать DEBUG NBP здесь, так как она будет в главном методе
            response = requests.get(url, headers={"Accept": "application/json"})
            response.raise_for_status() 
            
            data = response.json()
            
            if 'rates' in data:
                # Объединяем все полученные данные в один DataFrame
                df = pd.DataFrame(data['rates'])
                
                # Нормализация данных
                df.rename(columns={'mid': f'Rate_PLN_{currency}', 'effectiveDate': 'Date'}, inplace=True)
                
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                
                # Удаляем дубликаты и сортируем
                df = df[~df.index.duplicated(keep='last')]
                df.sort_index(inplace=True)
                
                return df[[f'Rate_PLN_{currency}']]
            
            return pd.DataFrame() 

        except requests.exceptions.HTTPError as e:
             if response.status_code == 404:
                 print(f"NBP Warning: No rates found for {currency} between {start_date} and {end_date}.")
             else:
                 print(f"NBP API Error for {currency} on period {start_date}-{end_date}: {e}")
             return pd.DataFrame() 
        except Exception as e:
            print(f"An unexpected error occurred for {currency}: {e}")
            return pd.DataFrame()


    def fetch_all_rates(self, start_date: date, end_date: date) -> Dict[str, pd.DataFrame]:
        """
        Загружает курсы для всех валют, разбивая периоды по 365 дней.
        """
        all_fetched_rates = {}
        MAX_DAYS = 365 

        for currency in self.foreign_currencies:
            current_start = start_date
            all_rates_df_list = []
            
            # Цикл, разбивающий большой период на части по 365 дней
            while current_start <= end_date:
                period_end = current_start + timedelta(days=MAX_DAYS - 1)
                
                if period_end > end_date:
                    period_end = end_date

                print(f"DEBUG NBP: Fetching {currency} from {current_start} to {period_end}")
                
                # Загружаем данные для части периода
                rates_df = self._fetch_currency_rates_in_period(currency, current_start, period_end)
                
                if not rates_df.empty:
                    all_rates_df_list.append(rates_df)
                
                current_start = period_end + timedelta(days=1)
                
            if all_rates_df_list:
                final_currency_df = pd.concat(all_rates_df_list)
                final_currency_df = final_currency_df[~final_currency_df.index.duplicated(keep='last')]
                final_currency_df.sort_index(inplace=True)
                all_fetched_rates[currency] = final_currency_df
                print(f"DEBUG: Successfully cached {len(final_currency_df)} rates for {currency}.")

        return all_fetched_rates