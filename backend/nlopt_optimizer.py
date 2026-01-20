"""
NLopt Optimizer for BAWT
Uses nlopt library for nonlinear optimization with tanh response curve.
Reference: https://nlopt.readthedocs.io/en/latest/

Response curve: profit = tanh(alpha * (spend / spend_max)^beta) * scale_factor
Output: net_spends, profit, ROI
"""

import numpy as np
from typing import Dict, List, Any, Optional

# Try to import nlopt, fall back to scipy if not available
try:
    import nlopt
    HAS_NLOPT = True
except ImportError:
    HAS_NLOPT = False
    from scipy.optimize import minimize


class TanhResponseCurve:
    """
    Tanh-based response curve model.
    profit = tanh(alpha * (spend / spend_max)^beta) * scale_factor * seasonality
    """
    
    @staticmethod
    def calculate_profit(spend: float, alpha: float, beta: float, 
                        spend_max: float, seasonality: float = 1.0,
                        scale_factor: float = 1000000) -> float:
        """Calculate profit using tanh response curve."""
        if spend <= 0 or spend_max <= 0:
            return 0.0
        
        normalized_spend = spend / spend_max
        profit = np.tanh(alpha * (normalized_spend ** beta)) * scale_factor * seasonality
        return profit
    
    @staticmethod
    def calculate_marginal_roi(spend: float, alpha: float, beta: float,
                               spend_max: float, seasonality: float = 1.0,
                               scale_factor: float = 1000000, delta: float = 1.0) -> float:
        """Calculate marginal ROI (derivative of profit w.r.t. spend)."""
        if spend <= 0:
            spend = delta
        
        profit_at_spend = TanhResponseCurve.calculate_profit(
            spend, alpha, beta, spend_max, seasonality, scale_factor)
        profit_at_spend_plus = TanhResponseCurve.calculate_profit(
            spend + delta, alpha, beta, spend_max, seasonality, scale_factor)
        
        marginal_profit = profit_at_spend_plus - profit_at_spend
        return marginal_profit / delta if delta > 0 else 0.0
    
    @staticmethod
    def calculate_gradient(spend: float, alpha: float, beta: float,
                           spend_max: float, seasonality: float = 1.0,
                           scale_factor: float = 1000000) -> float:
        """Calculate analytical gradient of profit w.r.t. spend."""
        if spend <= 0 or spend_max <= 0:
            return 0.0
        
        normalized_spend = spend / spend_max
        tanh_input = alpha * (normalized_spend ** beta)
        
        # Derivative of tanh(x) is sech²(x) = 1 - tanh²(x)
        sech_squared = 1 - np.tanh(tanh_input) ** 2
        
        # Chain rule: d/dspend = d/d(normalized) * d(normalized)/dspend
        grad = scale_factor * seasonality * sech_squared * alpha * beta * \
               (normalized_spend ** (beta - 1)) / spend_max
        
        return grad


class NLoptOptimizer:
    """
    NLopt-based budget optimizer.
    Maximizes total profit subject to budget and channel constraints.
    """
    
    def __init__(self, campaigns: List[Dict[str, Any]], 
                 total_budget: float,
                 algorithm: str = 'SLSQP'):
        """
        Initialize optimizer.
        
        Args:
            campaigns: List of campaign dicts with keys:
                - campaignproduct, campaigntype, Channel, publisher, mediagroup
                - alpha, beta, spend_max, n
                - W1-W52 (seasonality factors)
                - C1-C52 (consideration flags, 0/1)
            total_budget: Total budget constraint
            algorithm: Optimization algorithm (SLSQP, COBYLA, etc.)
        """
        self.campaigns = campaigns
        self.total_budget = total_budget
        self.algorithm = algorithm
        self.n_campaigns = len(campaigns)
        
        # Extract parameters
        self._extract_parameters()
    
    def _extract_parameters(self):
        """Extract optimization parameters from campaign data."""
        self.alphas = []
        self.betas = []
        self.spend_maxs = []
        self.spend_mins = []  # Minimum spend per campaign
        self.seasonalities = []  # Average seasonality across considered weeks
        self.names = []
        
        for camp in self.campaigns:
            self.alphas.append(float(camp.get('alpha', 1.0)))
            self.betas.append(float(camp.get('beta', 1.0)))
            self.spend_maxs.append(float(camp.get('spend_max', 100000)))
            self.spend_mins.append(float(camp.get('spend_min', 0)))
            self.names.append(camp.get('campaignproduct', 'Unknown'))
            
            # Calculate average seasonality for considered weeks
            total_seasonality = 0
            weeks_considered = 0
            for i in range(1, 53):
                consider = camp.get(f'C{i}', 1)
                if consider == 1 or consider == '1':
                    seasonality = float(camp.get(f'W{i}', 1.0))
                    total_seasonality += seasonality
                    weeks_considered += 1
            
            avg_seasonality = total_seasonality / weeks_considered if weeks_considered > 0 else 1.0
            self.seasonalities.append(avg_seasonality)
    
    def objective_function(self, spends: np.ndarray) -> float:
        """
        Objective function: Negative total profit (we minimize, so negative for max).
        """
        total_profit = 0.0
        for i, spend in enumerate(spends):
            profit = TanhResponseCurve.calculate_profit(
                spend,
                self.alphas[i],
                self.betas[i],
                self.spend_maxs[i],
                self.seasonalities[i]
            )
            total_profit += profit
        
        return -total_profit  # Negative for minimization
    
    def gradient_function(self, spends: np.ndarray) -> np.ndarray:
        """Gradient of objective function."""
        gradients = np.zeros(self.n_campaigns)
        for i, spend in enumerate(spends):
            grad = TanhResponseCurve.calculate_gradient(
                spend,
                self.alphas[i],
                self.betas[i],
                self.spend_maxs[i],
                self.seasonalities[i]
            )
            gradients[i] = -grad  # Negative for minimization
        
        return gradients
    
    def budget_constraint(self, spends: np.ndarray) -> float:
        """Budget constraint: sum(spends) - total_budget <= 0"""
        return np.sum(spends) - self.total_budget
    
    def optimize_nlopt(self) -> Dict[str, Any]:
        """Run optimization using NLopt library."""
        if not HAS_NLOPT:
            return self.optimize_scipy()
        
        # Choose algorithm
        alg_map = {
            'SLSQP': nlopt.LD_SLSQP,
            'COBYLA': nlopt.LN_COBYLA,
            'MMA': nlopt.LD_MMA,
            'AUGLAG': nlopt.LD_AUGLAG,
            'BOBYQA': nlopt.LN_BOBYQA,
        }
        
        alg = alg_map.get(self.algorithm, nlopt.LD_SLSQP)
        opt = nlopt.opt(alg, self.n_campaigns)
        
        # Set bounds
        lower_bounds = np.array(self.spend_mins)
        upper_bounds = np.array(self.spend_maxs)
        opt.set_lower_bounds(lower_bounds)
        opt.set_upper_bounds(upper_bounds)
        
        # Set objective
        def nlopt_objective(x, grad):
            if grad.size > 0:
                grad[:] = self.gradient_function(x)
            return self.objective_function(x)
        
        opt.set_min_objective(nlopt_objective)
        
        # Budget constraint (inequality: g(x) <= 0)
        def nlopt_constraint(x, grad):
            if grad.size > 0:
                grad[:] = np.ones(self.n_campaigns)
            return self.budget_constraint(x)
        
        opt.add_inequality_constraint(nlopt_constraint, 1e-8)
        
        # Termination conditions
        opt.set_xtol_rel(1e-6)
        opt.set_ftol_rel(1e-6)
        opt.set_maxeval(1000)
        
        # Initial guess: equal allocation
        x0 = np.full(self.n_campaigns, self.total_budget / self.n_campaigns)
        x0 = np.clip(x0, lower_bounds, upper_bounds)
        
        # Run optimization
        try:
            optimal_spends = opt.optimize(x0)
            min_val = opt.last_optimum_value()
            
            return self._format_results(optimal_spends, -min_val, 'NLopt-' + self.algorithm)
        except Exception as e:
            # Fall back to equal allocation
            return self._format_results(x0, -self.objective_function(x0), 'Fallback')
    
    def optimize_scipy(self) -> Dict[str, Any]:
        """Fallback optimization using scipy."""
        from scipy.optimize import minimize, Bounds, LinearConstraint
        
        # Bounds
        bounds = Bounds(
            np.array(self.spend_mins),
            np.array(self.spend_maxs)
        )
        
        # Budget constraint
        budget_constraint = LinearConstraint(
            np.ones((1, self.n_campaigns)),
            -np.inf,
            self.total_budget
        )
        
        # Initial guess
        x0 = np.full(self.n_campaigns, self.total_budget / self.n_campaigns)
        x0 = np.clip(x0, self.spend_mins, self.spend_maxs)
        
        # Optimize
        result = minimize(
            self.objective_function,
            x0,
            method='SLSQP',
            jac=self.gradient_function,
            bounds=bounds,
            constraints={'type': 'ineq', 'fun': lambda x: self.total_budget - np.sum(x)}
        )
        
        return self._format_results(result.x, -result.fun, 'SciPy-SLSQP')
    
    def _format_results(self, optimal_spends: np.ndarray, 
                        total_profit: float, 
                        solver: str) -> Dict[str, Any]:
        """Format optimization results."""
        results = {
            'solver': solver,
            'total_budget': self.total_budget,
            'total_spend': float(np.sum(optimal_spends)),
            'total_profit': float(total_profit),
            'average_roi': float(total_profit / np.sum(optimal_spends)) if np.sum(optimal_spends) > 0 else 0,
            'campaigns': []
        }
        
        for i in range(self.n_campaigns):
            spend = float(optimal_spends[i])
            profit = TanhResponseCurve.calculate_profit(
                spend,
                self.alphas[i],
                self.betas[i],
                self.spend_maxs[i],
                self.seasonalities[i]
            )
            roi = profit / spend if spend > 0 else 0
            
            results['campaigns'].append({
                'name': self.names[i],
                'net_spend': round(spend, 2),
                'profit': round(profit, 2),
                'roi': round(roi, 4),
                'spend_share': round(spend / self.total_budget * 100, 1) if self.total_budget > 0 else 0,
                'profit_share': round(profit / total_profit * 100, 1) if total_profit > 0 else 0,
            })
        
        return results
    
    def optimize(self) -> Dict[str, Any]:
        """Run optimization with best available method."""
        if HAS_NLOPT:
            return self.optimize_nlopt()
        else:
            return self.optimize_scipy()


def optimize_budget(campaigns: List[Dict[str, Any]], 
                    total_budget: float,
                    algorithm: str = 'SLSQP') -> Dict[str, Any]:
    """
    Main entry point for budget optimization.
    
    Args:
        campaigns: Campaign data with parameters
        total_budget: Total budget to allocate
        algorithm: Optimization algorithm
    
    Returns:
        Optimization results with net_spends, profit, ROI
    """
    optimizer = NLoptOptimizer(campaigns, total_budget, algorithm)
    return optimizer.optimize()


# Example usage and testing
if __name__ == '__main__':
    # Sample campaign data
    sample_campaigns = [
        {
            'campaignproduct': 'Campaign_01',
            'campaigntype': 'conversion',
            'Channel': 'Digital',
            'publisher': 'Meta',
            'mediagroup': 'Social',
            'alpha': 2.5,
            'beta': 0.7,
            'spend_max': 100000,
            'spend_min': 10000,
            'W1': 1.0, 'W2': 1.2, 'W3': 1.5, 'W4': 1.0,
            'C1': 1, 'C2': 1, 'C3': 1, 'C4': 1,
        },
        {
            'campaignproduct': 'Campaign_02',
            'campaigntype': 'conversion',
            'Channel': 'Digital',
            'publisher': 'Google',
            'mediagroup': 'Search',
            'alpha': 3.0,
            'beta': 0.6,
            'spend_max': 80000,
            'spend_min': 5000,
            'W1': 0.8, 'W2': 1.0, 'W3': 1.2, 'W4': 1.5,
            'C1': 1, 'C2': 1, 'C3': 1, 'C4': 1,
        },
        {
            'campaignproduct': 'Campaign_03',
            'campaigntype': 'awareness',
            'Channel': 'TV',
            'publisher': 'ITV',
            'mediagroup': 'Video',
            'alpha': 1.8,
            'beta': 0.8,
            'spend_max': 200000,
            'spend_min': 20000,
            'W1': 1.5, 'W2': 1.2, 'W3': 0.8, 'W4': 2.0,
            'C1': 1, 'C2': 1, 'C3': 0, 'C4': 1,  # Week 3 excluded
        },
    ]
    
    # Run optimization
    results = optimize_budget(sample_campaigns, total_budget=250000)
    
    print("=" * 60)
    print("OPTIMIZATION RESULTS")
    print("=" * 60)
    print(f"Solver: {results['solver']}")
    print(f"Total Budget: €{results['total_budget']:,.0f}")
    print(f"Total Spend: €{results['total_spend']:,.0f}")
    print(f"Total Profit: €{results['total_profit']:,.0f}")
    print(f"Average ROI: {results['average_roi']:.2f}")
    print()
    print("Campaign Allocations:")
    print("-" * 60)
    for camp in results['campaigns']:
        print(f"  {camp['name']}")
        print(f"    Net Spend: €{camp['net_spend']:,.0f} ({camp['spend_share']:.1f}%)")
        print(f"    Profit:    €{camp['profit']:,.0f} ({camp['profit_share']:.1f}%)")
        print(f"    ROI:       {camp['roi']:.2f}")
