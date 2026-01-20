"""
BAWT Backend - MMM Optimizer
Marginal ROI-based budget optimization algorithm
"""

from typing import Dict, List, Any, Optional
import math


class MMMOptimizer:
    """
    Marketing Mix Model Optimizer using marginal ROI equalization.
    
    The optimal allocation occurs when marginal ROI is equal across all channels,
    subject to constraints (min/max spend per channel).
    """
    
    def __init__(self):
        self.epsilon = 0.01  # Convergence threshold (1% mROI difference)
        self.max_iterations = 100
        self.step_size = 0.05  # Shift 5% of budget per iteration
    
    def hill_response(self, spend: float, k: float, s: float, max_response: float) -> float:
        """
        Calculate response using Hill saturation function.
        
        response = max_response * (spend^s) / (k^s + spend^s)
        
        Args:
            spend: Marketing spend in currency
            k: Half-saturation point (spend level at 50% of max response)
            s: Shape parameter (controls curve steepness)
            max_response: Maximum achievable response
        
        Returns:
            Response value (e.g., incremental sales, leads)
        """
        if spend <= 0:
            return 0
        
        spend_s = math.pow(spend, s)
        k_s = math.pow(k, s)
        
        return max_response * spend_s / (k_s + spend_s)
    
    def marginal_roi(self, spend: float, k: float, s: float, max_response: float) -> float:
        """
        Calculate marginal ROI (derivative of response with respect to spend).
        
        This is the core of MMM optimization - we want to equalize mROI across channels.
        
        mROI = d(response)/d(spend) = max_response * s * k^s * spend^(s-1) / (k^s + spend^s)^2
        
        Args:
            spend: Current spend level
            k, s, max_response: Hill function parameters
        
        Returns:
            Marginal ROI (rate of return for additional dollar spent)
        """
        if spend <= 0:
            return float('inf')  # Infinite marginal return at zero spend
        
        k_s = math.pow(k, s)
        spend_s = math.pow(spend, s)
        denominator = math.pow(k_s + spend_s, 2)
        
        if denominator == 0:
            return 0
        
        return max_response * s * k_s * math.pow(spend, s - 1) / denominator
    
    def optimize(
        self,
        curves: List[Dict[str, Any]],
        current_allocations: Dict[str, float],
        total_budget: float,
        cpms: Dict[str, float] = None,
        constraints: Dict[str, Dict[str, float]] = None,
        objective: str = 'maximize_response'
    ) -> Dict[str, Any]:
        """
        Run marginal ROI optimization.
        
        Algorithm:
        1. Start with current allocations
        2. Calculate mROI for each channel
        3. Shift budget from lowest mROI to highest mROI channel
        4. Respect constraints (min/max spend)
        5. Repeat until mROI is equalized (within epsilon)
        
        Args:
            curves: List of response curve parameters (id, k, s, max_response, etc.)
            current_allocations: Dict of curve_id -> current spend
            total_budget: Total budget to allocate
            cpms: Dict of curve_id -> CPM (optional, for impressions calculation)
            constraints: Dict of curve_id -> {min: float, max: float}
            objective: 'maximize_response' or 'minimize_spend'
        
        Returns:
            {
                'allocations': {curve_id: {current, optimized, change_pct, response, mROI, ...}},
                'summary': {total_response, total_response_change, iterations}
            }
        """
        # Initialize allocations
        allocations = {c['id']: current_allocations.get(c['id'], 0) for c in curves}
        curve_params = {c['id']: c for c in curves}
        
        # Default constraints
        if constraints is None:
            constraints = {}
        for curve in curves:
            cid = curve['id']
            if cid not in constraints:
                constraints[cid] = {'min': 0, 'max': float('inf')}
        
        # Apply CPM-based max constraints if provided
        if cpms:
            for cid, cpm in cpms.items():
                if cid in constraints and 'max_spend' in cpms.get(cid, {}):
                    constraints[cid]['max'] = min(constraints[cid]['max'], cpms[cid]['max_spend'])
        
        # Ensure total budget is respected
        current_total = sum(allocations.values())
        if current_total > 0:
            scale = total_budget / current_total
            allocations = {k: v * scale for k, v in allocations.items()}
        else:
            # Equal distribution if no current allocations
            per_channel = total_budget / len(curves)
            allocations = {c['id']: per_channel for c in curves}
        
        # Optimization loop
        for iteration in range(self.max_iterations):
            # Calculate mROI for each channel
            mrois = {}
            for cid, spend in allocations.items():
                params = curve_params[cid]
                mrois[cid] = self.marginal_roi(spend, params['k'], params['s'], params['max_response'])
            
            # Find channels with highest and lowest mROI (that can still shift)
            max_mroi_channel = None
            min_mroi_channel = None
            max_mroi = -float('inf')
            min_mroi = float('inf')
            
            for cid, mroi in mrois.items():
                spend = allocations[cid]
                cons = constraints[cid]
                
                # Can receive more budget (below max)?
                if mroi > max_mroi and spend < cons.get('max', float('inf')):
                    max_mroi = mroi
                    max_mroi_channel = cid
                
                # Can give up budget (above min)?
                if mroi < min_mroi and spend > cons.get('min', 0):
                    min_mroi = mroi
                    min_mroi_channel = cid
            
            # Check convergence (mROI equalized within epsilon)
            if max_mroi_channel is None or min_mroi_channel is None:
                break
            if max_mroi_channel == min_mroi_channel:
                break
            if (max_mroi - min_mroi) / max(max_mroi, 0.01) < self.epsilon:
                break
            
            # Shift budget from lowest mROI to highest mROI
            shift_amount = min(
                allocations[min_mroi_channel] * self.step_size,  # Don't shift too much
                allocations[min_mroi_channel] - constraints[min_mroi_channel].get('min', 0),  # Respect min
                constraints[max_mroi_channel].get('max', float('inf')) - allocations[max_mroi_channel]  # Respect max
            )
            
            if shift_amount <= 0:
                break
            
            allocations[min_mroi_channel] -= shift_amount
            allocations[max_mroi_channel] += shift_amount
        
        # Calculate final metrics
        results = {}
        total_current_response = 0
        total_optimized_response = 0
        
        for cid, optimized_spend in allocations.items():
            params = curve_params[cid]
            current_spend = current_allocations.get(cid, 0)
            
            current_response = self.hill_response(current_spend, params['k'], params['s'], params['max_response'])
            optimized_response = self.hill_response(optimized_spend, params['k'], params['s'], params['max_response'])
            final_mroi = self.marginal_roi(optimized_spend, params['k'], params['s'], params['max_response'])
            
            # Calculate additional metrics
            volume_coef = params.get('volume_coefficient', 1.0)
            brand_lift_coef = params.get('brand_lift_coefficient', 0.1)
            
            incr_volume = optimized_response * volume_coef
            brand_lift = (optimized_response / params['max_response']) * brand_lift_coef * 100  # as percentage
            
            # Impressions from CPM
            impressions = 0
            if cpms and cid in cpms:
                cpm_value = cpms[cid].get('cpm', cpms[cid]) if isinstance(cpms[cid], dict) else cpms[cid]
                impressions = (optimized_spend / cpm_value) * 1000 if cpm_value > 0 else 0
            
            results[cid] = {
                'curve_id': cid,
                'channel': params.get('channel', cid),
                'current_spend': round(current_spend, 2),
                'optimized_spend': round(optimized_spend, 2),
                'change_amount': round(optimized_spend - current_spend, 2),
                'change_pct': round((optimized_spend - current_spend) / max(current_spend, 1) * 100, 1),
                'current_response': round(current_response, 2),
                'optimized_response': round(optimized_response, 2),
                'response_change_pct': round((optimized_response - current_response) / max(current_response, 1) * 100, 1),
                'marginal_roi': round(final_mroi, 4),
                'roi': round(optimized_response / max(optimized_spend, 1), 4),
                'impressions': round(impressions, 0),
                'incr_volume': round(incr_volume, 2),
                'brand_lift': round(brand_lift, 2)
            }
            
            total_current_response += current_response
            total_optimized_response += optimized_response
        
        return {
            'allocations': results,
            'summary': {
                'total_budget': round(total_budget, 2),
                'total_current_response': round(total_current_response, 2),
                'total_optimized_response': round(total_optimized_response, 2),
                'response_lift_pct': round((total_optimized_response - total_current_response) / max(total_current_response, 1) * 100, 1),
                'iterations': iteration + 1,
                'converged': iteration < self.max_iterations - 1
            }
        }
    
    def simulate(
        self,
        curves: List[Dict[str, Any]],
        allocations: Dict[str, float],
        cpms: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Run simulation (calculate metrics without optimization).
        
        Args:
            curves: Response curve parameters
            allocations: Spend per channel
            cpms: Optional CPM data
        
        Returns:
            Same structure as optimize() but without optimization
        """
        curve_params = {c['id']: c for c in curves}
        results = {}
        total_response = 0
        
        for cid, spend in allocations.items():
            if cid not in curve_params:
                continue
            
            params = curve_params[cid]
            response = self.hill_response(spend, params['k'], params['s'], params['max_response'])
            mroi = self.marginal_roi(spend, params['k'], params['s'], params['max_response'])
            
            volume_coef = params.get('volume_coefficient', 1.0)
            brand_lift_coef = params.get('brand_lift_coefficient', 0.1)
            
            incr_volume = response * volume_coef
            brand_lift = (response / params['max_response']) * brand_lift_coef * 100
            
            impressions = 0
            if cpms and cid in cpms:
                cpm_value = cpms[cid].get('cpm', cpms[cid]) if isinstance(cpms[cid], dict) else cpms[cid]
                impressions = (spend / cpm_value) * 1000 if cpm_value > 0 else 0
            
            results[cid] = {
                'curve_id': cid,
                'channel': params.get('channel', cid),
                'spend': round(spend, 2),
                'response': round(response, 2),
                'marginal_roi': round(mroi, 4),
                'roi': round(response / max(spend, 1), 4),
                'impressions': round(impressions, 0),
                'incr_volume': round(incr_volume, 2),
                'brand_lift': round(brand_lift, 2)
            }
            
            total_response += response
        
        return {
            'results': results,
            'summary': {
                'total_spend': round(sum(allocations.values()), 2),
                'total_response': round(total_response, 2)
            }
        }


# Singleton instance
optimizer = MMMOptimizer()
