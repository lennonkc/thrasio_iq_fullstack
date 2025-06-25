"""智能数据分析命令行界面"""

import asyncio
import sys
from typing import Optional

import structlog

from app.agents.data_analysis_agent import DataAnalysisAgent
from app.core.config import get_settings

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
        print("🔍 智能BigQuery数据分析系统")
        print("=" * 60)
        print("功能：")
        print("- 🗂️  浏览可用数据集")
        print("- 📊 智能生成SQL查询")
        print("- 🔐 安全查询过滤")
        print("- 📈 生成分析报告")
        print("-" * 60)
        print()

    def display_system_info(self):
        """显示系统配置信息"""
        print("系统配置：")
        print(f"📍 BigQuery项目: {self.settings.google_cloud.bigquery_project_id}")
        print(f"🤖 LLM模型: {self.settings.llm.model_name}")
        print(f"🌍 环境: {self.settings.environment}")
        print()

    async def run_interactive_analysis(self):
        """运行交互式数据分析"""
        try:
            # 创建数据分析代理
            self.agent = DataAnalysisAgent()

            print("🚀 启动数据分析工作流...")
            print()

            # 运行分析工作流
            result = await self.agent.run()

            if result["success"]:
                print("\\n✅ 数据分析完成！")
                if result.get("analysis_report"):
                    print("\\n📊 分析报告已生成")

                print(f"\\n🔑 会话ID: {result['session_id']}")

            else:
                print(f"\\n❌ 数据分析失败: {result.get('error', '未知错误')}")

        except KeyboardInterrupt:
            print("\\n\\n👋 用户中断，退出系统")
            sys.exit(0)
        except Exception as e:
            logger.error("CLI运行异常", error=str(e))
            print(f"\\n💥 系统异常: {str(e)}")
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
            print("\\n\\n👋 用户中断，退出系统")
            sys.exit(0)
        except Exception as e:
            logger.error("流式CLI运行异常", error=str(e))
            print(f"\\n💥 系统异常: {str(e)}")
            sys.exit(1)

    def display_help(self):
        """显示帮助信息"""
        print("使用说明：")
        print("1. 系统会显示所有可用的数据集")
        print("2. 请选择要分析的数据集（输入数字编号）")
        print("3. 系统会显示该数据集中的所有表格")
        print("4. 请描述您的分析需求（用自然语言）")
        print("5. 系统会自动生成并执行SQL查询")
        print("6. 最后生成智能分析报告")
        print()
        print("注意事项：")
        print("- 系统只允许读取操作，确保数据安全")
        print("- 支持复杂的数据分析需求")
        print("- 大型结果会自动存储到外部记忆")
        print()

    def confirm_start(self) -> bool:
        """确认开始分析"""
        while True:
            try:
                choice = input("是否开始数据分析？(y/n): ").strip().lower()
                if choice in ["y", "yes", "是"]:
                    return True
                elif choice in ["n", "no", "否"]:
                    return False
                else:
                    print("请输入 y/yes/是 或 n/no/否")
            except KeyboardInterrupt:
                print("\\n用户取消")
                return False


async def main(mode: str = "interactive"):
    """主函数"""
    cli = DataAnalysisCLI()

    # 显示欢迎界面
    cli.display_welcome()
    cli.display_system_info()
    cli.display_help()

    # 确认开始
    if not cli.confirm_start():
        print("👋 退出系统")
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
