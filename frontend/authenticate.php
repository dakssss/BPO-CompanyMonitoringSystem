<?php
session_start();

// Dummy credentials (use database in production)
$valid_users = [
    "Nextvas@IT" => "N3xtv4z@it",
    "admin321" => "admin123"

    
];

$username = $_POST['username'];
$password = $_POST['password'];

if (isset($valid_users[$username]) && $valid_users[$username] === $password) {
    $_SESSION['user'] = $username;
    header("Location: index.php");
    exit();
} else {
    echo "<script>alert('Invalid credentials'); window.location.href='login.php';</script>";
}
?>
