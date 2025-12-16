# core/variable_protector.py
import re
import itertools
from typing import Tuple, Dict

class VariableProtector:
    """变量保护器，使用全局短标记"""
    
    # 类级别的全局映射，确保所有实例共享
    _global_var_map = {}  # 原始变量 -> 全局标记
    _marker_to_var = {}  # 全局标记 -> 原始变量（反向映射）
    _marker_gen = None  # 全局标记生成器
    _marker_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    def __init__(self):
        # 星露谷对话格式的变量正则表达式（按6,5,1,2,3,7,4顺序，已优化）
        self.variable_patterns = [
            # 6. 复杂命令（较少使用）
            r'\$[cq]\s+[^#]*#',  # 合并 $c 和 $q 命令
            r'\$[rp]\s+[^#]*#',  # 合并 $r 和 $p 命令
            r'\$d\s+[^#]*#',    # 世界状态 $d kent
            
            # 5. 特殊格式
            r'\$\{[^}]*\^[^}]*\}',  # 性别开关 ${male^female}
            r'\{\{[^}]*\}\}',       # {{...}}
            r'\$\{[^}]*\}',        # ${...}}
            r'\|\||\*|\^',          # 合并特殊字符：||, *, ^
            
            # 1. 基本对话命令（最常用的）
            r'#\$[be]#',  # 合并 #$e# 和 #$b#
            r'\$[be]',    # 合并 $e 和 $b
            
            # 2. 肖像命令（情绪表达）
            r'\$[hsluak]',  # 合并所有字母肖像命令：h,s,l,u,a,k
            r'\$\d+',      # 数字肖像
            
            # 3. 物品给予
            r'\[[^\]]+\+?]',  # 合并 [item...] 和 [item...+]
            
            # 7. 替换命令（占位符）- 优化分组
            # 特殊字符
            r'@',
            # %变量 - 只保护特定的系统变量，不保护NPC名字
            r'%fork|%item.*?%%',  # 特殊%变量
            # 明确列出需要保护的系统变量
            r'%spouse|%name|%time|%band|%book|%place|%adj|%noun',  # 长变量名
            r'%kid1|%kid2|%pet|%farm',  # 中等变量名
            r'%firstnameletter',   # 特殊情况
            r'%favorite',         # 特殊情况
            r'%',  # 保护%符号本身，防止AI误解为特殊变量（放在最后确保先匹配完整变量名）
            
            # 4. 保留的原有模式（向后兼容）
            r'\$\{\{[^{}]*?\}\}\s*#',  # ${...} #
            r'\$\{\{[^{}]*?\}}#',  # ${...}#
            r'\$[A-Za-z0-9_]+',  # 其他$变量（增加下划线支持）
        ]
        
        self.compiled_pattern = re.compile('|'.join(self.variable_patterns))
        self.pattern_string = '|'.join(self.variable_patterns)
        
        # 初始化全局标记生成器（如果还没有）
        if VariableProtector._marker_gen is None:
            VariableProtector._marker_gen = self._marker_generator()

    @classmethod
    def _marker_generator(cls):
        """生成全局标记：AAA, AAB, ...（统一3位格式）"""
        # 直接从3位开始，确保所有标记都是3位
        length = 3
        while True:
            for chars in itertools.product(cls._marker_chars, repeat=length):
                yield '<VAR>' + ''.join(chars) + '</VAR>'  # 使用XML风格的标记
            length += 1

    def protect_variables(self, text: str) -> Tuple[str, Dict[str, str]]:
        """保护文本中的变量，使用全局短标记"""
        if not text or not text.strip():
            return text, {}

        # 查找所有变量
        variables = []
        for match in self.compiled_pattern.finditer(text):
            variables.append(match.group(0))
        # message = f"输入文本: {text[:50]}...  找到变量: {variables}" if len(text) > 50 else f"输入文本: {text}  找到变量: {variables}"
        # signal_bus.log_message.emit("INFO", message,{})

        # 为每个变量分配/获取全局标记
        text_var_map = {}
        for var in variables:
            if var not in VariableProtector._global_var_map:
                marker = next(VariableProtector._marker_gen)
                VariableProtector._global_var_map[var] = marker
                VariableProtector._marker_to_var[marker] = var

            marker = VariableProtector._global_var_map[var]
            text_var_map[marker] = var

        # 构建保护后的文本（直接使用全局标记）
        protected_text = text
        for var in variables:
            marker = VariableProtector._global_var_map[var]
            # 只替换第一个匹配项，避免重复替换
            protected_text = protected_text.replace(var, marker, 1)

        return protected_text, text_var_map

    def restore_variables(self, protected_text: str) -> str:
        """恢复保护文本中的变量"""
        if not protected_text:
            return protected_text

        restored_text = protected_text
        # 按标记长度降序排序，避免部分匹配问题
        sorted_markers = sorted(VariableProtector._marker_to_var.items(),
                                key=lambda x: len(x[0]),
                                reverse=True)

        for marker, var in sorted_markers:
            restored_text = restored_text.replace(marker, var)

        return restored_text

    def count_variables_in_text(self, text):
        """统计文本中的变量数量"""
        if not text:
            return 0

        total_vars = 0
        for pattern in self.variable_patterns:
            matches = list(re.finditer(pattern, text))
            total_vars += len(matches)
        return total_vars

    @classmethod
    def reset_global(cls):
        """重置全局映射"""
        cls._global_var_map.clear()
        cls._marker_to_var.clear()
        cls._marker_gen = cls._marker_generator()

    def get_pattern_string(self):
        """获取变量re规则"""
        return self.pattern_string

