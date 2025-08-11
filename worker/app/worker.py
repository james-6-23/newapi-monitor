"""Worker主应用 - 定时任务调度器"""
import asyncio
import signal
import sys
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import structlog

from .config import settings, rules_config
from .database import get_mysql_pool_ro, get_mysql_pool_agg, get_redis_client, close_connections
from .aggregator import data_aggregator
from .rules import rule_engine

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class WorkerApp:
    """Worker应用主类"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    async def start(self):
        """启动Worker服务"""
        logger.info("正在启动NewAPI监控Worker服务...")
        
        try:
            # 初始化数据库连接
            await self._init_connections()
            
            # 配置定时任务
            await self._setup_jobs()
            
            # 启动调度器
            self.scheduler.start()
            self.is_running = True
            
            logger.info("Worker服务启动成功")
            
            # 设置信号处理
            self._setup_signal_handlers()
            
            # 保持运行
            await self._keep_running()
            
        except Exception as e:
            logger.error("Worker服务启动失败", error=str(e))
            raise
    
    async def stop(self):
        """停止Worker服务"""
        logger.info("正在停止Worker服务...")
        
        self.is_running = False
        
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        
        await close_connections()
        
        logger.info("Worker服务已停止")
    
    async def _init_connections(self):
        """初始化数据库连接"""
        try:
            await get_mysql_pool_ro()
            await get_mysql_pool_agg()
            await get_redis_client()
            logger.info("数据库连接初始化成功")
        except Exception as e:
            logger.error("数据库连接初始化失败", error=str(e))
            raise
    
    async def _setup_jobs(self):
        """配置定时任务"""
        logger.info("配置定时任务...")
        
        # 数据聚合任务 - 每5分钟执行一次
        self.scheduler.add_job(
            self._run_aggregation_job,
            trigger=IntervalTrigger(minutes=settings.aggregation_interval_minutes),
            id="aggregation_job",
            name="数据聚合任务",
            max_instances=1,
            coalesce=True
        )
        
        # 突发频率检测 - 每1分钟执行一次
        self.scheduler.add_job(
            self._run_burst_check_job,
            trigger=IntervalTrigger(minutes=settings.burst_check_interval_minutes),
            id="burst_check_job",
            name="突发频率检测",
            max_instances=1,
            coalesce=True
        )
        
        # 共享Token检测 - 每5分钟执行一次
        self.scheduler.add_job(
            self._run_multi_user_token_check_job,
            trigger=IntervalTrigger(minutes=settings.multi_user_token_check_interval_minutes),
            id="multi_user_token_check_job",
            name="共享Token检测",
            max_instances=1,
            coalesce=True
        )
        
        # 同IP多账号检测 - 每5分钟执行一次
        self.scheduler.add_job(
            self._run_ip_many_users_check_job,
            trigger=IntervalTrigger(minutes=settings.ip_many_users_check_interval_minutes),
            id="ip_many_users_check_job",
            name="同IP多账号检测",
            max_instances=1,
            coalesce=True
        )
        
        # 超大请求检测 - 每10分钟执行一次
        self.scheduler.add_job(
            self._run_big_request_check_job,
            trigger=IntervalTrigger(minutes=settings.big_request_check_interval_minutes),
            id="big_request_check_job",
            name="超大请求检测",
            max_instances=1,
            coalesce=True
        )
        
        # 清理旧数据任务 - 每天凌晨2点执行
        self.scheduler.add_job(
            self._run_cleanup_job,
            trigger=CronTrigger(hour=2, minute=0),
            id="cleanup_job",
            name="清理旧数据",
            max_instances=1,
            coalesce=True
        )
        
        logger.info("定时任务配置完成")
    
    async def _run_aggregation_job(self):
        """执行数据聚合任务"""
        try:
            logger.info("开始执行数据聚合任务")
            await data_aggregator.aggregate_hourly_data()
            logger.info("数据聚合任务执行完成")
        except Exception as e:
            logger.error("数据聚合任务执行失败", error=str(e))
    
    async def _run_burst_check_job(self):
        """执行突发频率检测任务"""
        try:
            logger.debug("开始执行突发频率检测")
            await rule_engine.check_burst_rule()
            logger.debug("突发频率检测完成")
        except Exception as e:
            logger.error("突发频率检测失败", error=str(e))
    
    async def _run_multi_user_token_check_job(self):
        """执行共享Token检测任务"""
        try:
            logger.debug("开始执行共享Token检测")
            await rule_engine.check_multi_user_token_rule()
            logger.debug("共享Token检测完成")
        except Exception as e:
            logger.error("共享Token检测失败", error=str(e))
    
    async def _run_ip_many_users_check_job(self):
        """执行同IP多账号检测任务"""
        try:
            logger.debug("开始执行同IP多账号检测")
            await rule_engine.check_ip_many_users_rule()
            logger.debug("同IP多账号检测完成")
        except Exception as e:
            logger.error("同IP多账号检测失败", error=str(e))
    
    async def _run_big_request_check_job(self):
        """执行超大请求检测任务"""
        try:
            logger.debug("开始执行超大请求检测")
            await rule_engine.check_big_request_rule()
            logger.debug("超大请求检测完成")
        except Exception as e:
            logger.error("超大请求检测失败", error=str(e))
    
    async def _run_cleanup_job(self):
        """执行清理旧数据任务"""
        try:
            logger.info("开始执行清理旧数据任务")
            await data_aggregator.cleanup_old_aggregation_data()
            logger.info("清理旧数据任务执行完成")
        except Exception as e:
            logger.error("清理旧数据任务执行失败", error=str(e))
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            logger.info("收到停止信号", signal=signum)
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _keep_running(self):
        """保持服务运行"""
        try:
            while self.is_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到键盘中断信号")
        finally:
            await self.stop()


async def main():
    """主函数"""
    worker = WorkerApp()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error("程序异常退出", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    # 设置日志级别
    import logging
    logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
    
    # 运行Worker
    asyncio.run(main())
