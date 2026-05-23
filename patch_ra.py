"""Patch remote_agent.php to add debug logging"""
import sys

with open('/usr/share/cacti/site/remote_agent.php', 'r') as f:
    content = f.read()

# Debug 1: Before switch - log the action value
old_switch = "switch ($item['action']) {"
new_switch = """file_put_contents('/tmp/cve_debug2.log', 'ACTION=' . $item['action'] . ' CONST=' . POLLER_ACTION_SNMP . ',' . POLLER_ACTION_SCRIPT . ',' . POLLER_ACTION_SCRIPT_PHP . chr(10), FILE_APPEND);
\t\t\t\t\tswitch ($item['action']) {"""

if old_switch in content:
    content = content.replace(old_switch, new_switch)
    print("PATCHED: pre-switch debug")
else:
    print("WARN: switch ($item['action']) not found")
    for i, line in enumerate(content.split('\n'), 1):
        if 'switch' in line and 'action' in line:
            print(f"  Similar line {i}: {line.strip()[:120]}")

# Debug 2: Before proc_open - log command
old_proc = "$cactiphp = proc_open(read_config_option('path_php_binary') . ' -q ' . $config['base_path'] . '/script_server.php realtime ' . $poller_id, $cactides, $pipes);"
new_proc = """file_put_contents('/tmp/cve_debug3.log', 'PROC_OPEN poller_id=[' . $poller_id . ']' . chr(10), FILE_APPEND);
\t\t\t\t\t\t\t$cactiphp = proc_open(read_config_option('path_php_binary') . ' -q ' . $config['base_path'] . '/script_server.php realtime ' . $poller_id, $cactides, $pipes);"""

if old_proc in content:
    content = content.replace(old_proc, new_proc)
    print("PATCHED: proc_open debug")
else:
    print("WARN: proc_open line not found")

with open('/usr/share/cacti/site/remote_agent.php', 'w') as f:
    f.write(content)
print("DONE")
