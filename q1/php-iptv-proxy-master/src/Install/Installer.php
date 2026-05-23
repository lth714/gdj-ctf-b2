<?php

class Installer
{
    private $requirements = [
        'php' => [
            'version' => '7.4.0',
            'description' => 'PHP版本要求 7.4.0 或更高'
        ],
        'extensions' => [
            'pdo' => [
                'required' => true,
                'description' => '数据库连接支持',
                'install_guide' => 'apt-get install php-pdo php-mysql'
            ],
            'pdo_mysql' => [
                'required' => true,
                'description' => 'MySQL数据库支持',
                'install_guide' => 'apt-get install php-mysql'
            ],
            'redis' => [
                'required' => true,
                'description' => 'Redis缓存支持',
                'install_guide' => 'apt-get install php-redis'
            ],
            'curl' => [
                'required' => true,
                'description' => '网络请求支持',
                'install_guide' => 'apt-get install php-curl'
            ],
            'json' => [
                'required' => true,
                'description' => 'JSON数据处理',
                'install_guide' => 'apt-get install php-json'
            ],
            'mbstring' => [
                'required' => true,
                'description' => '多字节字符串处理',
                'install_guide' => 'apt-get install php-mbstring'
            ]
        ],
        'functions' => [
            'proc_open' => [
                'required' => true,
                'description' => '进程控制支持',
                'install_guide' => '修改 php.ini 中的 disable_functions 移除 proc_open'
            ],
            'shell_exec' => [
                'required' => true,
                'description' => '命令执行支持',
                'install_guide' => '修改 php.ini 中的 disable_functions 移除 shell_exec'
            ]
        ]
    ];

    public function checkEnvironment()
    {
        $results = [
            'php' => $this->checkPhpVersion(),
            'extensions' => $this->checkExtensions(),
            'functions' => $this->checkFunctions(),
            'system' => $this->checkSystemRequirements(),
            'config' => $this->checkConfigFile(),
            'all_passed' => true
        ];

        foreach (['php', 'extensions', 'functions', 'system'] as $category) {
            if (isset($results[$category]['required_failed']) && $results[$category]['required_failed']) {
                $results['all_passed'] = false;
                break;
            }
        }

        // 检查配置文件状态
        if (!$results['config']['config_exists'] || !$results['config']['config_writable'] || $results['config']['error']) {
            $results['all_passed'] = false;
        }

        return $results;
    }

    private function checkPhpVersion()
    {
        $required = $this->requirements['php']['version'];
        $current = PHP_VERSION;
        $passed = version_compare($current, $required, '>=');

        return [
            'required' => $required,
            'current' => $current,
            'passed' => $passed,
            'required_failed' => !$passed,
            'description' => $this->requirements['php']['description']
        ];
    }

    private function checkExtensions()
    {
        $results = [
            'items' => [],
            'required_failed' => false
        ];

        foreach ($this->requirements['extensions'] as $ext => $config) {
            $loaded = extension_loaded($ext);
            $version = $loaded ? phpversion($ext) : null;
            
            $item = [
                'name' => $ext,
                'required' => $config['required'],
                'current' => $version ?: '未安装',
                'passed' => $loaded,
                'description' => $config['description'],
                'install_guide' => $config['install_guide']
            ];

            if ($config['required'] && !$loaded) {
                $results['required_failed'] = true;
            }

            $results['items'][$ext] = $item;
        }

        return $results;
    }

    private function checkFunctions()
    {
        $results = [
            'items' => [],
            'required_failed' => false
        ];

        foreach ($this->requirements['functions'] as $func => $config) {
            $exists = function_exists($func);
            
            $item = [
                'name' => $func,
                'required' => $config['required'],
                'passed' => $exists,
                'description' => $config['description'],
                'install_guide' => $config['install_guide']
            ];

            if ($config['required'] && !$exists) {
                $results['required_failed'] = true;
            }

            $results['items'][$func] = $item;
        }

        return $results;
    }

    private function checkSystemRequirements()
    {
        $results = [
            'items' => [],
            'required_failed' => false
        ];

        // 检查内存限制
        $memoryLimit = ini_get('memory_limit');
        $memoryLimitBytes = $this->returnBytes($memoryLimit);
        $minMemory = 128 * 1024 * 1024; // 128MB
        
        $results['items']['memory'] = [
            'name' => '内存限制',
            'required' => '128M',
            'current' => $memoryLimit,
            'passed' => $memoryLimitBytes >= $minMemory,
            'description' => '建议内存限制不低于128M',
            'install_guide' => '修改 php.ini 中的 memory_limit 值'
        ];

        // 检查最大执行时间
        $maxExecutionTime = ini_get('max_execution_time');
        $results['items']['max_execution_time'] = [
            'name' => '最大执行时间',
            'required' => '300',
            'current' => $maxExecutionTime,
            'passed' => $maxExecutionTime >= 300 || $maxExecutionTime == 0,
            'description' => '建议最大执行时间不低于300秒',
            'install_guide' => '修改 php.ini 中的 max_execution_time 值'
        ];

        foreach ($results['items'] as $item) {
            if (!$item['passed']) {
                $results['required_failed'] = true;
                break;
            }
        }

        return $results;
    }

    private function checkConfigFile()
    {
        $configPath = BASE_PATH . '/config/config.php';
        $templatePath = BASE_PATH . '/config/config.php.template';
        $results = [
            'config_exists' => false,
            'config_writable' => false,
            'template_exists' => false,
            'created' => false,
            'error' => null
        ];

        try {
            // 检查配置目录是否存在
            if (!is_dir(BASE_PATH . '/config')) {
                if (!@mkdir(BASE_PATH . '/config', 0755, true)) {
                    throw new Exception('无法创建配置目录');
                }
            }

            // 检查模板文件是否存在
            if (!file_exists($templatePath)) {
                throw new Exception('配置模板文件不存在');
            }
            $results['template_exists'] = true;

            // 检查配置文件是否已存在
            if (file_exists($configPath)) {
                $results['config_exists'] = true;
                $results['config_writable'] = is_writable($configPath);
            } else {
                // 检查目录是否可写
                $results['config_writable'] = is_writable(dirname($configPath));
                
                // 复制模板文件
                if (copy($templatePath, $configPath)) {
                    $results['created'] = true;
                    $results['config_exists'] = true;
                    $results['config_writable'] = true;
                } else {
                    throw new Exception('无法创建配置文件');
                }
            }

            return $results;

        } catch (Exception $e) {
            $results['error'] = $e->getMessage();
            return $results;
        }
    }

    private function returnBytes($val)
    {
        $val = trim($val);
        $last = strtolower($val[strlen($val)-1]);
        $val = (int)$val;
        
        switch($last) {
            case 'g':
                $val *= 1024;
            case 'm':
                $val *= 1024;
            case 'k':
                $val *= 1024;
        }
        
        return $val;
    }
    /**
     * 测试数据库连接
     * @param array $data
     * @return array
     */
    public function testDatabaseConnection($data)
    {
        try {
            // 验证输入
            $required = ['db_host', 'db_port', 'db_user', 'db_pass'];
            foreach ($required as $field) {
                if (empty($data[$field])) {
                    throw new Exception("请填写{$field}字段");
                }
            }

            // 测试连接
            $dsn = "mysql:host={$data['db_host']};port={$data['db_port']}";
            $pdo = new PDO($dsn, $data['db_user'], $data['db_pass']);
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

            // 检查数据库是否存在
            $dbExists = false;
            if (!empty($data['db_name'])) {
                $stmt = $pdo->query("SHOW DATABASES LIKE '{$data['db_name']}'");
                $dbExists = $stmt->rowCount() > 0;
            }

            return [
                'success' => true,
                'message' => '数据库连接成功',
                'db_exists' => $dbExists
            ];

        } catch (Exception $e) {
            return [
                'success' => false,
                'message' => '数据库连接失败: ' . $e->getMessage()
            ];
        }
    }

    /**
     * 配置数据库
     * @param array $data
     * @return array
     */
    public function configureDatabase($data)
    {
        try {
            // 验证输入
            $required = ['db_host', 'db_port', 'db_name', 'db_user', 'db_pass'];
            foreach ($required as $field) {
                if (empty($data[$field])) {
                    throw new Exception("请填写{$field}字段");
                }
            }

            // 连接数据库服务器
            $dsn = "mysql:host={$data['db_host']};port={$data['db_port']}";
            $pdo = new PDO($dsn, $data['db_user'], $data['db_pass']);
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

            // 检查数据库是否存在
            $stmt = $pdo->query("SHOW DATABASES LIKE '{$data['db_name']}'");
            $dbExists = $stmt->rowCount() > 0;

            if ($dbExists) {
                // 使用数据库
                $pdo->exec("USE `{$data['db_name']}`");
                
                // 禁用外键检查
                $pdo->exec("SET FOREIGN_KEY_CHECKS = 0");
                
                // 获取所有表
                $tables = $pdo->query("SHOW TABLES")->fetchAll(PDO::FETCH_COLUMN);
                
                // 删除所有表
                foreach ($tables as $table) {
                    $pdo->exec("DROP TABLE IF EXISTS `$table`");
                }
                
                // 启用外键检查
                $pdo->exec("SET FOREIGN_KEY_CHECKS = 1");
            } else {
                // 创建新数据库
                $pdo->exec("CREATE DATABASE `{$data['db_name']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
                $pdo->exec("USE `{$data['db_name']}`");
            }

            // 导入数据库结构和初始数据
            $sqlFile = BASE_PATH . '/src/Install/database.sql';
            if (!file_exists($sqlFile)) {
                throw new Exception('数据库结构文件不存在');
            }
            
            $sql = file_get_contents($sqlFile);
            if ($sql === false) {
                throw new Exception('无法读取数据库结构文件');
            }

            // 执行SQL语句
            try {
                // 分割SQL语句
                $statements = array_filter(array_map('trim', explode(';', $sql)));
                foreach ($statements as $statement) {
                    if (!empty($statement)) {
                        $pdo->exec($statement);
                    }
                }
            } catch (PDOException $e) {
                throw new Exception('导入数据库结构失败: ' . $e->getMessage());
            }

            // 更新配置文件
            $config = require BASE_PATH . '/config/config.php';
            $config['db'] = [
                'host' => $data['db_host'],
                'port' => $data['db_port'],
                'dbname' => $data['db_name'],
                'username' => $data['db_user'],
                'password' => $data['db_pass']
            ];

            file_put_contents(
                BASE_PATH . '/config/config.php',
                "<?php\nreturn " . var_export($config, true) . ";\n"
            );

            return [
                'success' => true,
                'message' => '数据库配置成功，已完成初始化'
            ];

        } catch (Exception $e) {
            return [
                'success' => false,
                'message' => '数据库配置失败: ' . $e->getMessage()
            ];
        }
    }

    /**
     * 测试 Redis 连接
     * @param array $data
     * @return array
     */
    public function testRedisConnection($data)
    {
        try {
            // 验证输入
            $required = ['redis_host', 'redis_port'];
            foreach ($required as $field) {
                if (empty($data[$field])) {
                    throw new Exception("请填写{$field}字段");
                }
            }

            // 测试连接
            $redis = new Redis();
            $connected = $redis->connect($data['redis_host'], $data['redis_port']);
            
            if (!$connected) {
                throw new Exception('Redis连接失败');
            }

            // 如果设置了密码，尝试认证
            if (!empty($data['redis_pass'])) {
                if (!$redis->auth($data['redis_pass'])) {
                    throw new Exception('Redis认证失败，请检查密码');
                }
            }

            // 测试写入和读取
            $testKey = 'install_test_' . uniqid();
            $testValue = 'test_' . time();
            if (!$redis->set($testKey, $testValue)) {
                throw new Exception('Redis写入测试失败');
            }
            if ($redis->get($testKey) !== $testValue) {
                throw new Exception('Redis读取测试失败');
            }
            $redis->del($testKey);

            return [
                'success' => true,
                'message' => 'Redis连接成功'
            ];

        } catch (Exception $e) {
            return [
                'success' => false,
                'message' => 'Redis连接失败: ' . $e->getMessage()
            ];
        }
    }

    /**
     * 配置 Redis
     * @param array $data
     * @return array
     */
    public function configureRedis($data)
    {
        try {
            // 验证输入
            $required = ['redis_host', 'redis_port'];
            foreach ($required as $field) {
                if (empty($data[$field])) {
                    throw new Exception("请填写{$field}字段");
                }
            }

            // 测试连接
            $testResult = $this->testRedisConnection($data);
            if (!$testResult['success']) {
                throw new Exception($testResult['message']);
            }

            // 1. 更新配置文件
            $config = require BASE_PATH . '/config/config.php';
            $config['redis'] = [
                'host' => $data['redis_host'],
                'port' => $data['redis_port'],
                'password' => empty($data['redis_pass']) ? null : $data['redis_pass']
            ];

            file_put_contents(
                BASE_PATH . '/config/config.php',
                "<?php\nreturn " . var_export($config, true) . ";\n"
            );

            // 2. 更新数据库
            try {
                // 使用配置文件中的数据库配置
                $dbConfig = $config['db'];
                $dsn = "mysql:host={$dbConfig['host']};port={$dbConfig['port']};dbname={$dbConfig['dbname']}";
                $pdo = new PDO($dsn, $dbConfig['username'], $dbConfig['password']);
                $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

                // 准备更新语句
                $stmt = $pdo->prepare("
                    INSERT INTO settings (`key`, `value`, `description`) 
                    VALUES (:key, :value, :description)
                    ON DUPLICATE KEY UPDATE 
                    `value` = VALUES(`value`),
                    `description` = VALUES(`description`),
                    `updated_at` = CURRENT_TIMESTAMP
                ");

                // 更新 Redis 配置
                $redisSettings = [
                    'redis_host' => [
                        'value' => $data['redis_host'],
                        'description' => 'Redis服务器地址'
                    ],
                    'redis_port' => [
                        'value' => $data['redis_port'],
                        'description' => 'Redis端口'
                    ],
                    'redis_password' => [
                        'value' => empty($data['redis_pass']) ? '' : $data['redis_pass'],
                        'description' => 'Redis密码'
                    ]
                ];

                foreach ($redisSettings as $key => $setting) {
                    $stmt->execute([
                        'key' => $key,
                        'value' => $setting['value'],
                        'description' => $setting['description']
                    ]);
                }

                return [
                    'success' => true,
                    'message' => 'Redis配置已成功更新到配置文件和数据库'
                ];

            } catch (PDOException $e) {
                throw new Exception('数据库更新失败: ' . $e->getMessage());
            }

        } catch (Exception $e) {
            return [
                'success' => false,
                'message' => 'Redis配置失败: ' . $e->getMessage()
            ];
        }
    }

    /**
     * 配置管理员账号
     * @param array $data
     * @return array
     */
    public function configureAdmin($data)
    {
        try {
            // 验证输入
            $required = ['username', 'password', 'confirm_password'];
            foreach ($required as $field) {
                if (empty($data[$field])) {
                    throw new Exception("请填写{$field}字段");
                }
            }

            // 验证密码
            if ($data['password'] !== $data['confirm_password']) {
                throw new Exception('两次输入的密码不一致');
            }

            if (strlen($data['password']) < 6) {
                throw new Exception('密码长度不能少于6个字符');
            }

            // 获取数据库配置
            $config = require BASE_PATH . '/config/config.php';
            $dbConfig = $config['db'];

            try {
                // 连接数据库
                $dsn = "mysql:host={$dbConfig['host']};port={$dbConfig['port']};dbname={$dbConfig['dbname']}";
                $pdo = new PDO($dsn, $dbConfig['username'], $dbConfig['password']);
                $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

                // 检查用户名是否已存在
                $stmt = $pdo->prepare("SELECT COUNT(*) FROM admins WHERE username = ?");
                $stmt->execute([$data['username']]);
                if ($stmt->fetchColumn() > 0) {
                    throw new Exception('用户名已存在');
                }

                // 创建管理员账号
                $stmt = $pdo->prepare("
                    INSERT INTO admins (username, password, description) 
                    VALUES (:username, :password, :description)
                ");

                // 密码加密
                $hashedPassword = password_hash($data['password'], PASSWORD_DEFAULT);

                $stmt->execute([
                    'username' => $data['username'],
                    'password' => $hashedPassword,
                    'description' => $data['description'] ?? '系统管理员'
                ]);

                // 更新站点名称设置
                if (!empty($data['site_name'])) {
                    $stmt = $pdo->prepare("
                        INSERT INTO settings (`key`, `value`, `description`) 
                        VALUES ('site_name', :value, '站点名称')
                        ON DUPLICATE KEY UPDATE 
                        `value` = VALUES(`value`),
                        `updated_at` = CURRENT_TIMESTAMP
                    ");
                    $stmt->execute(['value' => $data['site_name']]);
                }

                return [
                    'success' => true,
                    'message' => '管理员账号配置成功'
                ];

            } catch (PDOException $e) {
                throw new Exception('数据库操作失败: ' . $e->getMessage());
            }

        } catch (Exception $e) {
            return [
                'success' => false,
                'message' => '管理员配置失败: ' . $e->getMessage()
            ];
        }
    }

    /**
     * 完成安装
     * @return array
     */
    public function finishInstallation()
    {
        try {
            // 创建安装锁定文件
            $lockFile = BASE_PATH . '/storage/installed.lock';
            $lockContent = date('Y-m-d H:i:s');
            
            if (!file_put_contents($lockFile, $lockContent)) {
                throw new Exception('无法创建安装锁定文件');
            }

            // 获取数据库配置
            $config = require BASE_PATH . '/config/config.php';
            $dbConfig = $config['db'];

            try {
                // 连接数据库
                $dsn = "mysql:host={$dbConfig['host']};port={$dbConfig['port']};dbname={$dbConfig['dbname']}";
                $pdo = new PDO($dsn, $dbConfig['username'], $dbConfig['password']);
                $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

                // 记录安装完成时间
                $stmt = $pdo->prepare("
                    INSERT INTO settings (`key`, `value`, `description`) 
                    VALUES ('install_time', :value, '系统安装时间')
                    ON DUPLICATE KEY UPDATE 
                    `value` = VALUES(`value`),
                    `updated_at` = CURRENT_TIMESTAMP
                ");
                
                $stmt->execute(['value' => $lockContent]);

                return [
                    'success' => true,
                    'message' => '安装完成'
                ];

            } catch (PDOException $e) {
                throw new Exception('数据库操作失败: ' . $e->getMessage());
            }

        } catch (Exception $e) {
            return [
                'success' => false,
                'message' => '完成安装失败: ' . $e->getMessage()
            ];
        }
    }
}