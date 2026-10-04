<?php
header('Content-Type: application/json');
echo json_encode([
    'status' => 'ok',
    'php_version' => phpversion(),
    'sqlite3_enabled' => extension_loaded('sqlite3'),
    'pdo_sqlite_enabled' => extension_loaded('pdo_sqlite')
]);
