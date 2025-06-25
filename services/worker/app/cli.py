"""智能数据分析命令行界面"""

import asyncio
import sys
from typing import Optional

import structlog

from app.agents.data_analysis_agent import DataAnalysisAgent
from app.core.config import get_settings
from app.core.logging import setup_logging, LogLevel

logger = structlog.get_logger()


class DataAnalysisCLI:
    """数据分析命令行界面"""

    def __init__(self):
        """初始化CLI"""
        self.settings = get_settings()
        self.agent = None
        logger.info("数据分析CLI初始化")

    def display_welcome(self):
        """显示欢迎信息"""
        print("=" * 60)
        print("🔍 Intelligent BigQuery Data Analysis System")
        print("=" * 60)
        print("Features:")
        print("- 🗂️  Browse Available Datasets")
        print("- 📊 Smart SQL Query Generation")
        print("- 🔐 Secure Query Filtering")
        print("- 📈 Generate Analysis Reports")
        print("-" * 60)
        print()

    def display_system_info(self):
        """显示系统配置信息"""
        print("System Info: ")
        print(f"📍 BigQuery Project: {self.settings.google_cloud.bigquery_project_id}")
        print(f"🤖 LLM Model: {self.settings.llm.model_name}")
        print(f"🌍 Other Enviroment: {self.settings.environment}")
        print()

    async def run_interactive_analysis(self):
        """运行交互式数据分析"""
        try:
            # 创建数据分析代理
            self.agent = DataAnalysisAgent()

            # print("🚀 启动数据分析工作流...")
            # print()

            # 运行分析工作流
            result = await self.agent.run()

            if result["success"]:
                print("\n✅ Data analysis completed!")
                if result.get("analysis_report"):
                    print("\n📊 Analysis report has been generated")

                print(f"\n🔑 Session ID: {result['session_id']}")

            else:
                print(f"\n❌ Data analysis failed: {result.get('error', 'Unknown error')}")

        except KeyboardInterrupt:
            print("\n\n👋 User interrupted, exiting system")
            sys.exit(0)
        except Exception as e:
            logger.error("CLI Running Error", error=str(e))
            print(f"\n💥 System error: {str(e)}")
            sys.exit(1)

    async def run_streaming_analysis(self):
        """运行流式数据分析（显示中间步骤）"""
        try:
            # 创建数据分析代理
            self.agent = DataAnalysisAgent()

            print("🚀 启动流式数据分析工作流...")
            print()

            # 流式运行分析工作流
            async for update in self.agent.astream():
                if "error" in update:
                    print(f"❌ 流式分析错误: {update['error']}")
                    break

                current_step = update.get("current_step", "unknown")
                print(f"📍 当前步骤: {current_step}")

                # 可以在这里添加更多的状态显示逻辑

        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出系统")
            sys.exit(0)
        except Exception as e:
            logger.error("流式CLI运行异常", error=str(e))
            print(f"\n💥 系统异常: {str(e)}")
            sys.exit(1)

    def display_help(self):
        """显示帮助信息"""
        print("Instructions:")
        print("1. System will display all available datasets")
        print("2. Please select a dataset to analyze (enter number)")
        print("3. System will show all tables in the selected dataset")
        print("4. Please describe your analysis needs (in natural language)")
        print("5. System will automatically generate and execute SQL queries")
        print("6. Finally generate intelligent analysis report")
        print()
        print("Important Notes:")
        print("- System only allows read operations to ensure data security")
        print("- Supports complex data analysis requirements")
        print("- Large results will be automatically stored in external memory")
        print()

    def confirm_start(self) -> bool:
        """确认开始分析"""
        while True:
            try:
                choice = input("Start data analysis? (y/n): ").strip().lower()
                if choice in ["y", "yes", "是"]:
                    return True
                elif choice in ["n", "no", "否"]:
                    return False
                else:
                    print("Please enter y/yes or n/no")
            except KeyboardInterrupt:
                print("\nUser cancelled")
                return False


async def main(mode: str = "interactive"):
    """主函数"""
    # 配置CLI友好的日志格式
    setup_logging(
        log_level=LogLevel.WARNING,  # 只显示警告和错误
        log_format="text",  # 使用简洁的文本格式
        quiet_cli=True,  # 启用CLI静默模式
    )

    cli = DataAnalysisCLI()

    # 显示欢迎界面
    cli.display_welcome()
    cli.display_system_info()
    cli.display_help()

    # 确认开始
    if not cli.confirm_start():
        print("👋 Exit System")
        return

    # 根据模式运行分析
    if mode == "streaming":
        await cli.run_streaming_analysis()
    else:
        await cli.run_interactive_analysis()


if __name__ == "__main__":
    # 检查命令行参数
    mode = "interactive"
    if len(sys.argv) > 1 and sys.argv[1] == "--streaming":
        mode = "streaming"

    # 运行CLI
    asyncio.run(main(mode))
