-- 创建NewAPI监控系统数据库用户脚本
-- 请使用具有用户管理权限的账号执行此脚本

-- 1. 创建只读用户（用于API查询）
CREATE USER IF NOT EXISTS 'newapi_ro'@'%' IDENTIFIED BY 'newapi_ro_secure_password_2024';

-- 授予只读权限
GRANT SELECT ON `new-api`.* TO 'newapi_ro'@'%';

-- 2. 创建聚合用户（用于Worker写入聚合数据）
CREATE USER IF NOT EXISTS 'newapi_agg'@'%' IDENTIFIED BY 'newapi_agg_secure_password_2024';

-- 授予聚合用户权限
GRANT SELECT ON `new-api`.logs TO 'newapi_agg'@'%';
GRANT SELECT ON `new-api`.users TO 'newapi_agg'@'%';
GRANT SELECT ON `new-api`.tokens TO 'newapi_agg'@'%';
GRANT SELECT ON `new-api`.channels TO 'newapi_agg'@'%';
GRANT SELECT ON `new-api`.models TO 'newapi_agg'@'%';
GRANT SELECT ON `new-api`.vendors TO 'newapi_agg'@'%';
GRANT SELECT, INSERT, UPDATE ON `new-api`.agg_usage_hourly TO 'newapi_agg'@'%';

-- 3. 可选：创建管理用户（用于维护和监控）
-- CREATE USER IF NOT EXISTS 'newapi_admin'@'%' IDENTIFIED BY 'newapi_admin_secure_password_2024';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON `new-api`.* TO 'newapi_admin'@'%';
-- GRANT CREATE, DROP, INDEX, ALTER ON `new-api`.* TO 'newapi_admin'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 显示创建的用户
SELECT User, Host FROM mysql.user WHERE User LIKE 'newapi_%';

-- 显示用户权限
SHOW GRANTS FOR 'newapi_ro'@'%';
SHOW GRANTS FOR 'newapi_agg'@'%';

SELECT 'NewAPI监控系统用户创建完成！' AS message;
SELECT '请记得修改默认密码！' AS warning;
