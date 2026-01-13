import json

# Read the issues file
with open(r'C:\Users\GVMBT\.cursor\projects\d-pvndora\agent-tools\2de5d288-638e-4b57-84ce-cff5b5f04f71.txt', 'r', encoding='utf-8') as f:
    data = json.load(f)

all_issues = data['issues']

# Get reliability-related rules from SonarQube
# Reliability issues are typically bugs that could cause runtime errors
reliability_patterns = [
    'S930',   # Missing arguments
    'S5655',  # Type mismatch  
    'S3776',  # Cognitive complexity (can lead to bugs)
    'S1172',  # Unused parameters (potential bugs)
    'S7503',  # Unused async (potential bugs)
    'S7494',  # Set comprehension (code quality)
    'S4323',  # Union type alias (TypeScript)
    'S5145',  # Log user data (security/reliability)
    'S1481',  # Unused variables
    'S1854',  # Dead stores
    'S1067',  # Expression complexity
    'S3776',  # Cognitive complexity
    'S1128',  # Remove unused import
    'S1192',  # String literals should not be duplicated
]

# Filter reliability issues
reliability_issues = []
for issue in all_issues:
    rule = issue.get('rule', '')
    severity = issue.get('severity', '')
    # Include if matches pattern or is high severity
    if any(pattern in rule for pattern in reliability_patterns) or severity in ['BLOCKER', 'HIGH']:
        reliability_issues.append(issue)

print(f'Total issues in file: {len(all_issues)}')
print(f'Reliability-related issues: {len(reliability_issues)}')

# Group by status and severity
by_status = {}
for issue in reliability_issues:
    status = issue.get('status', 'UNKNOWN')
    if status not in by_status:
        by_status[status] = []
    by_status[status].append(issue)

print('\n=== By Status ===')
for status in ['OPEN', 'CLOSED', 'CONFIRMED', 'RESOLVED', 'REOPENED']:
    if status in by_status:
        print(f'{status}: {len(by_status[status])}')

# Show open issues grouped by severity
open_issues = [i for i in reliability_issues if i.get('status') == 'OPEN']
print(f'\n=== Open Reliability Issues ({len(open_issues)}) ===\n')

by_severity = {}
for issue in open_issues:
    severity = issue.get('severity', 'UNKNOWN')
    if severity not in by_severity:
        by_severity[severity] = []
    by_severity[severity].append(issue)

for severity in ['BLOCKER', 'HIGH', 'MEDIUM', 'LOW', 'MINOR', 'INFO']:
    if severity in by_severity:
        print(f'\n{severity} ({len(by_severity[severity])}):')
        for issue in by_severity[severity]:
            component = issue.get('component', '').split(':')[-1] if ':' in issue.get('component', '') else issue.get('component', '')
            line = issue.get('textRange', {}).get('startLine', 'N/A')
            rule = issue.get('rule', '')
            print(f"  [{issue['key']}] {rule}: {issue['message'][:70]}")
            print(f"      File: {component}:{line}")
