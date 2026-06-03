"""
JobTracer PDF生成模块
HTML → PDF 转换，使用 WeasyPrint
"""

import asyncio
import logging
import re
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jobtracer.pdf")

# 检查是否安装了 weasyprint
try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint not installed. PDF generation will use alternative method.")


class PDFGenerator:
    """HTML简历 → PDF转换器"""
    
    def __init__(self, font_config: str = None):
        """
        初始化 PDF 生成器
        
        Args:
            font_config: 中文字体配置（可选，使用系统默认）
        """
        self.font_config = font_config or self._get_default_font_config()
        self.font_config_obj = FontConfiguration() if WEASYPRINT_AVAILABLE else None
    
    def _get_default_font_config(self) -> str:
        """获取默认中文字体配置"""
        return """
        @font-face {
            font-family: 'ChineseFont';
            src: local('PingFang SC'), local('STSong'), local('SimSun');
        }
        body {
            font-family: 'PingFang SC', 'STSong', 'SimSun', 'Hiragino Sans GB', 
                        'Microsoft YaHei', sans-serif;
            font-size: 12px;
            line-height: 1.6;
        }
        """
    
    async def generate_pdf(
        self,
        html_path: str,
        output_path: str = None
    ) -> dict:
        """
        将 HTML 文件转换为 PDF
        
        Args:
            html_path: HTML 文件路径
            output_path: 输出 PDF 路径（默认同目录同名.pdf）
            
        Returns:
            {success, output_path, error}
        """
        html_path = Path(html_path)
        if not html_path.exists():
            return {"success": False, "error": f"HTML file not found: {html_path}"}
        
        if output_path is None:
            output_path = html_path.with_suffix(".pdf")
        else:
            output_path = Path(output_path)
        
        try:
            if WEASYPRINT_AVAILABLE:
                return await self._generate_with_weasyprint(html_path, output_path)
            else:
                return await self._generate_with_alternative(html_path, output_path)
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_with_weasyprint(
        self,
        html_path: Path,
        output_path: Path
    ) -> dict:
        """使用 WeasyPrint 生成 PDF"""
        try:
            font_css = CSS(string=self.font_config, font_config=self.font_config_obj)
            
            html_obj = HTML(filename=str(html_path))
            html_obj.write_pdf(
                str(output_path),
                stylesheets=[font_css],
                font_config=self.font_config_obj
            )
            
            logger.info(f"PDF generated: {output_path}")
            return {"success": True, "output_path": str(output_path)}
            
        except Exception as e:
            logger.error(f"WeasyPrint failed: {e}")
            return {"success": False, "error": f"WeasyPrint: {e}"}
    
    async def _generate_with_alternative(
        self,
        html_path: Path,
        output_path: Path
    ) -> dict:
        """使用 wkhtmltopdf 或系统命令生成 PDF"""
        # 尝试使用 wkhtmltopdf
        try:
            result = subprocess.run(
                ["wkhtmltopdf", str(html_path), str(output_path)],
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                return {"success": True, "output_path": str(output_path)}
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # 尝试使用浏览器打印（如果有 chrome）
        try:
            result = subprocess.run(
                [
                    "google-chrome", "--headless", "--print-to-pdf=" + str(output_path),
                    str(html_path)
                ],
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0 and output_path.exists():
                return {"success": True, "output_path": str(output_path)}
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return {
            "success": False, 
            "error": "No PDF converter available. Install WeasyPrint: pip install weasyprint"
        }
    
    async def generate_from_html_string(
        self,
        html_content: str,
        output_path: str
    ) -> dict:
        """
        直接从 HTML 字符串生成 PDF
        
        Args:
            html_content: HTML 字符串内容
            output_path: 输出 PDF 路径
            
        Returns:
            {success, output_path, error}
        """
        output_path = Path(output_path)
        
        try:
            # 创建临时 HTML 文件
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.html', 
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(html_content)
                temp_path = f.name
            
            try:
                result = await self.generate_pdf(temp_path, output_path)
                return result
            finally:
                # 清理临时文件
                Path(temp_path).unlink(missing_ok=True)
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def is_available(self) -> dict:
        """检查 PDF 生成器是否可用"""
        return {
            "weasyprint": WEASYPRINT_AVAILABLE,
            "wkhtmltopdf": self._check_command("wkhtmltopdf"),
            "chrome": self._check_command("google-chrome"),
        }
    
    def _check_command(self, cmd: str) -> bool:
        """检查命令是否可用"""
        try:
            subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False