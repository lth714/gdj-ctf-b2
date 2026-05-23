"""Fix get_client_addr() bug: break outer loop after finding valid proxy IP"""
with open('/usr/share/cacti/site/lib/functions.php', 'r') as f:
    content = f.read()

# The bug: after setting $client_addr = $header_ip, only inner loop breaks,
# so REMOTE_ADDR always overwrites. Fix: break out of outer loop too.
old_code = "					$client_addr = $header_ip;\n						cacti_log('DEBUG: Using remote client IP Address found in header (' . $header . '): ' . $client_addr . ' (' . $_SERVER[$header] . ')', false, 'AUTH', POLLER_VERBOSITY_DEBUG);\n						break;"

new_code = "					$client_addr = $header_ip;\n						cacti_log('DEBUG: Using remote client IP Address found in header (' . $header . '): ' . $client_addr . ' (' . $_SERVER[$header] . ')', false, 'AUTH', POLLER_VERBOSITY_DEBUG);\n						break 2;"

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('/usr/share/cacti/site/lib/functions.php', 'w') as f:
        f.write(content)
    print('PATCHED: break -> break 2 in get_client_addr()')
else:
    print('NOT FOUND: searching for pattern...')
    for i, line in enumerate(content.split('\n'), 1):
        if 'client_addr = $header_ip' in line:
            print('  Line {}: {}'.format(i+1, line.strip()))
