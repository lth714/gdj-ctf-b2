<?php
namespace App\Core;

class Response
{
    public static function json($data, $statusCode = 200)
    {
        header('Content-Type: application/json');
        http_response_code($statusCode);
        echo json_encode($data, JSON_UNESCAPED_UNICODE);
        exit;
    }
    
    public static function error($message, $statusCode = 400)
    {
        self::json([
            'success' => false,
            'message' => $message
        ], $statusCode);
    }
    
    public static function success($data = null, $message = null)
    {
        $response = ['success' => true];
        
        if ($data !== null) {
            $response['data'] = $data;
        }
        
        if ($message !== null) {
            $response['message'] = $message;
        }
        
        self::json($response);
    }
} 