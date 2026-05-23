<?php
define('BASE_PATH', dirname(dirname(__DIR__)));
require BASE_PATH . '/src/Controllers/AuthController.php';

$controller = new App\Controllers\AuthController();
$controller->login(); 