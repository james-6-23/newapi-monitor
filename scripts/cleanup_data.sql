-- NewAPI监控系统数据清理脚本
-- 用于清理旧数据，释放存储空间

USE `new-api`;

-- 设置安全模式（防止误删）
SET SQL_SAFE_UPDATES = 0;

-- 1. 显示当前数据量
SELECT '=== 清理前数据统计 ===' as '信息';

SELECT 
    'logs' as '表名',
    COUNT(*) as '总行数',
    COUNT(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 END) as '最近30天',
    COUNT(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY) THEN 1 END) as '最近90天',
    COUNT(CASE WHEN created_at < DATE_SUB(NOW(), INTERVAL 90 DAY) THEN 1 END) as '90天前'
FROM logs;

SELECT 
    'agg_usage_hourly' as '表名',
    COUNT(*) as '总行数',
    COUNT(CASE WHEN hour_bucket >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 END) as '最近30天',
    COUNT(CASE WHEN hour_bucket >= DATE_SUB(NOW(), INTERVAL 90 DAY) THEN 1 END) as '最近90天',
    COUNT(CASE WHEN hour_bucket < DATE_SUB(NOW(), INTERVAL 90 DAY) THEN 1 END) as '90天前'
FROM agg_usage_hourly;

-- 2. 清理90天前的原始日志数据（可选，谨慎操作）
-- 注意：这会永久删除数据，请确保已备份重要数据
-- 建议先在测试环境验证

-- 显示将要删除的数据量
SELECT 
    '将要删除的logs记录数' as '操作',
    COUNT(*) as '数量',
    MIN(created_at) as '最早时间',
    MAX(created_at) as '最晚时间'
FROM logs 
WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY);

-- 实际删除操作（默认注释，需要时取消注释）
/*
-- 分批删除，避免长时间锁表
DELIMITER $$
CREATE PROCEDURE CleanOldLogs()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE batch_size INT DEFAULT 10000;
    DECLARE deleted_rows INT;
    
    -- 循环删除
    REPEAT
        DELETE FROM logs 
        WHERE created_at < DATE_SUB(NOW(), INTERVAL 90 DAY)
        LIMIT batch_size;
        
        SET deleted_rows = ROW_COUNT();
        
        -- 短暂休息，避免影响正常业务
        SELECT SLEEP(0.1);
        
    UNTIL deleted_rows < batch_size END REPEAT;
    
END$$
DELIMITER ;

-- 执行清理
CALL CleanOldLogs();

-- 删除存储过程
DROP PROCEDURE CleanOldLogs;
*/

-- 3. 清理90天前的聚合数据
SELECT 
    '将要删除的agg_usage_hourly记录数' as '操作',
    COUNT(*) as '数量',
    MIN(hour_bucket) as '最早时间',
    MAX(hour_bucket) as '最晚时间'
FROM agg_usage_hourly 
WHERE hour_bucket < DATE_SUB(NOW(), INTERVAL 90 DAY);

-- 删除90天前的聚合数据
DELETE FROM agg_usage_hourly 
WHERE hour_bucket < DATE_SUB(NOW(), INTERVAL 90 DAY);

SELECT CONCAT('删除了 ', ROW_COUNT(), ' 条聚合数据记录') as '结果';

-- 4. 优化表空间
SELECT '=== 开始优化表空间 ===' as '信息';

-- 重建表以回收空间
ALTER TABLE logs ENGINE=InnoDB;
ALTER TABLE agg_usage_hourly ENGINE=InnoDB;

-- 分析表
ANALYZE TABLE logs;
ANALYZE TABLE agg_usage_hourly;
ANALYZE TABLE users;
ANALYZE TABLE tokens;
ANALYZE TABLE channels;
ANALYZE TABLE models;

-- 5. 显示清理后的数据量
SELECT '=== 清理后数据统计 ===' as '信息';

SELECT 
    TABLE_NAME as '表名',
    TABLE_ROWS as '行数',
    ROUND(DATA_LENGTH / 1024 / 1024, 2) as '数据大小(MB)',
    ROUND(INDEX_LENGTH / 1024 / 1024, 2) as '索引大小(MB)',
    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as '总大小(MB)'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'new-api' 
    AND TABLE_NAME IN ('logs', 'agg_usage_hourly')
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;

-- 6. 检查磁盘空间使用情况
SELECT 
    table_schema as '数据库',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) as '总大小(MB)'
FROM information_schema.tables 
WHERE table_schema = 'new-api'
GROUP BY table_schema;

-- 恢复安全模式
SET SQL_SAFE_UPDATES = 1;

SELECT '数据清理完成！' AS message;
SELECT '建议定期执行此脚本以维护数据库性能' AS suggestion;
