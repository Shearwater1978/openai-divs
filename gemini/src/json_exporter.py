import json
import os
from datetime import datetime
from typing import Dict, Any

class JSONExporter:
    """
    Exports the final calculated tax data (golden_dataset) into a structured 
    JSON file for archival and further processing.
    """
    
    # Конструктор принимает 3 явных позиционных аргумента
    def __init__(self, golden_dataset: Dict[str, Any], output_dir: str, report_year: int):
        self.golden_dataset = golden_dataset
        self.output_dir = output_dir
        self.report_year = report_year

    def export(self):
        """
        Writes the golden dataset to a JSON file in the specified output directory.
        """
        # Create a timestamped filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"tax_report_{self.report_year}_{timestamp}.json"
        full_path = os.path.join(self.output_dir, filename)
        
        # Prepare data for cleaner JSON output, including the new unrealized_lots
        export_data = {
            "metadata": {
                "report_year": self.report_year,
                "generation_date": datetime.now().isoformat()
            },
            "summary": self.golden_dataset.get('summary_stats', {}),
            "realized_gains_losses": self.golden_dataset.get('realized_gains_losses', []),
            "processed_dividends": self.golden_dataset.get('processed_dividends', []),
            # CRITICAL ADDITION: Include the serialized cost basis history
            "unrealized_lots": self.golden_dataset.get('unrealized_lots', {})
        }

        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=4)
            print(f"✅ Data successfully exported to JSON: {full_path}")
        except Exception as e:
            print(f"❌ Error exporting data to JSON: {e}")