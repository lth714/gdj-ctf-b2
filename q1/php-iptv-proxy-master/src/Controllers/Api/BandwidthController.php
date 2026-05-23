<?php
namespace App\Controllers\Api;

use App\Core\Controller;
use App\Core\Database;
use App\Core\Redis;
use App\Core\Response;

class BandwidthController extends Controller
{
    private $db;
    private $redis;
    
    public function __construct()
    {
        parent::__construct();
        $this->db = Database::getInstance()->getConnection();
        $this->redis = new Redis();
    }
    
    public function getAll()
    {
        try {
            $stmt = $this->db->query("SELECT id, name, upload_bandwidth, download_bandwidth FROM channels");
            $channels = $stmt->fetchAll(\PDO::FETCH_ASSOC);
            
            $data = [];
            $totalUpload = 0;
            $totalDownload = 0;
            
            foreach ($channels as $channel) {
                $realtime = $this->redis->hGetAll("channel:{$channel['id']}:bandwidth");
                
                $currentUpload = floatval($realtime['upload'] ?? 0);
                $currentDownload = floatval($realtime['download'] ?? 0);
                
                $totalUpload += $currentUpload;
                $totalDownload += $currentDownload;
                
                $data[] = [
                    'id' => $channel['id'],
                    'name' => $channel['name'],
                    'bandwidth' => [
                        'current' => [
                            'upload' => $currentUpload,
                            'download' => $currentDownload
                        ]
                    ]
                ];
            }
            
            Response::json([
                'success' => true,
                'data' => [
                    'total' => [
                        'upload' => $totalUpload,
                        'download' => $totalDownload
                    ],
                    'channels' => $data
                ]
            ]);
        } catch (\Exception $e) {
            Response::error('获取带宽数据失败: ' . $e->getMessage());
        }
    }
    
    public function getOne($id)
    {
        try {
            $stmt = $this->db->prepare("SELECT id, name, upload_bandwidth, download_bandwidth FROM channels WHERE id = ?");
            $stmt->execute([$id]);
            $channel = $stmt->fetch(\PDO::FETCH_ASSOC);
            
            if (!$channel) {
                Response::error('频道不存在', 404);
                return;
            }
            
            $realtime = $this->redis->hGetAll("channel:{$channel['id']}:bandwidth");
            
            Response::json([
                'success' => true,
                'data' => [
                    'id' => $channel['id'],
                    'name' => $channel['name'],
                    'bandwidth' => [
                        'current' => [
                            'upload' => floatval($realtime['upload'] ?? 0),
                            'download' => floatval($realtime['download'] ?? 0)
                        ]
                    ]
                ]
            ]);
        } catch (\Exception $e) {
            Response::error('获取带宽数据失败: ' . $e->getMessage());
        }
    }
} 