-- NewAPI监控系统性能检查脚本
-- 用于检查数据库性能和索引使用情况

USE `new-api`;

-- 1. 检查表大小和行数
SELECT 
    TABLE_NAME as '表名',
    TABLE_ROWS as '行数',
    ROUND(DATA_LENGTH / 1024 / 1024, 2) as '数据大小(MB)',
    ROUND(INDEX_LENGTH / 1024 / 1024, 2) as '索引大小(MB)',
    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as '总大小(MB)'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'new-api' 
    AND TABLE_NAME IN ('logs', 'users', 'tokens', 'channels', 'models', 'agg_usage_hourly')
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;

-- 2. 检查索引使用情况
SELECT 
    TABLE_NAME as '表名',
    INDEX_NAME as '索引名',
    COLUMN_NAME as '列名',
    SEQ_IN_INDEX as '序号',
    CARDINALITY as '基数',
    INDEX_TYPE as '索引类型'
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = 'new-api' 
    AND TABLE_NAME IN ('logs', 'users', 'tokens', 'channels', 'models', 'agg_usage_hourly')
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

-- 3. 检查慢查询相关配置
SHOW VARIABLES LIKE 'slow_query%';
SHOW VARIABLES LIKE 'long_query_time';

-- 4. 检查InnoDB状态
SHOW ENGINE INNODB STATUS\G

-- 5. 检查连接数
SHOW VARIABLES LIKE 'max_connections';
SHOW STATUS LIKE 'Threads_connected';
SHOW STATUS LIKE 'Threads_running';

-- 6. 检查缓冲池使用情况
SELECT 
    VARIABLE_NAME as '变量名',
    VARIABLE_VALUE as '值'
FROM information_schema.GLOBAL_STATUS 
WHERE VARIABLE_NAME IN (
    'Innodb_buffer_pool_size',
    'Innodb_buffer_pool_pages_total',
    'Innodb_buffer_pool_pages_free',
    'Innodb_buffer_pool_pages_data',
    'Innodb_buffer_pool_read_requests',
    'Innodb_buffer_pool_reads'
);

-- 7. 检查查询缓存（MySQL 5.7及以下）
-- SELECT 
--     VARIABLE_NAME as '变量名',
--     VARIABLE_VALUE as '值'
-- FROM information_schema.GLOBAL_STATUS 
-- WHERE VARIABLE_NAME LIKE 'Qcache%';

-- 8. 检查最近的查询性能（需要开启performance_schema）
SELECT 
    DIGEST_TEXT as '查询模式',
    COUNT_STAR as '执行次数',
    ROUND(AVG_TIMER_WAIT / 1000000000, 3) as '平均执行时间(秒)',
    ROUND(MAX_TIMER_WAIT / 1000000000, 3) as '最大执行时间(秒)',
    ROUND(SUM_TIMER_WAIT / 1000000000, 3) as '总执行时间(秒)'
FROM performance_schema.events_statements_summary_by_digest 
WHERE SCHEMA_NAME = 'new-api'
ORDER BY SUM_TIMER_WAIT DESC 
LIMIT 10;

-- 9. 检查表锁等待情况
SELECT 
    OBJECT_SCHEMA as '数据库',
    OBJECT_NAME as '表名',
    COUNT_STAR as '锁等待次数',
    ROUND(SUM_TIMER_WAIT / 1000000000, 3) as '总等待时间(秒)',
    ROUND(AVG_TIMER_WAIT / 1000000000, 3) as '平均等待时间(秒)'
FROM performance_schema.table_lock_waits_summary_by_table 
WHERE OBJECT_SCHEMA = 'new-api'
ORDER BY SUM_TIMER_WAIT DESC;

-- 10. 检查IO等待情况
SELECT 
    FILE_NAME as '文件名',
    EVENT_NAME as '事件名',
    COUNT_STAR as '次数',
    ROUND(SUM_TIMER_WAIT / 1000000000, 3) as '总等待时间(秒)',
    ROUND(AVG_TIMER_WAIT / 1000000000, 3) as '平均等待时间(秒)'
FROM performance_schema.file_summary_by_event_name 
WHERE FILE_NAME LIKE '%new-api%'
ORDER BY SUM_TIMER_WAIT DESC 
LIMIT 10;

-- 11. 生成优化建议
SELECT '=== 性能优化建议 ===' as '建议';

-- 检查是否需要增加索引
SELECT 
    CONCAT('建议为 ', TABLE_NAME, ' 表的查询添加合适的索引') as '建议'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'new-api' 
    AND TABLE_NAME = 'logs' 
    AND TABLE_ROWS > 1000000;

-- 检查是否需要分区
SELECT 
    CONCAT('建议对 ', TABLE_NAME, ' 表进行分区，当前行数: ', TABLE_ROWS) as '建议'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'new-api' 
    AND TABLE_NAME = 'logs' 
    AND TABLE_ROWS > 10000000;

-- 检查缓冲池命中率
SELECT 
    CASE 
        WHEN (SELECT VARIABLE_VALUE FROM information_schema.GLOBAL_STATUS WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests') > 0
        THEN CONCAT('缓冲池命中率: ', 
            ROUND(100 - (
                (SELECT VARIABLE_VALUE FROM information_schema.GLOBAL_STATUS WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads') * 100 / 
                (SELECT VARIABLE_VALUE FROM information_schema.GLOBAL_STATUS WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests')
            ), 2), '%')
        ELSE '无法计算缓冲池命中率'
    END as '缓冲池状态';

SELECT '性能检查完成！' AS message;
