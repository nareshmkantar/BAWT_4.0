"""
Export Database to Excel
Exports the BAWT database to two Excel files:
1. input_data.xlsx - All input/configuration data
2. results_data.xlsx - Results and audit data
"""

import sqlite3
import os
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    print("pandas not installed. Installing...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'pandas', 'openpyxl'])
    import pandas as pd


def export_database_to_excel():
    """Export all database tables to two Excel files."""
    
    # Database path
    db_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(db_dir, 'data', 'bawt.db')
    
    # Output paths
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    input_file = os.path.join(db_dir, 'data', f'input_data_{timestamp}.xlsx')
    results_file = os.path.join(db_dir, 'data', f'results_data_{timestamp}.xlsx')
    
    # Ensure data directory exists
    os.makedirs(os.path.join(db_dir, 'data'), exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    
    # ==========================================
    # INPUT DATA EXCEL FILE
    # ==========================================
    print("Creating input data Excel file...")
    
    input_tables = {
        'Response Curves': 'SELECT * FROM response_curves ORDER BY curve_ref',
        'Weekly Spend': 'SELECT * FROM weekly_spend ORDER BY curve_ref, week',
        'Weekly CPMs': 'SELECT * FROM weekly_cpms ORDER BY curve_ref, week',
        'Weekly Constraints': 'SELECT * FROM weekly_constraints ORDER BY curve_ref, constraint_type, week',
        'Weekly Weights': 'SELECT * FROM weekly_weights ORDER BY curve_ref, week',
        'Optimizer Controls': 'SELECT * FROM optimizer_controls ORDER BY category, setting_name',
        'Hierarchy': 'SELECT * FROM hierarchy ORDER BY market, brand, sub_brand, channel',
    }
    
    with pd.ExcelWriter(input_file, engine='openpyxl') as writer:
        for sheet_name, query in input_tables.items():
            try:
                df = pd.read_sql_query(query, conn)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"  ✓ Exported '{sheet_name}' ({len(df)} rows)")
            except Exception as e:
                print(f"  ✗ Error exporting '{sheet_name}': {e}")
    
    print(f"\n✓ Input data saved to: {input_file}")
    
    # ==========================================
    # RESULTS DATA EXCEL FILE
    # ==========================================
    print("\nCreating results data Excel file...")
    
    results_tables = {
        'Results': 'SELECT * FROM results ORDER BY created_at DESC',
        'Allocations': 'SELECT * FROM allocations ORDER BY result_id, curve_ref',
        'Audit Log': 'SELECT * FROM audit_log ORDER BY timestamp DESC',
    }
    
    with pd.ExcelWriter(results_file, engine='openpyxl') as writer:
        for sheet_name, query in results_tables.items():
            try:
                df = pd.read_sql_query(query, conn)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"  ✓ Exported '{sheet_name}' ({len(df)} rows)")
            except Exception as e:
                print(f"  ✗ Error exporting '{sheet_name}': {e}")
    
    print(f"\n✓ Results data saved to: {results_file}")
    
    conn.close()
    
    print("\n" + "="*50)
    print("EXPORT COMPLETE!")
    print("="*50)
    print(f"\nFiles created:")
    print(f"  1. {input_file}")
    print(f"  2. {results_file}")
    
    return input_file, results_file


if __name__ == '__main__':
    export_database_to_excel()
