-- ============================================
-- VM-A2 区域IPTV内容编排平台 — 数据库初始化
-- 数据来源于业务数据库备份
-- ============================================

CREATE DATABASE IF NOT EXISTS cms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'cmsuser'@'%' IDENTIFIED BY 'Cm5Us3r@2024!';
CREATE USER IF NOT EXISTS 'cmsuser'@'localhost' IDENTIFIED BY 'Cm5Us3r@2024!';
GRANT ALL PRIVILEGES ON cms.* TO 'cmsuser'@'%';
GRANT ALL PRIVILEGES ON cms.* TO 'cmsuser'@'localhost';
GRANT FILE ON *.* TO 'cmsuser'@'%';
GRANT FILE ON *.* TO 'cmsuser'@'localhost';
FLUSH PRIVILEGES;

USE cms;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for ay_user (运营账号)
-- ----------------------------
DROP TABLE IF EXISTS `ay_user`;
CREATE TABLE `ay_user` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `ucode` varchar(20) NOT NULL,
  `username` varchar(50) NOT NULL,
  `realname` varchar(50) DEFAULT '',
  `password` varchar(64) NOT NULL,
  `status` tinyint(1) DEFAULT '1',
  `role_id` int(10) DEFAULT '1',
  `login_count` int(10) DEFAULT '0',
  `last_login_ip` varchar(15) DEFAULT '',
  `last_login_time` datetime DEFAULT NULL,
  `create_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `ay_user` VALUES (1, '10001', 'admin', '超级管理员',
  'f0916d59b2d497402968dbdd3641ddbe', 1, 1, 127, '192.168.100.1',
  '2024-01-01 01:55:00', '2023-06-15 10:00:00', '2024-01-01 01:55:00');
INSERT INTO `ay_user` VALUES (2, '10002', 'operator', '内容运营员',
  'dd50ad190a36ac0b8a8c5018a1752a79', 1, 2, 8, '192.168.100.1',
  '2023-12-28 14:30:00', '2023-11-01 09:00:00', '2023-12-28 14:30:00');
INSERT INTO `ay_user` VALUES (3, '10003', 'editor', '内容审核员',
  'bc21fcad528a604ab1a98c0aa105345e', 1, 3, 22, '192.168.100.1',
  '2023-12-30 11:20:00', '2023-07-01 14:00:00', '2023-12-30 11:20:00');

-- ----------------------------
-- Table structure for ay_role
-- ----------------------------
DROP TABLE IF EXISTS `ay_role`;
CREATE TABLE `ay_role` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `description` varchar(255) DEFAULT '',
  `permission` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `ay_role` VALUES (1, '超级管理员', '全部权限', 'all');
INSERT INTO `ay_role` VALUES (2, '内容运营员', '内容运营权限', 'content');
INSERT INTO `ay_role` VALUES (3, '内容审核员', '内容审核权限', 'edit');

-- ----------------------------
-- Table structure for ay_content (PbootCMS standard schema + CTF data)
-- ----------------------------
DROP TABLE IF EXISTS `ay_content`;
CREATE TABLE `ay_content` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `acode` varchar(20) NOT NULL DEFAULT 'cn',
  `scode` varchar(50) NOT NULL,
  `subscode` varchar(50) NOT NULL DEFAULT '',
  `title` varchar(255) NOT NULL,
  `filename` varchar(100) NOT NULL DEFAULT '',
  `outlink` varchar(255) NOT NULL DEFAULT '',
  `content` longtext,
  `description` text,
  `author` varchar(50) DEFAULT '',
  `tags` varchar(255) DEFAULT '',
  `enclosure` varchar(255) NOT NULL DEFAULT '',
  `keywords` varchar(200) NOT NULL DEFAULT '',
  `ico` varchar(255) DEFAULT '',
  `pics` text,
  `istop` tinyint(1) DEFAULT '0',
  `isrecommend` tinyint(1) DEFAULT '0',
  `isheadline` tinyint(1) DEFAULT '0',
  `visits` int(10) DEFAULT '0',
  `likes` int(10) DEFAULT '0',
  `oppose` int(10) DEFAULT '0',
  `gid` int(10) NOT NULL DEFAULT '0',
  `sorting` int(10) DEFAULT '0',
  `status` tinyint(1) DEFAULT '1',
  `date` datetime DEFAULT NULL,
  `create_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_scode` (`scode`),
  KEY `idx_title` (`title`),
  KEY `idx_date` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `ay_content` (`id`,`acode`,`scode`,`subscode`,`title`,`filename`,`outlink`,`content`,`description`,`author`,`tags`,`enclosure`,`keywords`,`ico`,`pics`,`istop`,`isrecommend`,`isheadline`,`visits`,`likes`,`oppose`,`gid`,`sorting`,`status`,`date`,`create_time`,`update_time`) VALUES
(1, 'cn', 'live', '', 'IPTV直播频道编排与运营指南', '', '',
  '<p>本指南涵盖直播频道编排策略、信号源管理及播控发布流程。频道列表每日通过内网数据服务同步，节目单由EPG导入模块自动更新。频道封面和台标通过后台内容运营模块上传，经审核后发布至前端推荐位展示。</p>',
  'IPTV直播频道编排与运营指南', '超级管理员', '直播,频道编排,运营指南', '', '', '', '', 1, 1, 0, 520, 15, 2, 0, 1, 1,
  '2024-01-01 00:00:00', '2024-01-01 00:00:00', '2024-01-01 00:00:00');
INSERT INTO `ay_content` (`id`,`acode`,`scode`,`subscode`,`title`,`filename`,`outlink`,`content`,`description`,`author`,`tags`,`enclosure`,`keywords`,`ico`,`pics`,`istop`,`isrecommend`,`isheadline`,`visits`,`likes`,`oppose`,`gid`,`sorting`,`status`,`date`,`create_time`,`update_time`) VALUES
(2, 'cn', 'announce', '', '播控内容发布同步管理规范', '', '',
  '<p>为确保播控内容发布的准确性和及时性，所有节目单变更、频道调整、推荐位更新均需在内容运营后台完成操作后同步至前端。<br><br>同步机制说明：<br>1. 内容发布后由后台自动触发同步任务；<br>2. 内网数据服务(192.168.100.2)提供数据库及缓存支撑；<br>3. 同步状态可在播控同步状态页面查看；<br>4. 发布审核流程通过内部知识库系统记录操作日志。<br><br>值班运营人员需按规范完成每日发布核查。</p>',
  '播控内容发布同步管理规范', '超级管理员', '播控,同步,发布,管理规范', '', '',
  '', '', 0, 1, 1, 380, 8, 1, 0, 1,
  '2023-12-25 10:00:00', '2023-12-25 10:00:00', '2023-12-25 10:00:00');
INSERT INTO `ay_content` (`id`,`acode`,`scode`,`subscode`,`title`,`filename`,`outlink`,`content`,`description`,`author`,`tags`,`enclosure`,`keywords`,`ico`,`pics`,`istop`,`isrecommend`,`isheadline`,`visits`,`likes`,`oppose`,`gid`,`sorting`,`status`,`date`,`create_time`,`update_time`) VALUES
(3, 'cn', 'live', '', '媒资同步与EPG编目管理方案', '', '',
  '<p>针对IPTV直播频道的媒资同步需求，制定以下技术方案：<br><br>一、EPG数据获取<br>通过定时任务从上游系统获取电子节目指南数据，经格式化处理后导入平台数据库。<br><br>二、缓存加速<br>高频访问的频道列表和EPG数据使用Redis进行缓存，减少数据库查询压力。缓存服务部署于内网服务器。<br><br>三、编目规范<br>节目编目信息包含频道名称、节目名称、播出时段、节目类型等字段，统一由内容运营员维护。</p>',
  '媒资同步与EPG编目管理方案', '内容审核员', '媒资,EPG,编目,同步,缓存', '', '',
  '', '', 0, 0, 0, 210, 5, 0, 0, 1,
  '2023-12-20 15:30:00', '2023-12-20 15:30:00', '2023-12-20 15:30:00');
INSERT INTO `ay_content` (`id`,`acode`,`scode`,`subscode`,`title`,`filename`,`outlink`,`content`,`description`,`author`,`tags`,`enclosure`,`keywords`,`ico`,`pics`,`istop`,`isrecommend`,`isheadline`,`visits`,`likes`,`oppose`,`gid`,`sorting`,`status`,`date`,`create_time`,`update_time`) VALUES
(4, 'cn', 'sync', '', '运维参考 - 内网服务与数据管理', '', '',
  '<p>一、数据库备份命令<br>mysqldump -h 192.168.100.2 -u cmsuser -p cms &gt; backup.sql<br><br>二、数据库恢复命令<br>mysql -h 192.168.100.2 -u root -p cms &lt; backup.sql<br><br>三、备份策略<br>每日凌晨2点自动执行数据库备份脚本，备份文件存放于指定归档目录。<br><br>四、内网服务依赖<br>- 数据库服务器：192.168.100.2:3306<br>- 缓存服务器：192.168.100.2:6379<br>- 内部知识库：http://192.168.100.2:8090<br><br>五、定时任务<br>播控支撑服务健康检查由计划任务定期执行，检查间隔为10分钟。</p>',
  '内网服务与数据管理运维参考', '超级管理员', '运维,数据库,备份,内网服务', '', '',
  '', '', 0, 0, 0, 125, 6, 0, 0, 1,
  '2023-11-15 09:00:00', '2023-11-15 09:00:00', '2023-11-15 09:00:00');

-- ----------------------------
-- Table structure for ay_content_sort (PbootCMS standard schema + CTF data)
-- ----------------------------
DROP TABLE IF EXISTS `ay_content_sort`;
CREATE TABLE `ay_content_sort` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `acode` varchar(20) NOT NULL DEFAULT 'cn',
  `scode` varchar(50) NOT NULL,
  `name` varchar(100) NOT NULL,
  `pcode` varchar(50) DEFAULT '',
  `sorting` int(10) DEFAULT '0',
  `mcode` varchar(20) NOT NULL DEFAULT '2',
  `status` tinyint(1) DEFAULT '1',
  `filename` varchar(100) DEFAULT '',
  `outlink` varchar(255) DEFAULT '',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ay_content_sort_scode` (`scode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `ay_content_sort` VALUES (1, 'cn', 'live', '直播频道', '0', 1, '2', 1, '', '');
INSERT INTO `ay_content_sort` VALUES (2, 'cn', 'vod', '回看节目', '0', 2, '2', 1, '', '');
INSERT INTO `ay_content_sort` VALUES (3, 'cn', 'epg', 'EPG节目单', '0', 3, '2', 1, '', '');
INSERT INTO `ay_content_sort` VALUES (4, 'cn', 'channel', '频道栏目', '0', 4, '2', 1, '', '');
INSERT INTO `ay_content_sort` VALUES (5, 'cn', 'recommend', '首页推荐位', '0', 5, '2', 1, '', '');
INSERT INTO `ay_content_sort` VALUES (6, 'cn', 'announce', '内容发布公告', '0', 6, '2', 1, '', '');
INSERT INTO `ay_content_sort` VALUES (7, 'cn', 'sync', '播控同步状态', '0', 7, '2', 1, '', '');

-- ----------------------------
-- Table structure for ay_site (站点配置)
-- ----------------------------
DROP TABLE IF EXISTS `ay_site`;
CREATE TABLE `ay_site` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `acode` varchar(20) NOT NULL DEFAULT '',
  `title` varchar(100) NOT NULL DEFAULT '',
  `subtitle` varchar(200) NOT NULL DEFAULT '',
  `domain` varchar(50) NOT NULL DEFAULT '',
  `logo` varchar(100) NOT NULL DEFAULT '',
  `keywords` varchar(200) NOT NULL DEFAULT '',
  `description` varchar(500) NOT NULL DEFAULT '',
  `icp` varchar(30) NOT NULL DEFAULT '',
  `theme` varchar(30) NOT NULL DEFAULT 'default',
  `statistical` varchar(500) NOT NULL DEFAULT '',
  `copyright` varchar(200) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  KEY `ay_site_acode` (`acode`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

INSERT INTO `ay_site` (`id`,`acode`,`title`,`subtitle`,`domain`,`logo`,`keywords`,`description`,`icp`,`theme`,`statistical`,`copyright`) VALUES
('1','cn','区域IPTV内容编排平台','','','/static/images/logo.png','IPTV,内容编排,播控,媒资管理,直播频道','区域IPTV内容编排与播控管理平台，面向播出机构提供频道编排、节目单管理、推荐位运营和播控同步支撑服务。','','default','','Copyright © 2024 区域视听内容运营中心 All Rights Reserved.');

-- ============================================
-- 新增业务表: 播控配置信息
-- ============================================
DROP TABLE IF EXISTS `publish_config`;
CREATE TABLE `publish_config` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `config_key` varchar(100) NOT NULL,
  `config_value` text,
  `description` varchar(255) DEFAULT '',
  `update_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `publish_config` VALUES
(1, 'confluence_url', 'http://192.168.100.2:8090', '播控知识库地址', '2024-03-01 10:00:00'),
(2, 'confluence_space', 'IPTV播控运行手册', '知识库空间名称', '2024-03-01 10:00:00'),
(3, 'redis_host', '192.168.100.2', '缓存服务器地址', '2024-03-01 10:00:00'),
(4, 'redis_port', '6379', '缓存服务器端口', '2024-03-01 10:00:00'),
(5, 'sync_interval', '600', '播控同步间隔(秒)', '2024-03-15 08:30:00'),
(6, 'health_check_script', '/opt/confluence_health_check.sh', '知识库健康检查脚本路径', '2024-04-10 14:00:00');

-- ============================================
-- 新增业务表: 内网资产清单
-- ============================================
DROP TABLE IF EXISTS `internal_assets`;
CREATE TABLE `internal_assets` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `asset_name` varchar(100) NOT NULL,
  `asset_type` varchar(50) DEFAULT '',
  `ip_address` varchar(50) DEFAULT '',
  `port` varchar(10) DEFAULT '',
  `notes` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `internal_assets` VALUES
(1, '内网数据库服务器', 'MySQL', '192.168.100.2', '3306', '数据库账号cmsuser，用于内容编排平台数据存储'),
(2, '内网缓存服务器', 'Redis', '192.168.100.2', '6379', '频道列表与EPG数据热缓存，减轻数据库查询压力'),
(3, '播控知识库', 'Confluence', '192.168.100.2', '8090', '播控发布运行手册及运维文档存放处'),
(4, '媒体处理API', 'API服务', '127.0.0.1', '5000', '频道封面缩放与EPG导入内部接口');

-- ============================================
-- 新增业务表: 运维记录
-- ============================================
DROP TABLE IF EXISTS `ops_notes`;
CREATE TABLE `ops_notes` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `note_date` date DEFAULT NULL,
  `author` varchar(50) DEFAULT '',
  `content` text,
  `category` varchar(50) DEFAULT '',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `ops_notes` VALUES
(1, '2024-03-15', '运维值班员',
 '播控知识库(Confluence)服务健康检查脚本位于 /opt/confluence_health_check.sh，由计划任务(cron)每10分钟自动执行，检测服务运行状态，异常时尝试自动重启。该脚本需保持可执行权限以确保故障自愈功能正常。',
 '服务监控'),
(2, '2024-04-20', '运维值班员',
 'Redis缓存服务用于存储EPG节目单和频道列表的热数据，减少对MySQL数据库的直接查询压力。缓存键命名规范: epg:{channel_id}:{date} 和 channel:list。内网地址192.168.100.2:6379，当前无密码认证。',
 '缓存配置'),
(3, '2024-05-10', '运维值班员',
 'operator账号用于日常内容运营操作，具备sudo权限执行服务管理命令。内网服务器通过iptables实施访问控制，仅允许来自内容编排服务器(192.168.100.1)的数据库、缓存和知识库端口访问，SSH端口对内容编排服务器关闭。',
 '账号管理'),
(4, '2024-05-18', '运维值班员',
 '内容运营员账号operator通过Web后台(admin.php)登录，负责节目单编辑、频道封面上传等日常操作。如遇登录问题，请先确认账号状态和角色权限配置，必要时联系超级管理员复核。',
 '账号管理');

SET FOREIGN_KEY_CHECKS = 1;
