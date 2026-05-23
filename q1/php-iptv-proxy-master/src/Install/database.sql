SET FOREIGN_KEY_CHECKS=0;

-- ----------------------------
-- Table structure for admins
-- ----------------------------
DROP TABLE IF EXISTS `admins`;
CREATE TABLE `admins` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ----------------------------
-- Table structure for channels
-- ----------------------------
DROP TABLE IF EXISTS `channels`;
CREATE TABLE `channels` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `source_url` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `proxy_url` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `status` enum('active','inactive','error') CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'inactive',
  `connections` int DEFAULT '0',
  `bandwidth` float DEFAULT '0',
  `last_check` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `updated_ms` bigint DEFAULT '0',
  `group_id` int DEFAULT NULL,
  `sort_order` int DEFAULT '0',
  `response_time` int DEFAULT NULL COMMENT '检测响应延时(ms)',
  `last_accessed` datetime DEFAULT NULL,
  `last_checked` datetime DEFAULT NULL,
  `latency` int DEFAULT '0',
  `checked_at` timestamp NULL DEFAULT NULL,
  `error_count` int DEFAULT '0',
  `upload_bandwidth` float DEFAULT '0' COMMENT '上行带宽',
  `download_bandwidth` float DEFAULT '0' COMMENT '下行带宽',
  PRIMARY KEY (`id`),
  KEY `fk_channel_group` (`group_id`),
  CONSTRAINT `fk_channel_group` FOREIGN KEY (`group_id`) REFERENCES `channel_groups` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ----------------------------
-- Table structure for channel_connections
-- ----------------------------
DROP TABLE IF EXISTS `channel_connections`;
CREATE TABLE `channel_connections` (
  `id` int NOT NULL AUTO_INCREMENT,
  `channel_id` int unsigned NOT NULL,
  `last_active_time` datetime DEFAULT NULL,
  `disconnect_time` datetime DEFAULT NULL,
  `client_ip` varchar(45) DEFAULT NULL,
  `user_agent` varchar(255) DEFAULT NULL COMMENT '客户端 User Agent',
  `session_id` varchar(32) NOT NULL COMMENT '连接会话ID',
  `connect_time` datetime DEFAULT NULL,
  `status` enum('active','disconnected') NOT NULL DEFAULT 'active' COMMENT '连接状态',
  PRIMARY KEY (`id`),
  KEY `idx_last_active` (`last_active_time`),
  KEY `idx_channel_status` (`channel_id`,`status`),
  KEY `idx_session` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for channel_groups
-- ----------------------------
DROP TABLE IF EXISTS `channel_groups`;
CREATE TABLE `channel_groups` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `sort_order` int DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ----------------------------
-- Table structure for channel_logs
-- ----------------------------
DROP TABLE IF EXISTS `channel_logs`;
CREATE TABLE `channel_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `type` varchar(20) COLLATE utf8mb4_general_ci NOT NULL,
  `action` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `channel_id` int DEFAULT NULL,
  `channel_name` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `group_id` int DEFAULT NULL,
  `group_name` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `details` text COLLATE utf8mb4_general_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_type` (`type`),
  KEY `idx_channel_id` (`channel_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ----------------------------
-- Table structure for error_logs
-- ----------------------------
DROP TABLE IF EXISTS `error_logs`;
CREATE TABLE `error_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `level` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `file` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `line` int DEFAULT NULL,
  `trace` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ----------------------------
-- Table structure for settings
-- ----------------------------
DROP TABLE IF EXISTS `settings`;
CREATE TABLE `settings` (
  `key` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 在原有的表结构后添加以下内容：

-- ----------------------------
-- Records of settings
-- ----------------------------
INSERT INTO `settings` (`key`, `value`, `description`, `created_at`, `updated_at`) VALUES
('cache_time', '300', '缓存时间(秒)', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('check_interval', '6', '检查间隔(小时)', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('check_mode', 'daily', '检查模式(daily/interval)', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('chunk_size', '1048576', '流媒体分块大小(字节)', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('daily_check_time', '03:00', '每日检查时间', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('max_error_count', '5', '最大错误次数', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('monitor_refresh_interval', '8', '监控页面刷新间隔(秒)', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('proxy_buffer_size', '2048', '代理缓冲区大小(KB)', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('proxy_host', '0.0.0.0', '代理服务器监听地址', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('proxy_port', '9261', '代理服务器端口', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('proxy_timeout', '10', '代理超时时间(秒)', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('redis_host', '127.0.0.1', 'Redis服务器地址', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('redis_password', '', 'Redis密码', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('redis_port', '6379', 'Redis端口', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('site_name', 'IPTV代理系统', '站点名称', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('status_check_interval', '10', '状态检查间隔(秒)', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('clear_logs_on_stop', '0', '停止时是否清空日志', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

SET FOREIGN_KEY_CHECKS=1;