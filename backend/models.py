"""
BAWT Backend - MMM Models
Media Mix Modeling calculations: response curves, saturation, adstock
"""

import math
from typing import List, Dict, Any


class ResponseCurve:
    """Response curve calculations for MMM."""
    
    @staticmethod
    def hill(x: float, k: float, s: float) -> float:
        """
        Hill saturation function.
        
        Args:
            x: Input spend
            k: Half-saturation constant (spend at 50% max response)
            s: Shape parameter (steepness)
        
        Returns:
            Response value (0-1 scaled)
        """
        if x <= 0:
            return 0
        return (x ** s) / (k ** s + x ** s)
    
    @staticmethod
    def adstock(values: List[float], decay: float) -> List[float]:
        """
        Apply adstock transformation.
        
        Args:
            values: List of spend values over time
            decay: Decay rate (0-1, higher = more carryover)
        
        Returns:
            Adstocked values
        """
        if not values:
            return []
        
        result = [values[0]]
        for i in range(1, len(values)):
            result.append(values[i] + decay * result[i-1])
        return result
    
    @staticmethod
    def decay_to_halflife(decay: float) -> float:
        """Convert decay rate to half-life in periods."""
        if decay <= 0 or decay >= 1:
            return 0
        return math.log(0.5) / math.log(decay)


class MMModel:
    """Main MMM model class."""
    
    @staticmethod
    def hill_saturation(spend: float, k: float, s: float) -> float:
        """Calculate saturated response using Hill function."""
        return ResponseCurve.hill(spend, 1/k, s) * spend * 0.1
    
    @staticmethod
    def marginal_roi(spend: float, k: float, s: float, delta: float = 1000) -> float:
        """
        Calculate marginal ROI at current spend level.
        
        Args:
            spend: Current spend level
            k: Saturation parameter
            s: Shape parameter
            delta: Incremental spend for marginal calculation
        
        Returns:
            Marginal ROI percentage
        """
        if spend <= 0:
            return 0
        
        response_current = MMModel.hill_saturation(spend, k, s)
        response_plus = MMModel.hill_saturation(spend + delta, k, s)
        
        incremental_response = response_plus - response_current
        marginal_value = incremental_response * 30  # Value per unit
        
        return ((marginal_value - delta) / delta) * 100 if delta > 0 else 0
    
    @staticmethod
    def optimize_allocation(
        curves: List[Dict[str, Any]],
        total_budget: float,
        constraints: List[Dict[str, Any]],
        objective: str = 'value'
    ) -> List[Dict[str, Any]]:
        """
        Simple gradient-based budget allocation.
        
        In production, replace with scipy.optimize.minimize
        with proper constraint handling.
        """
        results = []
        n_curves = len(curves)
        
        # Start with equal allocation
        base_allocation = total_budget / n_curves
        
        # Apply constraints and calculate optimal allocation
        for curve in curves:
            params = curve['parameters']
            default_spend = curve['default_spend']
            
            # Simple heuristic: allocate based on marginal ROI
            marginal = MMModel.marginal_roi(default_spend, params['saturation_k'], params['saturation_s'])
            
            # Adjust allocation based on marginal ROI
            if marginal > 100:
                optimized_spend = default_spend * 1.1  # Increase
            elif marginal < 50:
                optimized_spend = default_spend * 0.9  # Decrease
            else:
                optimized_spend = default_spend
            
            # Apply min/max constraints
            for constraint in constraints:
                if constraint.get('curve_id') == curve['id']:
                    if constraint['type'] == 'min':
                        optimized_spend = max(optimized_spend, constraint['value'])
                    elif constraint['type'] == 'max':
                        optimized_spend = min(optimized_spend, constraint['value'])
                    elif constraint['type'] == 'fixed':
                        optimized_spend = constraint['value']
            
            # Calculate optimized KPIs
            response = MMModel.hill_saturation(optimized_spend, params['saturation_k'], params['saturation_s'])
            volume = response * 0.1
            value = volume * 30
            roi = ((value - optimized_spend) / optimized_spend) * 100 if optimized_spend > 0 else 0
            
            results.append({
                "curve_id": curve['id'],
                "name": curve['name'],
                "color": curve['color'],
                "original_spend": default_spend,
                "optimized_spend": round(optimized_spend, 0),
                "spend_change": round((optimized_spend - default_spend) / default_spend * 100, 1),
                "original_volume": round(MMModel.hill_saturation(default_spend, params['saturation_k'], params['saturation_s']) * 0.1, 0),
                "optimized_volume": round(volume, 0),
                "original_value": round(MMModel.hill_saturation(default_spend, params['saturation_k'], params['saturation_s']) * 0.1 * 30, 0),
                "optimized_value": round(value, 0),
                "optimized_roi": round(roi, 1),
                "marginal_roi": round(MMModel.marginal_roi(optimized_spend, params['saturation_k'], params['saturation_s']), 1)
            })
        
        return results


class Validator:
    """Data validation utilities."""
    
    @staticmethod
    def validate_spend_plan(plan: Dict[str, Any], curves: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate a spend plan against curve definitions."""
        errors = []
        warnings = []
        
        curve_ids = {c['id'] for c in curves}
        
        for item in plan.get('items', []):
            curve_id = item.get('curve_id')
            spend = item.get('spend', 0)
            
            # Check curve exists
            if curve_id not in curve_ids:
                errors.append(f"Unknown curve: {curve_id}")
                continue
            
            # Check spend is valid
            if not isinstance(spend, (int, float)):
                errors.append(f"Invalid spend type for {curve_id}")
                continue
            
            if spend < 0:
                errors.append(f"Negative spend for {curve_id}")
            
            # Check against observed ranges
            curve = next(c for c in curves if c['id'] == curve_id)
            obs_range = curve['observed_range']
            
            if spend < obs_range['min'] * 0.5:
                warnings.append(f"{curve_id}: spend below 50% of observed minimum")
            elif spend > obs_range['max'] * 1.5:
                warnings.append(f"{curve_id}: spend above 150% of observed maximum")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
