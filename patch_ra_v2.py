"""Patch remote_agent.php: add TOP-LEVEL debug right after includes"""
with open('/usr/share/cacti/site/remote_agent.php', 'r') as f:
    content = f.read()

# Add debug right after the last require/include line
marker = "require_once($config['base_path'] . '/lib/utility.php');"
debug_top = "\n" + """file_put_contents('/tmp/cve_top.log', 'REMOTE_AGENT STARTED: action=' . get_nfilter_request_var('action') . ' poller_id=' . get_nfilter_request_var('poller_id') . chr(10), FILE_APPEND);"""

if marker in content:
    content = content.replace(marker, marker + debug_top)
    print('PATCHED: Added top-level debug')
else:
    print('WARN: utility.php marker not found')

# Add debug right before poll_for_data() call
old_call = "poll_for_data();"
new_call = """file_put_contents('/tmp/cve_top.log', 'CALLING poll_for_data' . chr(10), FILE_APPEND);
\t\tpoll_for_data();"""

if old_call in content:
    content = content.replace(old_call, new_call)
    print('PATCHED: Added before poll_for_data call')
else:
    print('WARN: poll_for_data call not found')

# Add debug before switch statement inside poll_for_data
old_switch = "switch ($item['action']) {"
new_switch = """file_put_contents('/tmp/cve_top.log', 'ACTION=' . $item['action'] . ' SNMP=' . POLLER_ACTION_SNMP . ' SCRIPT=' . POLLER_ACTION_SCRIPT . ' SCRIPT_PHP=' . POLLER_ACTION_SCRIPT_PHP . chr(10), FILE_APPEND);
\t\t\t\t\tswitch ($item['action']) {"""

if old_switch in content:
    content = content.replace(old_switch, new_switch)
    print('PATCHED: Added pre-switch debug')
else:
    print('WARN: switch statement not found')

# Add debug before proc_open
old_proc = "$cactiphp = proc_open(read_config_option('path_php_binary') . ' -q ' . $config['base_path'] . '/script_server.php realtime ' . $poller_id, $cactides, $pipes);"
new_proc = """file_put_contents('/tmp/cve_top.log', 'PROC_OPEN poller_id=[' . $poller_id . ']' . chr(10), FILE_APPEND);
\t\t\t\t\t\t\t$cactiphp = proc_open(read_config_option('path_php_binary') . ' -q ' . $config['base_path'] . '/script_server.php realtime ' . $poller_id, $cactides, $pipes);"""

if old_proc in content:
    content = content.replace(old_proc, new_proc)
    print('PATCHED: Added proc_open debug')
else:
    print('WARN: proc_open line not found')

with open('/usr/share/cacti/site/remote_agent.php', 'w') as f:
    f.write(content)
print('DONE - file written')
