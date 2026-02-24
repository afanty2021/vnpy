"""
VeighNa Web监控启动脚本

用于启动Web监控服务器
"""

import argparse
import logging
import sys
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("web_monitor.log"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="VeighNa Web监控服务器")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="监听地址",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="监听端口",
    )
    parser.add_argument(
        "--rpc-rep",
        type=str,
        default="tcp://127.0.0.1:2014",
        help="RPC请求地址",
    )
    parser.add_argument(
        "--rpc-pub",
        type=str,
        default="tcp://127.0.0.1:4102",
        help="RPC发布地址",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="自动重载",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="日志级别",
    )

    args = parser.parse_args()

    # 导入模块
    try:
        import uvicorn
        from vnpy_china_monitor.web.config import WebMonitorConfig, set_config
        from vnpy_china_monitor.web.server import create_web_app
    except ImportError as e:
        logger.error(f"导入模块失败: {e}")
        logger.error("请确保已安装所需依赖: pip install -r vnpy_china_monitor/requirements.txt")
        sys.exit(1)

    # 设置配置
    config = WebMonitorConfig()
    config.web.host = args.host
    config.web.port = args.port
    config.rpc.rep_address = args.rpc_rep
    config.rpc.pub_address = args.rpc_pub
    config.web.reload = args.reload
    config.web.log_level = args.log_level.upper()

    set_config(config)

    # 创建应用
    app = create_web_app()

    # 启动服务器
    logger.info(f"启动Web监控服务器: {args.host}:{args.port}")
    logger.info(f"RPC地址: {args.rpc_rep}, {args.rpc_pub}")
    logger.info(f"API文档: http://{args.host}:{args.port}/docs")

    try:
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level,
        )
    except KeyboardInterrupt:
        logger.info("服务器已停止")
    except Exception as e:
        logger.error(f"服务器错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
