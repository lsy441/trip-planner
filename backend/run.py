"""启动脚本"""

# Windows 下强制 UTF-8 输出，Emoji 完美显示 ✅
import sys
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import uvicorn
from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    
    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower()
    )

