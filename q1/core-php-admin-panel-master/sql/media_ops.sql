-- ============================================================
-- 广电视听内容运营平台 - 数据库初始化
-- 库名: media_ops
-- ============================================================

CREATE DATABASE IF NOT EXISTS `media_ops`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `media_ops`;

-- 应用数据库用户
CREATE USER IF NOT EXISTS 'media_app'@'localhost' IDENTIFIED BY 'MediaDB@2026!';
GRANT SELECT, INSERT, UPDATE, DELETE ON media_ops.* TO 'media_app'@'localhost';
FLUSH PRIVILEGES;

-- ============================================================
-- 用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `nickname` varchar(50) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `role` varchar(20) NOT NULL DEFAULT 'editor',
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 角色表
-- ============================================================
CREATE TABLE IF NOT EXISTS `roles` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `display_name` varchar(50) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 频道栏目表
-- ============================================================
CREATE TABLE IF NOT EXISTS `channels` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `code` varchar(50) NOT NULL,
  `status` tinyint(1) NOT NULL DEFAULT 1,
  `sort_order` int(11) DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 节目素材表
-- ============================================================
CREATE TABLE IF NOT EXISTS `materials` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `type` varchar(50) DEFAULT NULL,
  `file_path` varchar(500) DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'pending',
  `channel_id` int(11) DEFAULT NULL,
  `uploader_id` int(11) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `channel_id` (`channel_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- EPG文件表
-- ============================================================
CREATE TABLE IF NOT EXISTS `epg_files` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `file_name` varchar(200) NOT NULL,
  `channel_code` varchar(50) DEFAULT NULL,
  `publish_date` date DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'pending',
  `file_path` varchar(500) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 发布任务表
-- ============================================================
CREATE TABLE IF NOT EXISTS `publish_tasks` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `task_name` varchar(200) NOT NULL,
  `task_type` varchar(50) DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'pending',
  `target_node` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `completed_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 缓存节点表
-- ============================================================
CREATE TABLE IF NOT EXISTS `cache_nodes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `node_name` varchar(100) NOT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `port` int(11) DEFAULT 6379,
  `status` varchar(20) NOT NULL DEFAULT 'offline',
  `remark` varchar(255) DEFAULT NULL,
  `last_heartbeat` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 运维备注表
-- ============================================================
CREATE TABLE IF NOT EXISTS `ops_notes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL,
  `content` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 操作日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS `operation_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) DEFAULT NULL,
  `action` varchar(50) NOT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `action` (`action`),
  KEY `created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- 种子数据: 默认用户 (bcrypt hash)
-- ============================================================
INSERT IGNORE INTO `users` (`username`, `password_hash`, `nickname`, `email`, `role`, `status`) VALUES
('admin',    '$2b$12$AwBJL0bfs5pZjwiN38ezwu.9Qa7GbN1k9wMCJ7a6.Mrwr1dLKpcfi', '系统管理员', 'admin@media-ops.local',    'admin',    1),
('operator', '$2b$12$3ENZZG6iEsRgs9otQEgHUOUGbCQvynh/DiwRVNrysjBLDeo6KTFKq', '运营人员',   'operator@media-ops.local', 'operator', 1),
('editor',   '$2b$12$tf09tXCPMz2eEkF60gzsH.VYzmAAoAeSvFegdZq4jIIe8qBEmMMaa', '编辑人员',   'editor@media-ops.local',   'editor',   1);

-- ============================================================
-- 种子数据: 角色
-- ============================================================
INSERT IGNORE INTO `roles` (`name`, `display_name`) VALUES
('admin',    '系统管理员'),
('operator', '运营人员'),
('editor',   '编辑人员');

-- ============================================================
-- 种子数据: 频道栏目
-- ============================================================
INSERT IGNORE INTO `channels` (`name`, `code`, `status`, `sort_order`) VALUES
('CCTV-1 综合',     'cctv1',      1, 1),
('CCTV-2 财经',     'cctv2',      1, 2),
('CCTV-新闻',       'cctv13',     1, 3),
('CCTV-体育',       'cctv5',      1, 4),
('湖南卫视',         'hunan-tv',   1, 5);

-- ============================================================
-- 种子数据: 缓存节点
-- ============================================================
INSERT IGNORE INTO `cache_nodes` (`node_name`, `ip`, `port`, `status`, `remark`, `last_heartbeat`) VALUES
('华北缓存节点-01', '192.168.110.21', 6379, 'online',  '华北区域CDN缓存节点', NOW()),
('华东缓存节点-01', '192.168.110.22', 6379, 'online',  '华东区域CDN缓存节点', NOW()),
('华南缓存节点-01', '192.168.110.23', 6379, 'online',  '华南区域CDN缓存节点', NOW()),
('西南缓存节点-01', '192.168.110.24', 6379, 'offline', '西南区域CDN缓存节点', DATE_SUB(NOW(), INTERVAL 2 HOUR)),
('华中缓存节点-01', '192.168.110.25', 6379, 'online',  '华中区域CDN缓存节点', NOW());

-- ============================================================
-- 种子数据: 发布任务
-- ============================================================
INSERT IGNORE INTO `publish_tasks` (`task_name`, `task_type`, `status`, `target_node`, `created_at`, `completed_at`) VALUES
('EPG同步-CCTV1-20260523',       'epg_sync',     'completed', '华北缓存节点-01', DATE_SUB(NOW(), INTERVAL 2 HOUR), DATE_SUB(NOW(), INTERVAL 1 HOUR)),
('频道封面刷新-CCTV新闻',         'cover_refresh', 'completed', '华东缓存节点-01', DATE_SUB(NOW(), INTERVAL 3 HOUR), DATE_SUB(NOW(), INTERVAL 2 HOUR)),
('节目素材发布-晚间新闻档',        'material_push', 'pending',   '华南缓存节点-01', DATE_SUB(NOW(), INTERVAL 1 HOUR), NULL),
('缓存预热-CCTV5体育频道',        'cache_warmup',  'running',   '华北缓存节点-01', DATE_SUB(NOW(), INTERVAL 30 MINUTE), NULL);

-- ============================================================
-- 种子数据: 运维备注 (含内网线索)
-- ============================================================
INSERT IGNORE INTO `ops_notes` (`title`, `content`, `created_at`) VALUES
('缓存发布支撑区说明', '内容发布平台通过内网访问缓存发布支撑节点。\n当前缓存节点地址：192.168.110.20:6379。\n缓存发布队列 key：media:publish:queue。\n缓存节点仅允许内容运营平台访问。', NOW()),
('接口联调备忘', '系统间接口联调期间，部分API接口暂未接入统一认证网关。联调完成后需统一回收未授权接口的访问控制。', DATE_SUB(NOW(), INTERVAL 30 DAY)),
('EPG发布规范', 'EPG文件需按频道编码分类存放，发布前需经编辑审核。旧版系统导出的模板包使用PHP序列化格式，导入时需通过发布模板导入功能处理。', DATE_SUB(NOW(), INTERVAL 60 DAY));

-- ============================================================
-- 种子数据: 操作日志
-- ============================================================
INSERT IGNORE INTO `operation_logs` (`username`, `action`, `ip`, `created_at`) VALUES
('admin',    'login',         '192.168.110.1',   DATE_SUB(NOW(), INTERVAL 10 MINUTE)),
('admin',    'api_call',      '192.168.110.1',   DATE_SUB(NOW(), INTERVAL 15 MINUTE)),
('operator', 'create_task',   '192.168.110.1',   DATE_SUB(NOW(), INTERVAL 1 HOUR)),
('admin',    'cache_refresh', '192.168.110.1',   DATE_SUB(NOW(), INTERVAL 2 HOUR)),
('operator', 'upload_material','192.168.110.1',  DATE_SUB(NOW(), INTERVAL 3 HOUR)),
('editor',   'review_epg',    '192.168.110.1',   DATE_SUB(NOW(), INTERVAL 4 HOUR)),
('admin',    'api_call',      '192.168.110.1',   DATE_SUB(NOW(), INTERVAL 5 HOUR)),
('admin',    'login',         '192.168.110.1',   DATE_SUB(NOW(), INTERVAL 6 HOUR));
