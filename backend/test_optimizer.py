"""Test script for MMM optimizer"""
import sys
sys.path.insert(0, '.')
from database import Database
from optimizer import optimizer

db = Database()
curves = db.get_curves('US', 'Brand A')
print(f'Loaded {len(curves)} curves')

# Test optimization
current = {c['id']: 200000 for c in curves}  # 200K each
result = optimizer.optimize(curves, current, 1000000)  # 1M total

print('\nOptimization Results:')
print(f"Total Budget: ${result['summary']['total_budget']:,.0f}")
print(f"Response Lift: {result['summary']['response_lift_pct']:.1f}%")
print(f"Iterations: {result['summary']['iterations']}")
print('\nAllocations:')
for alloc in result['allocations'].values():
    ch = alloc['channel']
    cur = alloc['current_spend']
    opt = alloc['optimized_spend']
    pct = alloc['change_pct']
    print(f"  {ch}: ${cur:,.0f} -> ${opt:,.0f} ({pct:+.1f}%)")
