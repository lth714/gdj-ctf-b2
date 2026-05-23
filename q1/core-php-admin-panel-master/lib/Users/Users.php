<?php
class Users
{
    public function __construct()
    {
    }

    public function __destruct()
    {
    }

    public function setOrderingValues()
    {
        $ordering = [
            'id' => 'ID',
            'username' => '用户名',
            'nickname' => '昵称',
            'email' => '邮箱',
            'role' => '角色',
            'status' => '状态',
            'created_at' => '创建时间'
        ];

        return $ordering;
    }
}
?>