-- ============================================
-- VM-C2 内部OA数据库初始化
-- 创建oa业务库 + users表 (供VM-C1 ApiController使用)
-- ============================================

CREATE DATABASE IF NOT EXISTS oa CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'oauser'@'%' IDENTIFIED BY 'Oaus3r@2024!';
CREATE USER IF NOT EXISTS 'oauser'@'localhost' IDENTIFIED BY 'Oaus3r@2024!';
GRANT ALL PRIVILEGES ON oa.* TO 'oauser'@'%';
GRANT ALL PRIVILEGES ON oa.* TO 'oauser'@'localhost';
FLUSH PRIVILEGES;

USE oa;

-- OA业务用户表 (供 /api/login 认证)
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(50) NOT NULL UNIQUE,
    `password` VARCHAR(100) NOT NULL,
    `email` VARCHAR(100) DEFAULT '',
    `department` VARCHAR(50) DEFAULT '',
    `role` VARCHAR(20) DEFAULT 'user'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `users` (username, password, email, department, role) VALUES
('admin',    'admin123',      'admin@gdj.local',     '技术部', 'admin'),
('zhangsan', 'Pass@1234',     'zhangsan@gdj.local',  '市场部', 'user'),
('lisi',     'Lisi@2024',     'lisi@gdj.local',      '研发部', 'user'),
('wangwu',   'WangWu#5678',   'wangwu@gdj.local',    '运维部', 'user'),
('operator', '0p3rat0r@GDJ',  'operator@gdj.local',  '运维部', 'operator');
