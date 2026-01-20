"""
BAWT Backend - Flask API
Media Mix Model Budget Allocation Workflow Tool

Run with: python backend/app.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime
from models import MMModel, ResponseCurve
from database import Database
from optimizer import optimizer

app = Flask(__name__)
CORS(app)

# Initialize database
db = Database()

# Sample data paths
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


# ==========================================
# MODELS & CURVES
# ==========================================

@app.route('/api/models', methods=['GET'])
def get_models():
    """Get all available MMM models."""
    models = [
        {"id": "brand-a-us", "name": "Brand A - US", "market": "United States", "brand": "Brand A", "status": "active"},
        {"id": "brand-a-uk", "name": "Brand A - UK", "market": "United Kingdom", "brand": "Brand A", "status": "active"},
        {"id": "brand-b-us", "name": "Brand B - US", "market": "United States", "brand": "Brand B", "status": "active"},
        {"id": "brand-b-de", "name": "Brand B - DE", "market": "Germany", "brand": "Brand B", "status": "draft"}
    ]
    return jsonify({"success": True, "data": models})


@app.route('/api/curves/<model_id>', methods=['GET'])
def get_curves(model_id):
    """Get curves for a specific model."""
    curve_type = request.args.get('type', 'short')  # short or long
    
    # Sample curve data with MMM parameters
    curves = [
        {
            "id": "paid-social-brand",
            "name": "Paid Social - Brand",
            "channel": "Paid Social",
            "campaign_type": "Brand",
            "color": "#4f8cff",
            "curve_type": curve_type,
            "parameters": {
                "saturation_k": 0.0012,  # Hill function K
                "saturation_s": 1.8,      # Hill function S (shape)
                "adstock_decay": 0.7,     # Decay rate
                "adstock_halflife": 2.3    # Weeks
            },
            "observed_range": {"min": 200000, "max": 800000},
            "default_spend": 500000,
            "cpm": 12.50
        },
        {
            "id": "paid-social-perf",
            "name": "Paid Social - Perf",
            "channel": "Paid Social",
            "campaign_type": "Performance",
            "color": "#00d4aa",
            "curve_type": curve_type,
            "parameters": {
                "saturation_k": 0.0015,
                "saturation_s": 2.1,
                "adstock_decay": 0.5,
                "adstock_halflife": 1.4
            },
            "observed_range": {"min": 100000, "max": 500000},
            "default_spend": 300000,
            "cpm": 8.00
        },
        {
            "id": "display-brand",
            "name": "Display - Brand",
            "channel": "Display",
            "campaign_type": "Brand",
            "color": "#9d7cff",
            "curve_type": curve_type,
            "parameters": {
                "saturation_k": 0.0008,
                "saturation_s": 1.5,
                "adstock_decay": 0.6,
                "adstock_halflife": 1.8
            },
            "observed_range": {"min": 100000, "max": 400000},
            "default_spend": 250000,
            "cpm": 15.00
        },
        {
            "id": "display-perf",
            "name": "Display - Perf",
            "channel": "Display",
            "campaign_type": "Performance",
            "color": "#f59e0b",
            "curve_type": curve_type,
            "parameters": {
                "saturation_k": 0.0018,
                "saturation_s": 2.3,
                "adstock_decay": 0.4,
                "adstock_halflife": 1.0
            },
            "observed_range": {"min": 50000, "max": 350000},
            "default_spend": 200000,
            "cpm": 10.00
        },
        {
            "id": "search-brand",
            "name": "Search - Brand",
            "channel": "Search",
            "campaign_type": "Brand",
            "color": "#ef4444",
            "curve_type": curve_type,
            "parameters": {
                "saturation_k": 0.0020,
                "saturation_s": 2.0,
                "adstock_decay": 0.3,
                "adstock_halflife": 0.7
            },
            "observed_range": {"min": 50000, "max": 250000},
            "default_spend": 150000,
            "cpm": 5.00
        },
        {
            "id": "search-perf",
            "name": "Search - Perf",
            "channel": "Search",
            "campaign_type": "Performance",
            "color": "#22c55e",
            "curve_type": curve_type,
            "parameters": {
                "saturation_k": 0.0025,
                "saturation_s": 2.5,
                "adstock_decay": 0.2,
                "adstock_halflife": 0.5
            },
            "observed_range": {"min": 30000, "max": 200000},
            "default_spend": 100000,
            "cpm": 4.50
        }
    ]
    
    return jsonify({"success": True, "data": curves})


# ==========================================
# SIMULATION
# ==========================================

@app.route('/api/simulate', methods=['POST'])
def run_simulation():
    """Run a simulation with the given parameters."""
    data = request.json
    
    model_id = data.get('model_id', 'brand-a-us')
    curve_type = data.get('curve_type', 'short')
    spend_plan = data.get('spend_plan', {})
    
    # Get curves
    curves_response = get_curves(model_id)
    curves = json.loads(curves_response.data)['data']
    
    # Calculate results per curve
    results = []
    warnings = []
    
    for curve in curves:
        curve_id = curve['id']
        spend = spend_plan.get(curve_id, curve['default_spend'])
        
        # Check guardrails
        obs_min = curve['observed_range']['min']
        obs_max = curve['observed_range']['max']
        
        if spend < obs_min * 0.5 or spend > obs_max * 1.5:
            warnings.append({
                "curve": curve['name'],
                "message": f"Spend {spend/1000:.0f}K is outside observed range ({obs_min/1000:.0f}K - {obs_max/1000:.0f}K)"
            })
        
        # Calculate response using Hill function
        params = curve['parameters']
        response = MMModel.hill_saturation(spend, params['saturation_k'], params['saturation_s'])
        
        # Apply adstock for more realistic modeling
        adstocked_response = response * (1 + params['adstock_decay'] * 0.3)
        
        # Calculate KPIs
        volume = adstocked_response * 0.1  # Conversion factor
        value = volume * 30  # Average value per unit
        roi = ((value - spend) / spend) * 100 if spend > 0 else 0
        marginal_roi = MMModel.marginal_roi(spend, params['saturation_k'], params['saturation_s'])
        
        results.append({
            "curve_id": curve_id,
            "name": curve['name'],
            "color": curve['color'],
            "spend": spend,
            "volume": round(volume, 0),
            "value": round(value, 0),
            "roi": round(roi, 1),
            "marginal_roi": round(marginal_roi, 1),
            "delta_vs_default": round((spend - curve['default_spend']) / curve['default_spend'] * 100, 1)
        })
    
    # Aggregate totals
    totals = {
        "spend": sum(r['spend'] for r in results),
        "volume": sum(r['volume'] for r in results),
        "value": sum(r['value'] for r in results)
    }
    totals['roi'] = round((totals['value'] - totals['spend']) / totals['spend'] * 100, 1) if totals['spend'] > 0 else 0
    
    return jsonify({
        "success": True,
        "data": {
            "curves": results,
            "totals": totals,
            "warnings": warnings,
            "metadata": {
                "model_id": model_id,
                "curve_type": curve_type,
                "timestamp": datetime.now().isoformat()
            }
        }
    })


# ==========================================
# OPTIMIZATION
# ==========================================

@app.route('/api/optimize/simple', methods=['POST'])
def run_simple_optimization():
    """Run optimization with constraints."""
    data = request.json
    
    model_id = data.get('model_id', 'brand-a-us')
    curve_type = data.get('curve_type', 'short')
    total_budget = data.get('total_budget', 1500000)
    constraints = data.get('constraints', [])
    objective = data.get('objective', 'value')  # value, volume, or roi
    
    # Get curves
    curves_response = get_curves(model_id)
    curves = json.loads(curves_response.data)['data']
    
    # Simple gradient-based allocation (placeholder for actual optimizer)
    # In production, use scipy.optimize or similar
    results = MMModel.optimize_allocation(curves, total_budget, constraints, objective)
    
    # Calculate totals
    totals = {
        "spend": sum(r['optimized_spend'] for r in results),
        "volume": sum(r['optimized_volume'] for r in results),
        "value": sum(r['optimized_value'] for r in results)
    }
    totals['roi'] = round((totals['value'] - totals['spend']) / totals['spend'] * 100, 1) if totals['spend'] > 0 else 0
    
    return jsonify({
        "success": True,
        "data": {
            "curves": results,
            "totals": totals,
            "constraints_applied": constraints,
            "metadata": {
                "model_id": model_id,
                "curve_type": curve_type,
                "objective": objective,
                "timestamp": datetime.now().isoformat()
            }
        }
    })


# ==========================================
# RESULTS
# ==========================================

@app.route('/api/results', methods=['GET'])
def get_results():
    """Get all saved results."""
    results = db.get_all_results()
    return jsonify({"success": True, "data": results})


@app.route('/api/results', methods=['POST'])
def save_result():
    """Save a simulation/optimization result."""
    data = request.json
    result_id = db.save_result(data)
    return jsonify({"success": True, "id": result_id})


@app.route('/api/results/<result_id>', methods=['GET'])
def get_result(result_id):
    """Get a specific result."""
    result = db.get_result(result_id)
    if result:
        return jsonify({"success": True, "data": result})
    return jsonify({"success": False, "error": "Result not found"}), 404


@app.route('/api/results/<result_id>', methods=['DELETE'])
def delete_result(result_id):
    """Delete a result."""
    success = db.delete_result(result_id)
    return jsonify({"success": success})


# ==========================================
# CPMs
# ==========================================

@app.route('/api/cpms', methods=['GET'])
def get_cpms():
    """Get CPM data."""
    cpms = [
        {"curve_id": "paid-social-brand", "name": "Paid Social - Brand", "cpm": 12.50, "updated": "2024-12-01"},
        {"curve_id": "paid-social-perf", "name": "Paid Social - Perf", "cpm": 8.00, "updated": "2024-12-01"},
        {"curve_id": "display-brand", "name": "Display - Brand", "cpm": 15.00, "updated": "2024-12-01"},
        {"curve_id": "display-perf", "name": "Display - Perf", "cpm": 10.00, "updated": "2024-12-01"},
        {"curve_id": "search-brand", "name": "Search - Brand", "cpm": 5.00, "updated": "2024-12-01"},
        {"curve_id": "search-perf", "name": "Search - Perf", "cpm": 4.50, "updated": "2024-12-01"}
    ]
    return jsonify({"success": True, "data": cpms})


@app.route('/api/cpms', methods=['PUT'])
def update_cpms():
    """Update CPM data."""
    data = request.json
    # In production, save to database
    return jsonify({"success": True, "message": "CPMs updated"})


# ==========================================
# VALIDATION
# ==========================================

@app.route('/api/validate', methods=['POST'])
def validate_plan():
    """Validate an uploaded spend plan."""
    data = request.json
    plan = data.get('plan', {})
    
    errors = []
    warnings = []
    
    # Schema validation
    required_fields = ['curve_id', 'spend']
    for item in plan.get('items', []):
        for field in required_fields:
            if field not in item:
                errors.append(f"Missing required field: {field}")
    
    # Range validation
    for item in plan.get('items', []):
        spend = item.get('spend', 0)
        if spend < 0:
            errors.append(f"Negative spend not allowed: {item.get('curve_id')}")
        if spend > 10000000:
            warnings.append(f"Very high spend: {item.get('curve_id')} = {spend}")
    
    return jsonify({
        "success": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    })


# ==========================================
# MMM DATA ENDPOINTS
# ==========================================

@app.route('/api/hierarchy', methods=['GET'])
def get_hierarchy():
    """Get full hierarchy for cascading dropdowns."""
    try:
        hierarchy = db.get_hierarchy()
        weeks = db.get_weeks()
        return jsonify({
            "success": True, 
            "data": {
                "hierarchy": hierarchy,
                "weeks": weeks
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/response-curves', methods=['GET'])
def get_response_curves():
    """Get response curves filtered by hierarchy."""
    market = request.args.get('market')
    brand = request.args.get('brand')
    sub_brand = request.args.get('sub_brand')
    
    try:
        curves = db.get_curves(market, brand, sub_brand)
        return jsonify({"success": True, "data": curves})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/response-curves', methods=['POST'])
def save_response_curve():
    """Save or update a response curve."""
    try:
        curve = request.json
        curve_id = db.save_curve(curve)
        return jsonify({"success": True, "id": curve_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/cpms', methods=['GET'])
def get_cpm_data():
    """Get CPM data filtered by criteria."""
    market = request.args.get('market')
    brand = request.args.get('brand')
    week_start = request.args.get('week')
    
    try:
        cpms = db.get_cpms(market, brand, week_start)
        return jsonify({"success": True, "data": cpms})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/cpms', methods=['POST'])
def save_cpm_data():
    """Save or update CPM data."""
    try:
        cpm = request.json
        cpm_id = db.save_cpm(cpm)
        return jsonify({"success": True, "id": cpm_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# MMM OPTIMIZATION
# ==========================================

@app.route('/api/optimize', methods=['POST'])
def run_optimization():
    """
    Run marginal ROI optimization.
    
    Request body:
    {
        "market": "US",
        "brand": "Brand A",
        "week": "2024-W50",
        "total_budget": 1000000,
        "current_allocations": {"RC-US-A-PS": 300000, ...},
        "constraints": {"RC-US-A-PS": {"min": 50000, "max": 500000}, ...}
    }
    """
    try:
        data = request.json
        market = data.get('market')
        brand = data.get('brand')
        week = data.get('week')
        total_budget = data.get('total_budget', 1000000)
        current_allocations = data.get('current_allocations', {})
        constraints = data.get('constraints', {})
        
        # Get curves and CPMs
        curves = db.get_curves(market, brand)
        cpms_list = db.get_cpms(market, brand, week)
        
        # Convert CPMs to dict
        cpms = {cpm['id'].replace('CPM', 'RC'): cpm for cpm in cpms_list}
        
        # If no current allocations, use equal distribution
        if not current_allocations:
            per_channel = total_budget / len(curves) if curves else 0
            current_allocations = {c['id']: per_channel for c in curves}
        
        # Run optimization
        result = optimizer.optimize(
            curves=curves,
            current_allocations=current_allocations,
            total_budget=total_budget,
            cpms=cpms,
            constraints=constraints
        )
        
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/simulate-mmm', methods=['POST'])
def run_mmm_simulation():
    """
    Run MMM simulation (calculate metrics without optimization).
    
    Request body:
    {
        "market": "US",
        "brand": "Brand A",
        "week": "2024-W50",
        "allocations": {"RC-US-A-PS": 300000, ...}
    }
    """
    try:
        data = request.json
        market = data.get('market')
        brand = data.get('brand')
        week = data.get('week')
        allocations = data.get('allocations', {})
        
        # Get curves and CPMs
        curves = db.get_curves(market, brand)
        cpms_list = db.get_cpms(market, brand, week)
        cpms = {cpm['id'].replace('CPM', 'RC'): cpm for cpm in cpms_list}
        
        # Run simulation
        result = optimizer.simulate(
            curves=curves,
            allocations=allocations,
            cpms=cpms
        )
        
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# FILE UPLOAD
# ==========================================

@app.route('/api/upload/curves', methods=['POST'])
def upload_curves():
    """
    Upload response curves from CSV file.
    
    Expected CSV columns:
    market, brand, sub_brand, channel, k, s, max_response, adstock_rate, volume_coefficient, brand_lift_coefficient
    """
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        import csv
        import io
        
        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        
        imported = 0
        errors = []
        
        for row in reader:
            try:
                curve = {
                    'market': row['market'],
                    'brand': row['brand'],
                    'sub_brand': row.get('sub_brand', 'All'),
                    'channel': row['channel'],
                    'k': float(row['k']),
                    's': float(row['s']),
                    'max_response': float(row['max_response']),
                    'adstock_rate': float(row.get('adstock_rate', 0.2)),
                    'volume_coefficient': float(row.get('volume_coefficient', 1.0)),
                    'brand_lift_coefficient': float(row.get('brand_lift_coefficient', 0.1)),
                    'source': 'upload'
                }
                db.save_curve(curve)
                imported += 1
            except Exception as e:
                errors.append(f"Row {imported + 1}: {str(e)}")
        
        return jsonify({
            "success": True, 
            "imported": imported,
            "errors": errors
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/upload/cpms', methods=['POST'])
def upload_cpms():
    """
    Upload CPM data from CSV file.
    
    Expected CSV columns:
    market, brand, channel, week_start, cpm, min_spend, max_spend
    """
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected"}), 400
        
        import csv
        import io
        
        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        
        imported = 0
        errors = []
        
        for row in reader:
            try:
                cpm = {
                    'market': row['market'],
                    'brand': row['brand'],
                    'sub_brand': row.get('sub_brand', 'All'),
                    'channel': row['channel'],
                    'week_start': row['week_start'],
                    'cpm': float(row['cpm']),
                    'min_spend': float(row.get('min_spend', 0)),
                    'max_spend': float(row.get('max_spend', 0)) or None
                }
                db.save_cpm(cpm)
                imported += 1
            except Exception as e:
                errors.append(f"Row {imported + 1}: {str(e)}")
        
        return jsonify({
            "success": True, 
            "imported": imported,
            "errors": errors
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# NLOPT OPTIMIZER
# ==========================================

@app.route('/api/optimize/nlopt', methods=['POST'])
def run_nlopt_optimization():
    """
    Run NLopt optimization with tanh response curve.
    
    Input:
    - campaigns: List of campaign data with alpha, beta, spend_max, n, W1-W52, C1-C52
    - total_budget: Total budget constraint
    - algorithm: Optimization algorithm (SLSQP, COBYLA, etc.)
    
    Output per campaign:
    - net_spend: Optimized spend allocation
    - profit: Profit from tanh response curve
    - roi: Return on investment (profit / spend)
    """
    try:
        from nlopt_optimizer import optimize_budget
        
        data = request.json
        campaigns = data.get('campaigns', [])
        total_budget = float(data.get('total_budget', 1000000))
        algorithm = data.get('algorithm', 'SLSQP')
        
        if not campaigns:
            return jsonify({"success": False, "error": "No campaign data provided"}), 400
        
        # Run optimization
        results = optimize_budget(campaigns, total_budget, algorithm)
        
        return jsonify({
            "success": True,
            "data": results
        })
        
    except ImportError as e:
        return jsonify({
            "success": False, 
            "error": "NLopt optimizer not available. Install nlopt or scipy.",
            "details": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500


@app.route('/api/optimize/nlopt/template', methods=['GET'])
def get_optimization_template():
    """
    Get optimization input template structure.
    """
    template = {
        "dimensions": ["campaignproduct", "campaigntype", "Channel", "publisher", "mediagroup"],
        "parameters": {
            "alpha": "Response curve alpha parameter",
            "beta": "Response curve beta parameter", 
            "spend_max": "Maximum spend limit",
            "n": "Count/frequency parameter"
        },
        "seasonality": {
            "format": "W1, W2, ... W52",
            "description": "Weekly seasonality multipliers (0.5-2.0 range)",
            "default": 1.0
        },
        "consideration": {
            "format": "C1, C2, ... C52",
            "description": "Weekly inclusion flags (1=include, 0=exclude)",
            "default": 1
        },
        "response_curve": {
            "type": "tanh",
            "formula": "profit = tanh(alpha * (spend / spend_max)^beta) * scale * seasonality"
        },
        "output": ["net_spend", "profit", "roi"]
    }
    
    return jsonify({"success": True, "data": template})


# ==========================================
# HEALTH CHECK
# ==========================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


if __name__ == '__main__':
    print("=" * 50)
    print("  BAWT Backend API")
    print("=" * 50)
    print("\n  API running at: http://localhost:5000")
    print("  Health check: http://localhost:5000/api/health")
    print("\n  Press Ctrl+C to stop")
    print("=" * 50)
    app.run(debug=True, port=5000)
