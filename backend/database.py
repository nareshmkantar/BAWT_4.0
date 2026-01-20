"""
BAWT Backend - Database
SQLite database for storing results and metadata
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid


class Database:
    """SQLite database manager for BAWT."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(db_dir, 'data', 'bawt.db')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                model_id TEXT,
                curve_type TEXT,
                time_period TEXT,
                source TEXT,
                owner TEXT,
                status TEXT DEFAULT 'draft',
                data TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        # Audit log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id TEXT,
                action TEXT,
                user TEXT,
                timestamp TEXT,
                details TEXT
            )
        ''')
        
        # Optimizer Controls table (matches controls_workspace.csv)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimizer_controls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_name TEXT NOT NULL UNIQUE,
                setting_value TEXT NOT NULL,
                description TEXT,
                category TEXT,
                updated_at TEXT
            )
        ''')
        
        # Response Curves table (matches curves_workspace_internal.csv)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS response_curves (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                curve_ref INTEGER NOT NULL UNIQUE,
                market TEXT,
                category TEXT,
                brand TEXT,
                sub_brand TEXT,
                variant TEXT,
                campaign TEXT,
                channel TEXT,
                partner TEXT,
                buy TEXT,
                format TEXT,
                curve_type TEXT DEFAULT 'hill',
                adstock REAL DEFAULT 0.3,
                param_a REAL,
                param_b REAL,
                param_c REAL,
                param_d REAL,
                param_e REAL,
                param_f REAL,
                param_g REAL,
                param_h REAL,
                param_i REAL,
                param_j REAL,
                updated_at TEXT
            )
        ''')
        
        # Weekly Spend table (matches budget_workspace.csv)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_spend (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                curve_ref INTEGER NOT NULL,
                week TEXT NOT NULL,
                spend REAL DEFAULT 0,
                UNIQUE(curve_ref, week)
            )
        ''')
        
        # Weekly Constraints table (matches constraints_workspace.csv)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_constraints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                curve_ref INTEGER NOT NULL,
                constraint_type TEXT NOT NULL CHECK(constraint_type IN ('Min', 'Max', 'Equal')),
                week TEXT NOT NULL,
                value REAL DEFAULT 0,
                UNIQUE(curve_ref, constraint_type, week)
            )
        ''')
        
        # Weekly CPMs table (matches cpm_workspace.csv)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_cpms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                curve_ref INTEGER NOT NULL,
                week TEXT NOT NULL,
                cpm REAL DEFAULT 0,
                UNIQUE(curve_ref, week)
            )
        ''')
        
        # Weekly Weights table (matches weights_workspace.csv)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                curve_ref INTEGER NOT NULL,
                week TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                UNIQUE(curve_ref, week)
            )
        ''')
        
        # Hierarchy table (for cascading dropdowns)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hierarchy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market TEXT NOT NULL,
                brand TEXT NOT NULL,
                sub_brand TEXT DEFAULT 'All',
                channel TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Allocations table (optimization results)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS allocations (
                id TEXT PRIMARY KEY,
                result_id TEXT,
                curve_ref INTEGER NOT NULL,
                current_spend REAL NOT NULL,
                optimized_spend REAL NOT NULL,
                impressions REAL,
                response REAL,
                marginal_roi REAL,
                roi REAL,
                incr_volume REAL,
                brand_lift REAL,
                created_at TEXT,
                FOREIGN KEY (result_id) REFERENCES results(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Insert sample data if empty
        self._seed_data()
    
    def _seed_data(self):
        """Seed initial sample data matching template structures."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # Check if results exist
        cursor.execute('SELECT COUNT(*) FROM results')
        if cursor.fetchone()[0] == 0:
            sample_results = [
                {"id": "RES-001", "type": "Simulation", "name": "Q4 Budget Plan", "model_id": "brand-a-us", "curve_type": "short", "time_period": "Q4 2024", "source": "default", "owner": "Demo User", "status": "approved", "data": json.dumps({"curves": [], "totals": {}})},
                {"id": "RES-002", "type": "Optimization", "name": "Marketing Shift", "model_id": "brand-a-us", "curve_type": "long", "time_period": "Q4 2024", "source": "upload", "owner": "Demo User", "status": "applied", "data": json.dumps({"curves": [], "totals": {}})},
                {"id": "RES-003", "type": "Simulation", "name": "Cost Analysis", "model_id": "brand-b-us", "curve_type": "short", "time_period": "Q3 2024", "source": "result", "owner": "Admin", "status": "draft", "data": json.dumps({"curves": [], "totals": {}})}
            ]
            for result in sample_results:
                cursor.execute('INSERT INTO results (id, type, name, model_id, curve_type, time_period, source, owner, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (result['id'], result['type'], result['name'], result['model_id'], result['curve_type'], result['time_period'], result['source'], result['owner'], result['status'], result['data'], now, now))
        
        # Seed optimizer controls (matches controls_workspace.csv)
        cursor.execute('SELECT COUNT(*) FROM optimizer_controls')
        if cursor.fetchone()[0] == 0:
            controls = [
                ('objective_type', 'MaxRevenue', 'Optimization objective: MaxRevenue or MinBudget', 'General'),
                ('target_kpi', 'value', 'KPI to optimize: value, profit, sales, reach', 'General'),
                ('optimization_period_start', '2024_wk1', 'Start week for optimization window', 'General'),
                ('optimization_period_end', '2025_wk52', 'End week for optimization window', 'General'),
                ('total_budget_constraint', '5000000', 'Total budget cap across all curves', 'Budget'),
                ('budget_flex_percent', '20', 'Percentage flexibility allowed on total budget', 'Budget'),
                ('min_curve_spend_percent', '5', 'Minimum spend per curve as % of its baseline', 'Curve Rules'),
                ('max_curve_spend_percent', '300', 'Maximum spend per curve as % of its baseline', 'Curve Rules'),
                ('seasonality_enabled', 'true', 'Whether to apply seasonality factors', 'Seasonality'),
                ('default_seasonality_factor', '1.0', 'Default weight when not specified', 'Seasonality'),
                ('kpi_value_scalar', '1.0', 'Scalar multiplier for Value KPI', 'KPI Scalars'),
                ('kpi_profit_scalar', '0.35', 'Profit margin percentage', 'KPI Scalars'),
                ('kpi_reach_scalar', '1000', 'Impressions to reach conversion factor', 'KPI Scalars'),
            ]
            for c in controls:
                cursor.execute('INSERT INTO optimizer_controls (setting_name, setting_value, description, category, updated_at) VALUES (?, ?, ?, ?, ?)',
                    (c[0], c[1], c[2], c[3], now))
        
        # Seed response curves (matches curves_workspace_internal.csv)
        cursor.execute('SELECT COUNT(*) FROM response_curves')
        if cursor.fetchone()[0] == 0:
            curves = [
                (1, 'UK', 'Stain removal', 'Vanish', 'Vanish Oxy Action', 'Powder', 'Back to school', 'TV', 'ITV', 'Breakfast', '30s', 'atan', 0.7, 0.1, 0.2, 0.3, 0.4, None, None, None, None, None, None),
                (2, 'UK', 'Stain removal', 'Vanish', 'Vanish Oxy Action', 'Powder', 'Back to school', 'Digital', 'Meta', 'Paid Social', 'Video', 'hill', 0.3, 100000, 1.8, 1000000, 0.08, None, None, None, None, None, None),
                (3, 'UK', 'Stain removal', 'Vanish', 'Vanish Oxy Action', 'Powder', 'Back to school', 'Digital', 'Google', 'Search', 'Text', 'scurve', 0.2, 0.15, 0.25, 0.5, None, None, None, None, None, None, None),
                (4, 'UK', 'Stain removal', 'Vanish', 'Vanish Oxy Action', 'Powder', 'Always-on', 'OOH', 'JCDecaux', 'Digital Screens', '6-sheet', 'hill', 0.4, 80000, 1.5, 500000, 0.05, None, None, None, None, None, None),
                (5, 'UK', 'Stain removal', 'Vanish', 'Vanish Oxy Action', 'Gel', 'Spring Clean', 'TV', 'Channel 4', 'Prime', '30s', 'atan', 0.65, 0.12, 0.22, 0.35, 0.42, None, None, None, None, None, None),
                (6, 'UK', 'Stain removal', 'Vanish', 'Vanish Oxy Action', 'Gel', 'Spring Clean', 'Digital', 'Google', 'Display', 'Banner', 'hill', 0.25, 120000, 2.0, 800000, 0.06, None, None, None, None, None, None),
            ]
            for c in curves:
                cursor.execute('''INSERT INTO response_curves 
                    (curve_ref, market, category, brand, sub_brand, variant, campaign, channel, partner, buy, format, curve_type, adstock, param_a, param_b, param_c, param_d, param_e, param_f, param_g, param_h, param_i, param_j, updated_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (*c, now))
        
        # Seed weekly spend (sample data for a few weeks)
        cursor.execute('SELECT COUNT(*) FROM weekly_spend')
        if cursor.fetchone()[0] == 0:
            sample_weeks = ['2024_wk33', '2024_wk34', '2024_wk35', '2024_wk36', '2024_wk37', '2024_wk38']
            spend_data = {
                1: [25000, 25000, 30000, 30000, 25000, 20000],  # TV - ITV
                2: [5000, 5000, 5000, 5000, 5000, 5000],        # Digital - Meta
                3: [3000, 3000, 3000, 3000, 3000, 3000],        # Search
                4: [1000, 1000, 1000, 1000, 1000, 1000],        # OOH
                5: [0, 0, 0, 0, 0, 0],                          # Spring campaign (not active)
                6: [0, 0, 0, 0, 0, 0],                          # Spring campaign (not active)
            }
            for curve_ref, spends in spend_data.items():
                for i, week in enumerate(sample_weeks):
                    cursor.execute('INSERT INTO weekly_spend (curve_ref, week, spend) VALUES (?, ?, ?)',
                        (curve_ref, week, spends[i]))
        
        # Seed weekly constraints (sample data)
        cursor.execute('SELECT COUNT(*) FROM weekly_constraints')
        if cursor.fetchone()[0] == 0:
            sample_weeks = ['2024_wk33', '2024_wk34', '2024_wk35', '2024_wk36', '2024_wk37', '2024_wk38']
            constraints = [
                (1, 'Max', [50000, 50000, 60000, 60000, 60000, 50000]),
                (2, 'Max', [10000, 10000, 12000, 12000, 12000, 10000]),
                (2, 'Min', [2000, 2000, 2000, 2000, 2000, 2000]),
                (3, 'Max', [5000, 5000, 5000, 5000, 5000, 5000]),
                (4, 'Max', [3000, 3000, 3000, 3000, 3000, 3000]),
            ]
            for curve_ref, ctype, values in constraints:
                for i, week in enumerate(sample_weeks):
                    cursor.execute('INSERT INTO weekly_constraints (curve_ref, constraint_type, week, value) VALUES (?, ?, ?, ?)',
                        (curve_ref, ctype, week, values[i]))
        
        # Seed weekly CPMs (sample data)
        cursor.execute('SELECT COUNT(*) FROM weekly_cpms')
        if cursor.fetchone()[0] == 0:
            sample_weeks = ['2024_wk33', '2024_wk34', '2024_wk35', '2024_wk36', '2024_wk37', '2024_wk38']
            cpms = {
                1: [2600, 2600, 2600, 2600, 2600, 2600],     # TV
                2: [52000, 52000, 52000, 52000, 52000, 52000],  # Meta (large audience)
                3: [1050, 1050, 1050, 1050, 1050, 1050],     # Search
                4: [520, 520, 520, 520, 520, 520],           # OOH
                5: [2700, 2700, 2700, 2700, 2700, 2700],     # TV - Spring
                6: [3100, 3100, 3100, 3100, 3100, 3100],     # Display
            }
            for curve_ref, values in cpms.items():
                for i, week in enumerate(sample_weeks):
                    cursor.execute('INSERT INTO weekly_cpms (curve_ref, week, cpm) VALUES (?, ?, ?)',
                        (curve_ref, week, values[i]))
        
        # Seed weekly weights (seasonality factors)
        cursor.execute('SELECT COUNT(*) FROM weekly_weights')
        if cursor.fetchone()[0] == 0:
            sample_weeks = ['2024_wk33', '2024_wk34', '2024_wk35', '2024_wk36', '2024_wk37', '2024_wk38']
            weights = {
                1: [1.5, 1.5, 1.5, 1.5, 1.5, 1.0],  # BTS campaign - TV
                2: [1.8, 1.8, 1.8, 1.8, 1.8, 1.0],  # BTS campaign - Digital stronger
                3: [1.2, 1.2, 1.2, 1.2, 1.2, 1.0],  # BTS campaign - Search
                4: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],  # Always-on - flat
                5: [0.8, 0.8, 0.8, 0.8, 0.8, 0.8],  # Off-season
                6: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],  # Flat
            }
            for curve_ref, values in weights.items():
                for i, week in enumerate(sample_weeks):
                    cursor.execute('INSERT INTO weekly_weights (curve_ref, week, weight) VALUES (?, ?, ?)',
                        (curve_ref, week, values[i]))
        
        # Seed hierarchy
        cursor.execute('SELECT COUNT(*) FROM hierarchy')
        if cursor.fetchone()[0] == 0:
            hierarchy = [
                ("UK", "Vanish", "Vanish Oxy Action", "TV"),
                ("UK", "Vanish", "Vanish Oxy Action", "Digital"),
                ("UK", "Vanish", "Vanish Oxy Action", "OOH"),
                ("UK", "Vanish", "Gold range", "TV"),
                ("UK", "Vanish", "Gold range", "Digital"),
                ("US", "OxiClean", "OxiClean Max", "TV"),
                ("US", "OxiClean", "OxiClean Max", "Digital"),
            ]
            for h in hierarchy:
                cursor.execute('INSERT INTO hierarchy (market, brand, sub_brand, channel) VALUES (?, ?, ?, ?)', h)
        
        conn.commit()
        conn.close()
    
    # ==========================================
    # RESPONSE CURVES METHODS
    # ==========================================
    
    def get_curves(self, market: str = None, brand: str = None, sub_brand: str = None) -> List[Dict[str, Any]]:
        """Get response curves filtered by hierarchy."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM response_curves WHERE 1=1'
        params = []
        if market:
            query += ' AND market = ?'
            params.append(market)
        if brand:
            query += ' AND brand = ?'
            params.append(brand)
        if sub_brand:
            query += ' AND sub_brand = ?'
            params.append(sub_brand)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def save_curve(self, curve: Dict[str, Any]) -> int:
        """Save or update a response curve."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO response_curves 
            (curve_ref, market, category, brand, sub_brand, variant, campaign, channel, partner, buy, format, 
             curve_type, adstock, param_a, param_b, param_c, param_d, param_e, param_f, param_g, param_h, param_i, param_j, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            curve['curve_ref'], curve.get('market'), curve.get('category'), curve.get('brand'),
            curve.get('sub_brand'), curve.get('variant'), curve.get('campaign'), curve.get('channel'),
            curve.get('partner'), curve.get('buy'), curve.get('format'), curve.get('curve_type', 'hill'),
            curve.get('adstock', 0.3), curve.get('param_a'), curve.get('param_b'), curve.get('param_c'),
            curve.get('param_d'), curve.get('param_e'), curve.get('param_f'), curve.get('param_g'),
            curve.get('param_h'), curve.get('param_i'), curve.get('param_j'), now
        ))
        
        conn.commit()
        conn.close()
        return curve['curve_ref']
    
    # ==========================================
    # OPTIMIZER CONTROLS METHODS
    # ==========================================
    
    def get_controls(self) -> List[Dict[str, Any]]:
        """Get all optimizer control settings."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM optimizer_controls ORDER BY category, setting_name')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def save_control(self, setting_name: str, setting_value: str) -> None:
        """Save or update a control setting."""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO optimizer_controls (setting_name, setting_value, updated_at)
            VALUES (?, ?, ?)
        ''', (setting_name, setting_value, now))
        conn.commit()
        conn.close()
    
    # ==========================================
    # WEEKLY CPM METHODS
    # ==========================================
    
    def get_weekly_cpms(self, curve_ref: int = None) -> List[Dict[str, Any]]:
        """Get weekly CPM data filtered by curve_ref."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if curve_ref:
            cursor.execute('SELECT * FROM weekly_cpms WHERE curve_ref = ? ORDER BY week', (curve_ref,))
        else:
            cursor.execute('SELECT * FROM weekly_cpms ORDER BY curve_ref, week')
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def save_weekly_cpm(self, curve_ref: int, week: str, cpm: float) -> None:
        """Save or update a weekly CPM value."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO weekly_cpms (curve_ref, week, cpm)
            VALUES (?, ?, ?)
        ''', (curve_ref, week, cpm))
        conn.commit()
        conn.close()
    
    # ==========================================
    # WEEKLY SPEND METHODS
    # ==========================================
    
    def get_weekly_spend(self, curve_ref: int = None) -> List[Dict[str, Any]]:
        """Get weekly spend data filtered by curve_ref."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if curve_ref:
            cursor.execute('SELECT * FROM weekly_spend WHERE curve_ref = ? ORDER BY week', (curve_ref,))
        else:
            cursor.execute('SELECT * FROM weekly_spend ORDER BY curve_ref, week')
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def save_weekly_spend(self, curve_ref: int, week: str, spend: float) -> None:
        """Save or update a weekly spend value."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO weekly_spend (curve_ref, week, spend)
            VALUES (?, ?, ?)
        ''', (curve_ref, week, spend))
        conn.commit()
        conn.close()
    
    # ==========================================
    # WEEKLY CONSTRAINTS METHODS
    # ==========================================
    
    def get_weekly_constraints(self, curve_ref: int = None) -> List[Dict[str, Any]]:
        """Get weekly constraint data filtered by curve_ref."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if curve_ref:
            cursor.execute('SELECT * FROM weekly_constraints WHERE curve_ref = ? ORDER BY constraint_type, week', (curve_ref,))
        else:
            cursor.execute('SELECT * FROM weekly_constraints ORDER BY curve_ref, constraint_type, week')
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def save_weekly_constraint(self, curve_ref: int, constraint_type: str, week: str, value: float) -> None:
        """Save or update a weekly constraint value."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO weekly_constraints (curve_ref, constraint_type, week, value)
            VALUES (?, ?, ?, ?)
        ''', (curve_ref, constraint_type, week, value))
        conn.commit()
        conn.close()
    
    # ==========================================
    # WEEKLY WEIGHTS METHODS
    # ==========================================
    
    def get_weekly_weights(self, curve_ref: int = None) -> List[Dict[str, Any]]:
        """Get weekly weight data filtered by curve_ref."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if curve_ref:
            cursor.execute('SELECT * FROM weekly_weights WHERE curve_ref = ? ORDER BY week', (curve_ref,))
        else:
            cursor.execute('SELECT * FROM weekly_weights ORDER BY curve_ref, week')
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def save_weekly_weight(self, curve_ref: int, week: str, weight: float) -> None:
        """Save or update a weekly weight value."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO weekly_weights (curve_ref, week, weight)
            VALUES (?, ?, ?)
        ''', (curve_ref, week, weight))
        conn.commit()
        conn.close()
    
    # ==========================================
    # HIERARCHY METHODS
    # ==========================================
    
    def get_hierarchy(self) -> Dict[str, Any]:
        """Get full hierarchy for cascading dropdowns."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT market FROM hierarchy WHERE is_active = 1')
        markets = [row['market'] for row in cursor.fetchall()]
        
        hierarchy = {}
        for market in markets:
            hierarchy[market] = {}
            cursor.execute('SELECT DISTINCT brand FROM hierarchy WHERE market = ? AND is_active = 1', (market,))
            brands = [row['brand'] for row in cursor.fetchall()]
            
            for brand in brands:
                cursor.execute('SELECT DISTINCT sub_brand FROM hierarchy WHERE market = ? AND brand = ? AND is_active = 1', (market, brand))
                hierarchy[market][brand] = {}
                sub_brands = [row['sub_brand'] for row in cursor.fetchall()]
                
                for sub_brand in sub_brands:
                    cursor.execute('SELECT channel FROM hierarchy WHERE market = ? AND brand = ? AND sub_brand = ? AND is_active = 1', (market, brand, sub_brand))
                    hierarchy[market][brand][sub_brand] = [row['channel'] for row in cursor.fetchall()]
        
        conn.close()
        return hierarchy
    
    def get_weeks(self, market: str = None, brand: str = None) -> List[str]:
        """Get available weeks for CPM data."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT DISTINCT week_start FROM cpms'
        params = []
        if market:
            query += ' WHERE market = ?'
            params.append(market)
            if brand:
                query += ' AND brand = ?'
                params.append(brand)
        query += ' ORDER BY week_start DESC'
        
        cursor.execute(query, params)
        weeks = [row['week_start'] for row in cursor.fetchall()]
        conn.close()
        return weeks
    
    def get_all_results(self) -> List[Dict[str, Any]]:
        """Get all saved results."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM results ORDER BY created_at DESC')
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row['id'],
                "type": row['type'],
                "name": row['name'],
                "model_id": row['model_id'],
                "curve_type": row['curve_type'],
                "time_period": row['time_period'],
                "source": row['source'],
                "owner": row['owner'],
                "status": row['status'],
                "created_at": row['created_at'],
                "updated_at": row['updated_at']
            })
        
        conn.close()
        return results
    
    def get_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific result by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM results WHERE id = ?', (result_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return {
                "id": row['id'],
                "type": row['type'],
                "name": row['name'],
                "model_id": row['model_id'],
                "curve_type": row['curve_type'],
                "time_period": row['time_period'],
                "source": row['source'],
                "owner": row['owner'],
                "status": row['status'],
                "data": json.loads(row['data']) if row['data'] else {},
                "created_at": row['created_at'],
                "updated_at": row['updated_at']
            }
        return None
    
    def save_result(self, result: Dict[str, Any]) -> str:
        """Save a new result."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        result_id = result.get('id', f"RES-{uuid.uuid4().hex[:8].upper()}")
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO results (id, type, name, model_id, curve_type, time_period, source, owner, status, data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result_id,
            result.get('type', 'Simulation'),
            result.get('name', 'Untitled'),
            result.get('model_id', ''),
            result.get('curve_type', 'short'),
            result.get('time_period', ''),
            result.get('source', 'default'),
            result.get('owner', 'User'),
            result.get('status', 'draft'),
            json.dumps(result.get('data', {})),
            result.get('created_at', now),
            now
        ))
        
        # Log audit
        cursor.execute('''
            INSERT INTO audit_log (result_id, action, user, timestamp, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (result_id, 'save', result.get('owner', 'User'), now, 'Result saved'))
        
        conn.commit()
        conn.close()
        
        return result_id
    
    def delete_result(self, result_id: str) -> bool:
        """Delete a result."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM results WHERE id = ?', (result_id,))
        deleted = cursor.rowcount > 0
        
        if deleted:
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO audit_log (result_id, action, user, timestamp, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (result_id, 'delete', 'User', now, 'Result deleted'))
        
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_audit_log(self, result_id: str = None) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if result_id:
            cursor.execute('SELECT * FROM audit_log WHERE result_id = ? ORDER BY timestamp DESC', (result_id,))
        else:
            cursor.execute('SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 100')
        
        rows = cursor.fetchall()
        
        logs = []
        for row in rows:
            logs.append({
                "id": row['id'],
                "result_id": row['result_id'],
                "action": row['action'],
                "user": row['user'],
                "timestamp": row['timestamp'],
                "details": row['details']
            })
        
        conn.close()
        return logs
