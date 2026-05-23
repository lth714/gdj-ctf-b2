<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

echo "PHP Version: " . PHP_VERSION . "\n";
echo "Current Directory: " . __DIR__ . "\n";
echo "Document Root: " . $_SERVER['DOCUMENT_ROOT'] . "\n";

echo "\nPHP Extensions:\n";
print_r(get_loaded_extensions());

echo "\nFile Permissions:\n";
$paths = [
    '../config',
    '../public/uploads',
    '../storage/logs',
    '../storage/cache'
];

foreach ($paths as $path) {
    $fullPath = realpath(__DIR__ . '/' . $path);
    echo $path . ": " . 
         (file_exists($fullPath) ? "Exists" : "Not exists") . 
         (is_writable($fullPath) ? " (Writable)" : " (Not writable)") . 
         " - Permissions: " . substr(sprintf('%o', fileperms($fullPath)), -4) . "\n";
} 