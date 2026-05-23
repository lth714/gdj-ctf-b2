<?php
namespace App\Models;

use App\Core\Database;

class ChannelGroup
{
    private $db;

    public function __construct()
    {
        $this->db = Database::getInstance()->getConnection();
    }

    public function getAllGroups()
    {
        try {
            $query = "SELECT g.*, COUNT(c.id) as channel_count 
                     FROM channel_groups g 
                     LEFT JOIN channels c ON g.id = c.group_id 
                     GROUP BY g.id";
            $stmt = $this->db->query($query);
            return $stmt->fetchAll(\PDO::FETCH_ASSOC);
        } catch (\PDOException $e) {
            return [];
        }
    }
}