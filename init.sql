-- Crear usuario específico para la aplicación
CREATE USER IF NOT EXISTS 'app_user'@'%' IDENTIFIED BY 'app_password';
GRANT ALL PRIVILEGES ON excel_uploader.* TO 'app_user'@'%';
FLUSH PRIVILEGES;