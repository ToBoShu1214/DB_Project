<?php
// 老師的 Apache 伺服器預設會尋找 index.php
// 這裡我們直接幫他跳轉到我們寫好的前端介面
header("Location: frontend/index.html");
exit;
?>
