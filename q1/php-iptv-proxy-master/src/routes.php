// ... 保持现有路由不变 ...

// 带宽监控相关路由
'/api/bandwidth' => ['Api\BandwidthController', 'getAll'],
'/api/bandwidth/{id}' => ['Api\BandwidthController', 'getOne'], 