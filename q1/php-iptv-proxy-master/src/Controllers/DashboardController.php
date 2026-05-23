<?php

class DashboardController
{
    public function index()
    {
        $config = Config::getInstance();
        $data = [
            'title' => '控制面板',
            'config' => $config
        ];
        
        $this->view->render('dashboard', $data);
    }
} 