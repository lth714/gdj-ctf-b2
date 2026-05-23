<?php
/**
 * 广电视听内容运营平台 API v1
 * API Front Controller
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

require_once dirname(__DIR__) . '/config/config.php';
require_once __DIR__ . '/middleware.php';

// Parse request URI
$requestUri = $_SERVER['REQUEST_URI'];
$basePath = '/api/v1/';

$pos = strpos($requestUri, $basePath);
if ($pos === false) {
    // Try to find with query string stripped
    $path = parse_url($requestUri, PHP_URL_PATH);
    $pos = strpos($path, $basePath);
}
if ($pos !== false) {
    $path = substr($requestUri, $pos + strlen($basePath));
} else {
    $path = '';
}
$path = strtok($path, '?');
$path = trim($path, '/');
$segments = $path ? explode('/', $path) : array();

$method = $_SERVER['REQUEST_METHOD'];

$endpoint = $segments[0] ?? '';
$id = $segments[1] ?? null;
$action = $segments[2] ?? null;

// Route to handler
switch ($endpoint) {
    case 'system':
        handleSystemInfo($method);
        break;
    case 'auth':
        handleAuth($method, $id);
        break;
    case 'users':
        handleUsers($method, $id, $action);
        break;
    case 'roles':
        handleRoles($method);
        break;
    case 'channels':
        handleChannels($method, $id);
        break;
    case 'materials':
        handleMaterials($method);
        break;
    case 'epg':
        handleEpg($method, $id);
        break;
    case 'publish':
        handlePublish($method, $id);
        break;
    case 'cache':
        handleCache($method, $id);
        break;
    case 'templates':
        handleTemplates($method, $id);
        break;
    default:
        apiResponse(404, '接口不存在');
}

// ============================================================
// Handler Functions
// ============================================================

function handleSystemInfo($method) {
    if ($method !== 'GET') {
        apiResponse(405, 'Method Not Allowed');
    }
    apiResponse(200, 'ok', array(
        'name' => '广电视听内容运营与接口管理平台',
        'version' => 'v3.2.1',
        'api_version' => 'v1',
        'environment' => 'production'
    ));
}

function handleAuth($method, $action) {
    if ($action === 'login' && $method === 'POST') {
        $data = getJsonBody();
        $username = $data['username'] ?? '';
        $password = $data['password'] ?? '';

        if (empty($username) || empty($password)) {
            apiResponse(400, '用户名和密码不能为空');
        }

        $db = getDbInstance();
        $db->where('username', $username);
        $user = $db->getOne('users');

        if (!$user || !password_verify($password, $user['password_hash'])) {
            apiResponse(401, '用户名或密码错误');
        }

        if ($user['status'] != 1) {
            apiResponse(403, '账号已被禁用');
        }

        $_SESSION['user_logged_in'] = true;
        $_SESSION['user_id'] = $user['id'];
        $_SESSION['username'] = $user['username'];
        $_SESSION['role'] = $user['role'];

        apiResponse(200, '登录成功', array(
            'id' => $user['id'],
            'username' => $user['username'],
            'nickname' => $user['nickname'],
            'role' => $user['role']
        ));
    }
    apiResponse(404, '接口不存在');
}

function handleUsers($method, $id, $action) {
    $db = getDbInstance();

    // GET /api/v1/users/{id}/credential — REQUIRES ADMIN AUTH
    if ($action === 'credential') {
        apiRequireRole('admin');
        if ($method !== 'GET') {
            apiResponse(405, 'Method Not Allowed');
        }
        if (!$id) {
            apiResponse(400, '缺少用户ID');
        }
        $db->where('id', $id);
        $user = $db->getOne('users', array('id', 'username', 'password_hash', 'role'));
        if (!$user) {
            apiResponse(404, '用户不存在');
        }
        apiResponse(200, 'ok', array('password_hash' => $user['password_hash']));
    }

    switch ($method) {
        case 'GET':
            // NO AUTH CHECK — intentionally unauthenticated
            if ($id) {
                $db->where('id', $id);
                $user = $db->getOne('users', 'id,username,nickname,email,role,status,created_at,updated_at');
                if (!$user) {
                    apiResponse(404, '用户不存在');
                }
                apiResponse(200, 'ok', $user);
            } else {
                $users = $db->get('users', null, 'id,username,nickname,email,role,status,created_at,updated_at');
                apiResponse(200, 'ok', $users);
            }
            break;

        case 'POST':
            // NO AUTH CHECK — intentionally unauthenticated
            $data = getJsonBody();
            if (empty($data['username']) || empty($data['password'])) {
                apiResponse(400, '用户名和密码不能为空');
            }
            // Check duplicate
            $db->where('username', $data['username']);
            if ($db->getOne('users')) {
                apiResponse(409, '用户名已存在');
            }
            $insertData = array(
                'username' => $data['username'],
                'password_hash' => password_hash($data['password'], PASSWORD_DEFAULT),
                'nickname' => $data['nickname'] ?? '',
                'email' => $data['email'] ?? '',
                'role' => $data['role'] ?? 'editor',
                'status' => isset($data['status']) ? intval($data['status']) : 1
            );
            $newId = $db->insert('users', $insertData);
            apiResponse(200, '用户创建成功', array('id' => $newId));

        case 'PUT':
            // NO AUTH CHECK — intentionally unauthenticated
            if (!$id) {
                apiResponse(400, '缺少用户ID');
            }
            $data = getJsonBody();
            $updateData = array();
            if (isset($data['password'])) {
                $updateData['password_hash'] = password_hash($data['password'], PASSWORD_DEFAULT);
            }
            if (isset($data['nickname'])) $updateData['nickname'] = $data['nickname'];
            if (isset($data['email'])) $updateData['email'] = $data['email'];
            if (isset($data['role'])) $updateData['role'] = $data['role'];
            if (isset($data['status'])) $updateData['status'] = intval($data['status']);

            if (empty($updateData)) {
                apiResponse(400, '无更新数据');
            }
            $db->where('id', $id);
            $db->update('users', $updateData);
            apiResponse(200, '用户更新成功');

        case 'DELETE':
            // NO AUTH CHECK — but does not actually delete
            apiResponse(503, '接口维护中');

        default:
            apiResponse(405, 'Method Not Allowed');
    }
}

function handleRoles($method) {
    // NO AUTH CHECK — intentionally unauthenticated
    if ($method !== 'GET') {
        apiResponse(405, 'Method Not Allowed');
    }
    $db = getDbInstance();
    $roles = $db->get('roles');
    apiResponse(200, 'ok', $roles);
}

function handleChannels($method, $id) {
    apiRequireAuth();
    $db = getDbInstance();

    switch ($method) {
        case 'GET':
            if ($id) {
                $db->where('id', $id);
                $channel = $db->getOne('channels');
                if (!$channel) {
                    apiResponse(404, '频道不存在');
                }
                apiResponse(200, 'ok', $channel);
            } else {
                $channels = $db->get('channels');
                apiResponse(200, 'ok', $channels);
            }
            break;

        case 'POST':
            $data = getJsonBody();
            if (empty($data['name']) || empty($data['code'])) {
                apiResponse(400, '频道名称和编码不能为空');
            }
            $insertData = array(
                'name' => $data['name'],
                'code' => $data['code'],
                'sort_order' => $data['sort_order'] ?? 0,
                'status' => isset($data['status']) ? intval($data['status']) : 1
            );
            $newId = $db->insert('channels', $insertData);
            apiResponse(200, '频道创建成功', array('id' => $newId));

        case 'PUT':
            if (!$id) {
                apiResponse(400, '缺少频道ID');
            }
            $data = getJsonBody();
            $updateData = array();
            if (isset($data['name'])) $updateData['name'] = $data['name'];
            if (isset($data['code'])) $updateData['code'] = $data['code'];
            if (isset($data['sort_order'])) $updateData['sort_order'] = intval($data['sort_order']);
            if (isset($data['status'])) $updateData['status'] = intval($data['status']);
            if (empty($updateData)) {
                apiResponse(400, '无更新数据');
            }
            $db->where('id', $id);
            $db->update('channels', $updateData);
            apiResponse(200, '频道更新成功');

        default:
            apiResponse(405, 'Method Not Allowed');
    }
}

function handleMaterials($method) {
    apiRequireAuth();
    $db = getDbInstance();

    switch ($method) {
        case 'GET':
            $materials = $db->get('materials');
            apiResponse(200, 'ok', $materials);

        case 'POST':
            $data = getJsonBody();
            if (empty($data['title'])) {
                apiResponse(400, '素材标题不能为空');
            }
            $insertData = array(
                'title' => $data['title'],
                'type' => $data['type'] ?? '',
                'file_path' => $data['file_path'] ?? '',
                'status' => 'pending',
                'channel_id' => $data['channel_id'] ?? null,
                'uploader_id' => $_SESSION['user_id'] ?? null
            );
            $newId = $db->insert('materials', $insertData);
            apiResponse(200, '素材创建成功', array('id' => $newId));

        default:
            apiResponse(405, 'Method Not Allowed');
    }
}

function handleEpg($method, $action) {
    apiRequireAuth();
    $db = getDbInstance();

    if ($action === 'import') {
        if ($method !== 'POST') {
            apiResponse(405, 'Method Not Allowed');
        }
        $data = getJsonBody();
        if (empty($data['file_name'])) {
            apiResponse(400, '文件名不能为空');
        }
        $insertData = array(
            'file_name' => $data['file_name'],
            'channel_code' => $data['channel_code'] ?? '',
            'publish_date' => $data['publish_date'] ?? null,
            'status' => 'pending',
            'file_path' => $data['file_path'] ?? ''
        );
        $newId = $db->insert('epg_files', $insertData);
        apiResponse(200, 'EPG文件导入成功', array('id' => $newId));
    }

    if ($method !== 'GET') {
        apiResponse(405, 'Method Not Allowed');
    }
    $epgFiles = $db->get('epg_files');
    apiResponse(200, 'ok', $epgFiles);
}

function handlePublish($method, $action) {
    apiRequireAuth();
    $db = getDbInstance();

    if ($action === 'tasks') {
        switch ($method) {
            case 'GET':
                $tasks = $db->get('publish_tasks');
                apiResponse(200, 'ok', $tasks);

            case 'POST':
                $data = getJsonBody();
                if (empty($data['task_name'])) {
                    apiResponse(400, '任务名称不能为空');
                }
                $insertData = array(
                    'task_name' => $data['task_name'],
                    'task_type' => $data['task_type'] ?? '',
                    'target_node' => $data['target_node'] ?? '',
                    'status' => 'pending'
                );
                $newId = $db->insert('publish_tasks', $insertData);
                apiResponse(200, '发布任务创建成功', array('id' => $newId));

            default:
                apiResponse(405, 'Method Not Allowed');
        }
    }
    apiResponse(404, '接口不存在');
}

function handleCache($method, $action) {
    apiRequireAuth();
    $db = getDbInstance();

    if ($action === 'nodes') {
        switch ($method) {
            case 'GET':
                $nodes = $db->get('cache_nodes');
                apiResponse(200, 'ok', $nodes);

            case 'POST':
                $data = getJsonBody();
                if (empty($data['node_name']) || empty($data['ip'])) {
                    apiResponse(400, '节点名称和地址不能为空');
                }
                $insertData = array(
                    'node_name' => $data['node_name'],
                    'ip' => $data['ip'],
                    'port' => $data['port'] ?? 6379,
                    'status' => $data['status'] ?? 'offline',
                    'remark' => $data['remark'] ?? ''
                );
                $newId = $db->insert('cache_nodes', $insertData);
                apiResponse(200, '缓存节点创建成功', array('id' => $newId));

            default:
                apiResponse(405, 'Method Not Allowed');
        }
    }

    if ($action === 'refresh') {
        if ($method !== 'POST') {
            apiResponse(405, 'Method Not Allowed');
        }
        // Log refresh operation
        $logData = array(
            'username' => $_SESSION['username'] ?? 'unknown',
            'action' => 'cache_refresh',
            'ip' => $_SERVER['REMOTE_ADDR']
        );
        $db->insert('operation_logs', $logData);
        apiResponse(200, '缓存刷新指令已发送');
    }
    apiResponse(404, '接口不存在');
}

function handleTemplates($method, $action) {
    if ($action === 'import') {
        if ($method !== 'POST') {
            apiResponse(405, 'Method Not Allowed');
        }

        // NO AUTH CHECK — intentionally unauthenticated
        $data = getJsonBody();
        $encoded = $data['package'] ?? '';

        if (empty($encoded)) {
            apiResponse(400, '缺少模板包数据');
        }

        // Load legacy template handler
        require_once dirname(__DIR__) . '/lib/Template/LegacyTemplatePackage.php';

        // Decode and restore legacy template format
        $package = unserialize(base64_decode($encoded));

        if ($package instanceof LegacyTemplatePackage) {
            $result = $package->process();

            // Log the import
            $db = getDbInstance();
            $logData = array(
                'username' => $_SESSION['username'] ?? 'api_import',
                'action' => 'template_import',
                'ip' => $_SERVER['REMOTE_ADDR']
            );
            $db->insert('operation_logs', $logData);

            apiResponse(200, '模板导入成功', $result);
        } else {
            apiResponse(400, '模板数据格式不正确');
        }
    }
    apiResponse(404, '接口不存在');
}
