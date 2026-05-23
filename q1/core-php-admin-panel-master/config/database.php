<?php
/**
 * 扩展数据库与缓存服务配置
 * 视听内容运营平台 — 内部使用
 */

// 数据库连接配置
define('DB_HOST_INTERNAL', '127.0.0.1');
define('DB_PORT_INTERNAL', '3306');
define('DB_USER_INTERNAL', 'media_app');
define('DB_PASSWORD_INTERNAL', 'MediaDB@2026!');
define('DB_NAME_INTERNAL', 'media_ops');

// 缓存发布支撑区配置
define('REDIS_HOST', '192.168.110.20');
define('REDIS_PORT', '6379');
define('REDIS_AUTH', '');
define('REDIS_DB', '0');

// 缓存Key前缀定义
define('CACHE_KEY_PUBLISH_QUEUE', 'media:publish:queue');
define('CACHE_KEY_PUBLISH_LAST_JOB', 'media:publish:last_job');
define('CACHE_KEY_CACHE_NODES', 'media:cache:nodes');
define('CACHE_KEY_CACHE_STATUS', 'media:cache:status');
define('CACHE_KEY_OPS_NOTE', 'media:ops:note');
define('CACHE_KEY_AGENT_CONFIG', 'media:agent:config');
