import json

# Read the issues file
with open(r'C:\Users\GVMBT\.cursor\projects\d-pvndora\agent-tools\2de5d288-638e-4b57-84ce-cff5b5f04f71.txt', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Filter for OPEN issues only
open_issues = [i for i in data['issues'] if i.get('status') == 'OPEN']

# Common reliability-related rule patterns
reliability_rules = [
    'S930',  # Missing arguments
    'S5655',  # Type mismatch
    'S3776',  # Cognitive complexity
    'S1172',  # Unused parameters
    'S7503',  # Unused async
    'S7494',  # Set comprehension
    'S4323',  # Union type alias
    'S5145',  # Log user-controlled data
    'S1481',  # Unused variables
    'S1854',  # Dead stores
    'S1067',  # Expression complexity
    'S3776',  # Cognitive complexity
]

# Find reliability issues
reliability_issues = []
for issue in open_issues:
    rule = issue.get('rule', '')
    # Check if it's a reliability-related rule or has high/blocker severity
    if any(rule_pattern in rule for rule_pattern in reliability_rules) or issue.get('severity') in ['BLOCKER', 'HIGH']:
        reliability_issues.append(issue)

print(f'Total open issues: {len(open_issues)}')
print(f'Potential reliability issues: {len(reliability_issues)}')
print('\n=== Reliability Issues ===\n')

# Group by severity
by_severity = {}
for issue in reliability_issues:
    severity = issue.get('severity', 'UNKNOWN')
    if severity not in by_severity:
        by_severity[severity] = []
    by_severity[severity].append(issue)

for severity in ['BLOCKER', 'HIGH', 'MEDIUM', 'LOW', 'MINOR', 'INFO']:
    if severity in by_severity:
        print(f'\n{severity} ({len(by_severity[severity])}):')
        for issue in by_severity[severity][:10]:  # Show first 10
            component = issue.get('component', '').split(':')[-1] if ':' in issue.get('component', '') else issue.get('component', '')
            line = issue.get('textRange', {}).get('startLine', 'N/A')
            print(f"  {issue['key']}: {issue['rule']} - {issue['message'][:80]} - {component}:{line}")
