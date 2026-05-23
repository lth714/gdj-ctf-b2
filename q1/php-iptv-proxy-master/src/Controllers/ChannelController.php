<?php
namespace App\Controllers;

use App\Models\Channel;
use App\Models\ChannelGroup;

class ChannelController
{
    private $channelModel;
    private $groupModel;

    public function __construct()
    {
        $this->channelModel = new Channel();
        $this->groupModel = new ChannelGroup();
    }

    public function index()
    {
        $page = isset($_GET['page']) ? (int)$_GET['page'] : 1;
        $perPage = isset($_GET['per_page']) ? (int)$_GET['per_page'] : 50;
        $groupId = isset($_GET['group_id']) ? $_GET['group_id'] : null;

        // 获取频道列表
        $result = $this->channelModel->getChannelList($page, $perPage, $groupId);
        $channels = $result['channels'];
        
        // 获取分组列表
        $groups = $this->groupModel->getAllGroups();
        
        // 分页信息
        $pagination = [
            'total' => $result['total'],
            'totalPages' => ceil($result['total'] / $perPage),
            'current' => $page
        ];

        require __DIR__ . '/../views/admin/channels/index.php';
    }

    public function checkChannel($id)
    {
        try {
            header('Content-Type: application/json');
            $result = $this->channelModel->checkChannel($id);
            echo json_encode($result);
        } catch (\Exception $e) {
            header('Content-Type: application/json');
            echo json_encode([
                'success' => false,
                'message' => '检查失败：' . $e->getMessage()
            ]);
        }
    }

    public function checkAll()
    {
        // 获取分组参数
        $groupId = isset($_GET['group_id']) ? $_GET['group_id'] : null;
        
        try {
            header('Content-Type: application/json');
            
            // 获取需要检查的频道ID列表
            $query = "SELECT id FROM channels";
            if ($groupId !== null) {
                if ($groupId === '0') {
                    $query .= " WHERE group_id IS NULL";
                } else {
                    $query .= " WHERE group_id = :group_id";
                }
            }
            
            $stmt = $this->channelModel->getConnection()->prepare($query);
            if ($groupId !== null && $groupId !== '0') {
                $stmt->execute([':group_id' => $groupId]);
            } else {
                $stmt->execute();
            }
            
            $ids = array_column($stmt->fetchAll(\PDO::FETCH_ASSOC), 'id');
            
            if (empty($ids)) {
                throw new \Exception('没有找到需要检查的频道');
            }
            
            $taskId = uniqid('check_', true);
            $_SESSION['check_tasks'][$taskId] = [
                'total' => count($ids),
                'completed' => 0,
                'status' => '开始检查...'
            ];

            // 启动异步检查任务
            $this->startCheckTask($taskId, $ids);

            echo json_encode([
                'success' => true,
                'taskId' => $taskId
            ]);
        } catch (\Exception $e) {
            echo json_encode([
                'success' => false,
                'message' => $e->getMessage()
            ]);
        }
    }

    public function checkMultiple()
    {
        try {
            header('Content-Type: application/json');
            
            // 获取POST数据
            $data = json_decode(file_get_contents('php://input'), true);
            $ids = $data['ids'] ?? [];
            
            if (empty($ids)) {
                throw new \Exception('未选择要检查的频道');
            }

            $taskId = uniqid('check_', true);
            $_SESSION['check_tasks'][$taskId] = [
                'total' => count($ids),
                'completed' => 0,
                'status' => '开始检查...'
            ];

            // 启动异步检查任务
            $this->startCheckTask($taskId, $ids);

            echo json_encode([
                'success' => true,
                'taskId' => $taskId
            ]);
        } catch (\Exception $e) {
            echo json_encode([
                'success' => false,
                'message' => $e->getMessage()
            ]);
        }
    }

    private function startCheckTask($taskId, $ids)
    {
        // 这里应该使用队列系统，但为了简单，我们直接在这里处理
        foreach ($ids as $index => $id) {
            try {
                $this->channelModel->checkChannel($id);
                $_SESSION['check_tasks'][$taskId]['completed']++;
                $_SESSION['check_tasks'][$taskId]['status'] = sprintf(
                    "已检查 %d/%d 个频道 (%.1f%%)",
                    $_SESSION['check_tasks'][$taskId]['completed'],
                    $_SESSION['check_tasks'][$taskId]['total'],
                    ($_SESSION['check_tasks'][$taskId]['completed'] / $_SESSION['check_tasks'][$taskId]['total']) * 100
                );
                // 每检查完一个频道就刷新session
                session_write_close();
                session_start();
            } catch (\Exception $e) {
                error_log("Error checking channel {$id}: " . $e->getMessage());
                continue;
            }
        }
    }

    public function checkProgress($taskId)
    {
        session_write_close(); // 释放session锁
        session_start(); // 重新开启session以获取最新数据
        
        if (!isset($_SESSION['check_tasks'][$taskId])) {
            header('Content-Type: application/json');
            echo json_encode(['progress' => 100, 'status' => '任务不存在']);
            return;
        }

        $task = $_SESSION['check_tasks'][$taskId];
        $progress = ($task['total'] > 0) ? round(($task['completed'] / $task['total']) * 100) : 100;

        header('Content-Type: application/json');
        echo json_encode([
            'progress' => $progress,
            'status' => $task['status']
        ]);
    }

    public function deleteChannel($id)
    {
        try {
            header('Content-Type: application/json');
            
            // 开始事务
            $this->channelModel->getConnection()->beginTransaction();
            
            // 获取频道信息用于日志记录
            $channel = $this->channelModel->getChannel($id);
            if (!$channel) {
                throw new \Exception('频道不存在');
            }
            
            // 获取频道所属分组ID
            $query = "SELECT group_id FROM channels WHERE id = :id";
            $stmt = $this->channelModel->getConnection()->prepare($query);
            $stmt->execute([':id' => $id]);
            $groupId = $stmt->fetch(\PDO::FETCH_COLUMN);

            // 删除频道
            $stmt = $this->channelModel->getConnection()->prepare("DELETE FROM channels WHERE id = :id");
            $result = $stmt->execute([':id' => $id]);

            if ($result && $groupId) {
                // 检查分组是否还有其他频道
                $stmt = $this->channelModel->getConnection()->prepare(
                    "SELECT COUNT(*) FROM channels WHERE group_id = :group_id"
                );
                $stmt->execute([':group_id' => $groupId]);
                $count = $stmt->fetchColumn();
                
                if ($count == 0) {
                    // 删除空分组
                    $stmt = $this->channelModel->getConnection()->prepare(
                        "DELETE FROM channel_groups WHERE id = :group_id"
                    );
                    $stmt->execute([':group_id' => $groupId]);
                }
            }
            
            // 提交事务
            $this->channelModel->getConnection()->commit();
            
            echo json_encode([
                'success' => true,
                'message' => '频道已删除'
            ]);
        } catch (\Exception $e) {
            // 回滚事务
            if ($this->channelModel->getConnection()->inTransaction()) {
                $this->channelModel->getConnection()->rollBack();
            }
            
            error_log("Error deleting channel {$id}: " . $e->getMessage());
            echo json_encode([
                'success' => false,
                'message' => '删除频道失败：' . $e->getMessage()
            ]);
        }
    }

    public function deleteMultiple()
    {
        $data = json_decode(file_get_contents('php://input'), true);
        $ids = $data['ids'] ?? [];
        
        $result = $this->channelModel->deleteMultiple($ids);
        header('Content-Type: application/json');
        echo json_encode($result);
    }

    public function deleteAll()
    {
        try {
            header('Content-Type: application/json');
            
            // 开始事务
            $this->channelModel->getConnection()->beginTransaction();
            
            // 删除所有频道
            $stmt = $this->channelModel->getConnection()->prepare("DELETE FROM channels");
            $stmt->execute();
            
            // 删除空分组
            $stmt = $this->channelModel->getConnection()->prepare("DELETE FROM channel_groups WHERE NOT EXISTS (SELECT 1 FROM channels WHERE channels.group_id = channel_groups.id)");
            $stmt->execute();
            
            // 提交事务
            $this->channelModel->getConnection()->commit();
            
            echo json_encode([
                'success' => true,
                'message' => '所有频道已清空'
            ]);
        } catch (\Exception $e) {
            // 回滚事务
            if ($this->channelModel->getConnection()->inTransaction()) {
                $this->channelModel->getConnection()->rollBack();
            }
            
            error_log("Error deleting all channels: " . $e->getMessage());
            echo json_encode([
                'success' => false,
                'message' => '清空频道失败：' . $e->getMessage()
            ]);
        }
    }

    public function add()
    {
        // 获取分组列表供选择
        $groups = $this->groupModel->getAllGroups();
        require __DIR__ . '/../views/admin/channels/add.php';
    }

    public function create()
    {
        $name = $_POST['name'] ?? '';
        $sourceUrl = $_POST['source_url'] ?? '';
        $groupId = $_POST['group_id'] ?? null;
        
        if (empty($name) || empty($sourceUrl)) {
            $_SESSION['flash_message'] = [
                'type' => 'error',
                'message' => '频道名称和源地址不能为空'
            ];
            header('Location: /admin/channels/add');
            exit;
        }

        // 生成代理地址
        $proxyUrl = $this->generateProxyUrl($sourceUrl);
        
        $result = $this->channelModel->createChannel([
            'name' => $name,
            'source_url' => $sourceUrl,
            'proxy_url' => $proxyUrl,
            'group_id' => $groupId ?: null,
            'status' => 'inactive'
        ]);

        if ($result['success']) {
            $_SESSION['flash_message'] = [
                'type' => 'success',
                'message' => '频道添加成功'
            ];
            header('Location: /admin/channels');
        } else {
            $_SESSION['flash_message'] = [
                'type' => 'error',
                'message' => $result['message']
            ];
            header('Location: /admin/channels/add');
        }
        exit;
    }

    private function generateProxyUrl($sourceUrl)
    {
        // 生成唯一的代理路径
        $uniqueId = uniqid('ch_', true);
        // 从源URL中提取文件扩展名
        $extension = pathinfo(parse_url($sourceUrl, PHP_URL_PATH), PATHINFO_EXTENSION);
        if (empty($extension)) {
            $extension = 'm3u8'; // 默认扩展名
        }
        // 返回标准格式的代理地址
        return '/proxy/' . $uniqueId . '/stream.' . $extension;
    }

    public function showImport()
    {
        require __DIR__ . '/../views/admin/channels/import.php';
    }

    public function import()
    {
        try {
            $importType = $_POST['import_type'] ?? 'file';

            if ($importType === 'file') {
                // 处理文件上传
                if (!isset($_FILES['file']) || $_FILES['file']['error'] !== UPLOAD_ERR_OK) {
                    throw new \Exception('文件上传失败');
                }

                $result = $this->channelModel->importFromFile($_FILES['file']);
            } else {
                // 处理在线文件导入
                $url = $_POST['url'] ?? '';
                if (empty($url)) {
                    throw new \Exception('请输入在线文件地址');
                }

                // 获取在线文件内容
                $content = @file_get_contents($url);
                if ($content === false) {
                    throw new \Exception('无法获取在线文件内容');
                }

                // 根据文件扩展名选择导入方法
                $extension = strtolower(pathinfo(parse_url($url, PHP_URL_PATH), PATHINFO_EXTENSION));
                if ($extension === 'txt') {
                    $result = $this->channelModel->importFromTxt($content);
                } else if ($extension === 'm3u' || $extension === 'm3u8') {
                    $result = $this->channelModel->importFromM3u($content);
                } else {
                    throw new \Exception('不支持的文件格式');
                }
            }

            $_SESSION['flash_message'] = [
                'type' => $result['success'] ? 'success' : 'danger',
                'message' => $result['message']
            ];
        } catch (\Exception $e) {
            $_SESSION['flash_message'] = [
                'type' => 'danger',
                'message' => $e->getMessage()
            ];
        }

        header('Location: /admin/channels/import');
        exit;
    }

    public function edit($id)
    {
        // 获取频道信息
        $channel = $this->channelModel->getChannel($id);
        if (!$channel) {
            $_SESSION['flash_message'] = [
                'type' => 'error',
                'message' => '频道不存在'
            ];
            header('Location: /admin/channels');
            exit;
        }

        // 获取分组列表
        $groups = $this->groupModel->getAllGroups();
        require __DIR__ . '/../views/admin/channels/edit.php';
    }

    public function update($id)
    {
        $name = $_POST['name'] ?? '';
        $sourceUrl = $_POST['source_url'] ?? '';
        $groupId = $_POST['group_id'] ?? null;
        
        if (empty($name) || empty($sourceUrl)) {
            $_SESSION['flash_message'] = [
                'type' => 'error',
                'message' => '频道名称和源地址不能为空'
            ];
            header("Location: /admin/channels/edit/{$id}");
            exit;
        }

        $result = $this->channelModel->updateChannel($id, [
            'name' => $name,
            'source_url' => $sourceUrl,
            'group_id' => $groupId
        ]);

        if ($result['success']) {
            $_SESSION['flash_message'] = [
                'type' => 'success',
                'message' => '频道更新成功'
            ];
            header('Location: /admin/channels');
        } else {
            $_SESSION['flash_message'] = [
                'type' => 'error',
                'message' => $result['message']
            ];
            header("Location: /admin/channels/edit/{$id}");
        }
        exit;
    }
}