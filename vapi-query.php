<?php
// vapi-query.php - Real-Time High Performance DLD SQL Query Engine for Vapi Voice AI
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

$db_path = __DIR__ . '/data/transactions.db';
if (!file_exists($db_path)) {
    echo json_encode([
        'error' => 'Database file not found',
        'results' => [['toolCallId' => 'error', 'result' => 'Database file not found']]
    ]);
    exit;
}

try {
    $pdo = new PDO('sqlite:' . $db_path);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);

    // Register MEDIAN aggregate function in SQLite
    $pdo->sqliteCreateAggregate(
        'median',
        function (&$context, $row, $value) {
            if ($value !== null && is_numeric($value)) {
                if (!is_array($context)) {
                    $context = [];
                }
                $context[] = (float)$value;
            }
            return $context;
        },
        function (&$context) {
            if (empty($context)) return null;
            sort($context);
            $n = count($context);
            $mid = floor($n / 2);
            if ($n % 2 == 1) {
                return $context[$mid];
            } else {
                return ($context[$mid - 1] + $context[$mid]) / 2.0;
            }
        }
    );

    // Register quantile / percentile aliases if used
    $pdo->sqliteCreateAggregate(
        'percentile_cont',
        function (&$context, $row, $value) {
            if ($value !== null && is_numeric($value)) {
                if (!is_array($context)) {
                    $context = [];
                }
                $context[] = (float)$value;
            }
            return $context;
        },
        function (&$context) {
            if (empty($context)) return null;
            sort($context);
            $n = count($context);
            $mid = floor($n / 2);
            return $context[$mid];
        }
    );

} catch (Exception $e) {
    echo json_encode([
        'error' => 'Failed to connect to database: ' . $e->getMessage(),
        'results' => [['toolCallId' => 'error', 'result' => 'Database connection failed']]
    ]);
    exit;
}

// Read incoming input
$raw_input = file_get_contents('php://input');
$body = json_decode($raw_input, true) ?: [];

// Check if this is a Vapi tool call request
$tool_calls = [];
if (!empty($body['message']['toolCalls'])) {
    $tool_calls = $body['message']['toolCalls'];
} elseif (!empty($body['toolCalls'])) {
    $tool_calls = $body['toolCalls'];
}

// Function to normalize SQL query for maximum compatibility
function sanitize_and_normalize_sql($sql) {
    $sql = trim($sql);
    // Remove trailing semicolons
    $sql = rtrim($sql, ';');

    // Security check: Only allow SELECT or WITH statements
    if (!preg_match('/^(SELECT|WITH)\b/i', $sql)) {
        throw new Exception("Only SELECT queries are permitted.");
    }

    // Replace table aliases
    $sql = preg_replace('/\bFROM\s+data\b/i', 'FROM sales', $sql);
    $sql = preg_replace('/\bFROM\s+sales_data\b/i', 'FROM sales', $sql);

    // Map common conversational areas if queried directly
    $area_maps = [
        "'Dubai Marina'" => "('Marsa Dubai', 'Dubai Marina')",
        "'JLT'" => "('Al Thanyah Fifth', 'Jumeirah Lakes Towers', 'JLT')",
        "'Jumeirah Lake Towers'" => "('Al Thanyah Fifth', 'Jumeirah Lakes Towers')",
        "'Downtown Dubai'" => "('Burj Khalifa', 'Downtown Dubai')",
        "'JVC'" => "('Al Barsha South Fourth', 'Jumeirah Village Circle', 'JVC')",
        "'Dubai Hills'" => "('Hadaeq Sheikh Mohammed Bin Rashid', 'Dubai Hills', 'Dubai Hills Estate')",
        "'Dubai South'" => "('Madinat Al Mataar', 'Dubai South')",
        "'Motor City'" => "('Al Hebiah First', 'Motor City')",
        "'Sports City'" => "('Al Hebiah Fourth', 'Dubai Sports City', 'Sports City')"
    ];

    foreach ($area_maps as $spoken => $replacement) {
        $sql = preg_replace("/\barea\s*=\s*" . preg_quote($spoken, '/') . "/i", "area IN " . $replacement, $sql);
    }

    return $sql;
}

// Process tool calls if present
if (!empty($tool_calls)) {
    $responses = [];
    foreach ($tool_calls as $call) {
        $call_id = $call['id'] ?? 'unknown';
        $fn = $call['function'] ?? [];
        $args = $fn['arguments'] ?? [];
        
        if (is_string($args)) {
            $decoded_args = json_decode($args, true);
            if ($decoded_args) {
                $args = $decoded_args;
            }
        }

        $sql_query = $args['sql_query'] ?? $args['query'] ?? null;

        if (!$sql_query) {
            $responses[] = [
                'toolCallId' => $call_id,
                'result' => 'Error: You did not provide a sql_query argument.'
            ];
            continue;
        }

        try {
            $prepared_sql = sanitize_and_normalize_sql($sql_query);
            $stmt = $pdo->query($prepared_sql);
            $rows = $stmt->fetchAll();

            $responses[] = [
                'toolCallId' => $call_id,
                'result' => json_encode($rows)
            ];
        } catch (Exception $e) {
            $responses[] = [
                'toolCallId' => $call_id,
                'result' => 'Database Error: ' . $e->getMessage()
            ];
        }
    }

    echo json_encode(['results' => $responses]);
    exit;
}

// Direct query fallback for testing via browser/cURL/GET/POST
$direct_query = $body['sql_query'] ?? $body['query'] ?? $_GET['sql_query'] ?? $_GET['query'] ?? null;

if ($direct_query) {
    try {
        $prepared_sql = sanitize_and_normalize_sql($direct_query);
        $stmt = $pdo->query($prepared_sql);
        $rows = $stmt->fetchAll();

        echo json_encode([
            'status' => 'success',
            'query' => $prepared_sql,
            'count' => count($rows),
            'results' => $rows
        ]);
    } catch (Exception $e) {
        http_response_code(400);
        echo json_encode([
            'status' => 'error',
            'message' => $e->getMessage()
        ]);
    }
    exit;
}

// Default response if no parameters provided
echo json_encode([
    'status' => 'ready',
    'service' => 'Vapi Real Estate SQL Webhook Engine',
    'database' => [
        'file' => basename($db_path),
        'size_mb' => round(filesize($db_path) / (1024 * 1024), 2),
        'tables' => ['sales', 'rentals', 'data']
    ]
]);
