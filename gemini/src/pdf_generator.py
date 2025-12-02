from fpdf import FPDF
from typing import Dict, Any, List
from datetime import date
import os

# Set output directory (must match JSON exporter)
OUTPUT_DIR = 'output'

class PDFReport(FPDF):
    """Custom FPDF class to handle headers, footers, and page breaks."""
    
    def header(self):
        """PDF Header implementation."""
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Interactive Brokers PIT-38 Report', 0, 1, 'L')
        self.set_font('Arial', '', 10)
        self.cell(0, 5, f'Reporting Period: {self.report_period}', 0, 1, 'L')
        self.line(10, 20, 200, 20)
        self.ln(5)

    def footer(self):
        """PDF Footer implementation."""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

class PDFGenerator:
    """Generates the multi-page PDF document from the calculated dataset."""
    
    def __init__(self, data_set: Dict[str, Any], year: int):
        self.data_set = data_set
        self.year = year
        self.pdf = PDFReport()
        self.pdf.report_period = str(year)
        self.pdf.set_auto_page_break(auto=True, margin=15)
        self.pdf.alias_nb_pages() # Enables {nb} in footer

    def _add_title_page(self):
        """Creates the initial title page."""
        self.pdf.add_page()
        self.pdf.set_font('Arial', 'B', 24)
        self.pdf.cell(0, 50, 'Annual PIT-38 Investment Report', 0, 1, 'C')
        self.pdf.set_font('Arial', '', 14)
        self.pdf.cell(0, 10, f'Generated for Tax Year: {self.year}', 0, 1, 'C')
        self.pdf.ln(20)
        self.pdf.set_font('Arial', 'I', 10)
        self.pdf.cell(0, 10, f'Report generated on: {date.today().isoformat()}', 0, 1, 'C')

    def _add_summary_table(self):
        """Adds a summary table of key financial results."""
        self.pdf.add_page()
        self.pdf.set_font('Arial', 'B', 16)
        self.pdf.cell(0, 10, '1. Annual Financial Summary (PLN)', 0, 1, 'L')
        self.pdf.set_font('Arial', '', 12)

        # Get summary data (assumes summary_stats is prepared in tax_engine)
        total_pnl = self.data_set.get('summary_stats', {}).get('total_pnl_pln', 0.0)
        total_dividends = self.data_set.get('summary_stats', {}).get('total_gross_dividends_pln', 0.0)

        # Simple table structure
        col_width = 70
        self.pdf.cell(col_width, 8, 'Total Realized P&L (PLN):', 1, 0, 'L')
        self.pdf.cell(col_width, 8, f'{total_pnl:,.2f} PLN', 1, 1, 'R')

        self.pdf.cell(col_width, 8, 'Total Gross Dividends (PLN):', 1, 0, 'L')
        self.pdf.cell(col_width, 8, f'{total_dividends:,.2f} PLN', 1, 1, 'R')
        self.pdf.ln(10)

    def _add_trades_table(self):
        """Adds a detailed table of all realized transactions."""
        self.pdf.add_page()
        self.pdf.set_font('Arial', 'B', 16)
        self.pdf.cell(0, 10, '2. Detailed Realized Transactions (For PIT-38)', 0, 1, 'L')
        
        # Define table columns
        header = ['Date', 'Symbol', 'Revenue (PLN)', 'Cost Basis (PLN)', 'P&L (PLN)']
        col_widths = [25, 25, 40, 40, 40]
        self.pdf.set_font('Arial', 'B', 8)
        
        # Print header
        for col, width in zip(header, col_widths):
            self.pdf.cell(width, 7, col, 1, 0, 'C')
        self.pdf.ln()

        # Print data rows
        self.pdf.set_font('Arial', '', 8)
        for tx in self.data_set.get('realized_gains_losses', []):
            self.pdf.cell(col_widths[0], 6, tx['date'][:10], 1, 0)
            self.pdf.cell(col_widths[1], 6, tx['symbol'], 1, 0)
            self.pdf.cell(col_widths[2], 6, f"{tx['gross_revenue_pln']:,.2f}", 1, 0, 'R')
            self.pdf.cell(col_widths[3], 6, f"{tx['cost_basis_pln']:,.2f}", 1, 0, 'R')
            self.pdf.cell(col_widths[4], 6, f"{tx['pnl_pln']:,.2f}", 1, 1, 'R')
            
            # Check for page break necessity
            if self.pdf.get_y() > 270:
                 self.pdf.add_page()
                 self.pdf.set_font('Arial', 'B', 8)
                 for col, width in zip(header, col_widths):
                    self.pdf.cell(width, 7, col, 1, 0, 'C')
                 self.pdf.ln()
                 self.pdf.set_font('Arial', '', 8)

    def generate_report(self) -> str:
        """Runs the entire report generation process."""
        self._add_title_page()
        self._add_summary_table()
        self._add_trades_table()
        # You would add tables for Dividends, Open Positions, and Monthly Yield here.
        
        filename = f'pit38_report_{self.year}.pdf'
        file_path = os.path.join(OUTPUT_DIR, filename)
        
        self.pdf.output(file_path)
        print(f"PDF Report generation successful: {file_path}")
        return file_path

# Example usage (called from main.py)
# if __name__ == '__main__':
#     # The PDF generator requires that you install fpdf2: pip install fpdf2
#     # Assuming mock_final_data is available from tax_engine
#     pdf_gen = PDFGenerator(mock_final_data, year=2024)
#     pdf_gen.generate_report()