# -*- coding: utf-8 -*-
"""强制设置UTF-8编码，解决Windows终端Emoji显示问题"""
import sys
import io

if sys.platform == "win32":
    # 强制设置stdout和stderr为UTF-8编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    # 设置默认编码
    import locale
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'
