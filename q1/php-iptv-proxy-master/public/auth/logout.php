<?php
require __DIR__ . '/../../vendor/autoload.php';

$controller = new \App\Controllers\AuthController();
$controller->logout();
?>