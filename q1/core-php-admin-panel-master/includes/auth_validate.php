<?php

// Start session if not already started
if (session_status() === PHP_SESSION_NONE) {
	session_start();
}

// If user is not logged in, redirect to login page
if (!isset($_SESSION['user_logged_in']) || $_SESSION['user_logged_in'] !== true) {
	header('Location: login.php', true, 302);
	exit;
}

?>