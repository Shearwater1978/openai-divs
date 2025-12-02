import requests
import pandas as pd
from datetime import date, timedelta
from typing import Optional

class NBPAPI:
    """
    Класс для загрузки курсов валют Национального банка Польши (NBP).
    """

    def __init__(self, start_date: date, end_date: date):
        self.start_date = start_date
        self.end_date = end_date

    def fetch_rates(self, currency: str) -> pd.DataFrame:
        """
        Запрашивает курсы валюты с разбивкой на периоды по 365 дней
        для обхода лимита NBP API.
        
        Возвращает DataFrame с индексом pd.Timestamp.
        """
        BASE_URL = "http://api.nbp.pl/api/exchangerates/rates/a"
        MAX_DAYS = 365 

        current_start = self.start_date
        all_rates_data = []

        # Цикл, разбивающий большой период на части по 365 дней
        while current_start <= self.end_date:
            period_end = current_start + timedelta(days=MAX_DAYS - 1)
            
            if period_end > self.end_date:
                period_end = self.end_date

            url = f"{BASE_URL}/{currency}/{current_start.isoformat()}/{period_end.isoformat()}/"
            
            try:
                print(f"DEBUG NBP: Fetching {currency} from {current_start} to {period_end}")
                response = requests.get(url, headers={"Accept": "application/json"})
                response.raise_for_status() 
                
                data = response.json()
                
                if 'rates' in data:
                    all_rates_data.extend(data['rates'])
                
                current_start = period_end + timedelta(days=1)

            except requests.exceptions.RequestException as e:
                print(f"NBP API Error for {currency} on period {current_start}-{period_end}: {e}")
                return pd.DataFrame() 
            except Exception as e:
                print(f"An unexpected error occurred for {currency}: {e}")
                return pd.DataFrame()

        if not all_rates_data:
            return pd.DataFrame()
        
        # Объединяем все полученные данные в один DataFrame
        df = pd.DataFrame(all_rates_data)
        
        # Нормализация данных
        df.rename(columns={'mid': f'Rate_PLN_{currency}', 'effectiveDate': 'Date'}, inplace=True)
        
        # !!! КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: сохраняем pd.Timestamp !!!
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        # Удаляем дубликаты и сортируем
        df = df[~df.index.duplicated(keep='last')]
        df.sort_index(inplace=True)
        
        return df[[f'Rate_PLN_{currency}']]