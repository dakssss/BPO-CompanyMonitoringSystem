<?php
session_start();
if (isset($_SESSION['user'])) {
    header("Location: index.php");
    exit();
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Login - PC Monitor</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        
        body {
                font-family: Arial;
                background: url('https://en.idei.club/uploads/posts/2023-06/1685765735_en-idei-club-p-investment-background-dizain-65.jpg') no-repeat center center fixed;
                background-size: cover;
                display: flex;
                height: 100vh;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }

            form {
    background: rgba(255, 255, 255, 0.8); /* White background with 80% opacity */
    padding: 30px;
    border-radius: 10px;
    box-shadow: 0 0 10px #ccc;
    width: 100%; /* Ensure the form takes up the full width */
    max-width: 400px; /* Optional: limit the form width to a maximum size */
    margin: auto; /* Centers the form on the page */
}

input {
    display: block;
    margin-bottom: 15px;
    padding: 10px; /* Increased padding for better input size */
    width: 100%;
    border: 1px solid #ccc; /* Border around input */
    border-radius: 5px; /* Rounded corners for input */
    box-sizing: border-box; /* Ensure padding doesn't affect width */
}

button {
    padding: 10px;
    width: 100%;
    background-color: #132937; /* Optional: Add a background color */
    color: white; /* Text color */
    border: none; /* Remove default border */
    border-radius: 5px; /* Rounded corners for the button */
    cursor: pointer; /* Change cursor to pointer on hover */
    font-size: 16px; /* Optional: Larger text size */
}
h2 {
      color: #127179;
      display: flex;
      align-items: center;
    }

    .icon {
      margin-right: 10px; /* Adds space between the icon and the text */
    }
    </style>
</head>
<body>
    <form method="POST" action="authenticate.php">
        
        <h2 style="color: #127179"><i class="fa fa-user icon"></i>Login</h2>
        <input type="text" name="username" placeholder="Username" required />
        <input type="password" name="password" placeholder="Password" required />
        <button type="submit">Log In</button>
    </form>
</body>
</html>
