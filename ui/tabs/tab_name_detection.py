# ui/tabs/tab_name_detection.py
import os
import json

from core.config import config
from core.file_tool import file_tool
from typing import List, Dict
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                               QLabel, QGroupBox, QProgressBar)
from PySide6.QtCore import QThread, Signal

from core.signal_bus import signal_bus
from ui.styles import get_start_button_style, get_background_gray_style, get_settings_desc_style
from ui.widgets import DragDropWidget
from ui.name_detection_result_dialog import NameDetectionResultDialog
from ui.custom_message_box import CustomMessageBox


class NameExtractionThread(QThread):
    """人名地名提取线程"""
    progress_updated = Signal(int)
    finished = Signal(list)  # 改为传递list而不是DataFrame
    error_occurred = Signal(str)

    def __init__(self, mod_folders):
        super().__init__()
        self.mod_folders = mod_folders
        self.extractor = SmartNameExtractor()

    def run(self):
        try:
            all_pairs = []
            total_folders = len(self.mod_folders)

            for i, mod_folder in enumerate(self.mod_folders):
                # 查找i18n文件夹
                i18n_folder = os.path.join(mod_folder, 'i18n')
                if not os.path.exists(i18n_folder):
                    continue

                # 处理第一种情况：直接有default.json和zh.json
                default_file = os.path.join(i18n_folder, 'default.json')
                zh_file = os.path.join(i18n_folder, 'zh.json')

                if os.path.exists(default_file) and os.path.exists(zh_file):
                    pairs = self.extractor.load_and_match_files(default_file, zh_file, mod_folder)
                    all_pairs.extend(pairs)

                # 处理第二种情况：有Default和Zh文件夹
                default_folder = os.path.join(i18n_folder, 'Default')
                zh_folder = os.path.join(i18n_folder, 'Zh')

                if os.path.exists(default_folder) and os.path.exists(zh_folder):
                    # 获取两个文件夹中的所有json文件
                    default_files = [f for f in os.listdir(default_folder) if f.endswith('.json')]
                    zh_files = [f for f in os.listdir(zh_folder) if f.endswith('.json')]

                    # 匹配相同文件名的文件
                    for filename in default_files:
                        if filename in zh_files:
                            default_path = os.path.join(default_folder, filename)
                            zh_path = os.path.join(zh_folder, filename)
                            pairs = self.extractor.load_and_match_files(default_path, zh_path, mod_folder)
                            all_pairs.extend(pairs)

                # 更新进度
                progress = int((i + 1) / total_folders * 100)
                self.progress_updated.emit(progress)

            # 过滤和去重
            if all_pairs:
                filtered_pairs = self.extractor.smart_filter_names(all_pairs, min_confidence=0.6)
                # 去重
                seen_pairs = set()
                unique_pairs = []
                for pair in filtered_pairs:
                    key = (pair['en'], pair['zh'])
                    if key not in seen_pairs:
                        seen_pairs.add(key)
                        unique_pairs.append(pair)
                self.finished.emit(unique_pairs)
            else:
                self.finished.emit([])

        except Exception as e:
            self.error_occurred.emit(str(e))


class SmartNameExtractor:
    """智能人名地名提取器"""

    def __init__(self):
        # 英文常见名字（用于基准判断）
        self.common_first_names = {
            'James', 'John', 'Robert', 'Michael', 'William',
            'David', 'Richard', 'Charles', 'Joseph', 'Thomas',
            'Christopher', 'Daniel', 'Paul', 'Mark', 'Donald',
            'George', 'Kenneth', 'Steven', 'Edward', 'Brian',
            'Mary', 'Patricia', 'Linda', 'Barbara', 'Elizabeth',
            'Jennifer', 'Maria', 'Susan', 'Margaret', 'Dorothy',
            'Lisa', 'Nancy', 'Karen', 'Betty', 'Helen',
            'Sandra', 'Donna', 'Carol', 'Ruth', 'Sharon',
            # 星露谷原版角色名
            'Abigail', 'Alex', 'Sam', 'Sebastian', 'Maru', 'Harvey',
            'Elliott', 'Leah', 'Penny', 'Haley', 'Emily', 'Shane',
            'Marnie', 'Jas', 'Vincent', 'Lewis', 'Pierre', 'Caroline',
            'Jodi', 'Kent', 'Clint', 'George', 'Evelyn',
            'Gus', 'Robin', 'Demetrius', 'Linus', 'Willy', 'Marlon',
            'Morris', 'Sandy', 'Wizard', 'Krobus', 'Dwarf',
            # SVE新增角色
            'Andy', 'Olivia', 'Victor', 'Sophia', 'Susan', 'Martin',
            'Lance', 'Magnus', 'Apples', 'Scarlett', 'Jerry', 'Elizabeth',
            # 阳莓村角色名
            'Jumana', 'Ophelia', 'Elias', 'Ezra', 'Iman', 'Maia', 'Amina',
            'Ari', 'Diala', 'Derya', 'Reihana', 'Lyenne', 'Blake', 'Nadia',
            'Ysabelle', 'Corine', 'Keahi', 'Alissa', 'Richard', 'Bert',
            'Maive', 'Pika', 'Kiarra', 'Kiwi', 'Silas', 'Miyoung', 'Chris',
            # 官方地点相关角色
            'Pam', 'Gunther', 'Mr. Qi', 'Birdie', 'Professor Snail', 'Henchman'
        }

        # 英文常见姓氏
        self.common_last_names = {
            'Smith', 'Johnson', 'Williams', 'Jones', 'Brown',
            'Davis', 'Miller', 'Wilson', 'Moore', 'Taylor',
            'Anderson', 'Thomas', 'Jackson', 'White', 'Harris',
            'Martin', 'Thompson', 'Garcia', 'Martinez', 'Robinson',
            # 星露谷姓氏
            'Muller', 'Jenkins', 'Shearwater', 'Grampleton', 'Fable',
            'Crimson', 'Highlands', 'Castle', 'Diamond', 'Iridium',
            'Treasure', 'First', 'Slash', 'Scarlett', 'Dawkins',
            # 阳莓村角色姓氏
            'Miyoung', 'Silas', 'Jumana', 'Ophelia', 'Elias', 'Ezra',
            'Iman', 'Maia', 'Amina', 'Ari', 'Diala', 'Derya', 'Reihana',
            'Lyenne', 'Blake', 'Nadia', 'Ysabelle', 'Corine', 'Keahi',
            'Alissa', 'Richard', 'Bert', 'Maive', 'Pika', 'Kiarra', 'Kiwi'
        }

        # 地名关键词
        self.location_indicators = {
            'city', 'town', 'village', 'street', 'road', 'avenue',
            'boulevard', 'lane', 'drive', 'way', 'place', 'court',
            'square', 'park', 'bridge', 'river', 'lake', 'mountain',
            'hill', 'valley', 'forest', 'beach', 'port', 'harbor',
            'airport', 'station', 'center', 'plaza', 'mall',
            # 星露谷特有地点类型
            'farm', 'valley', 'vineyard', 'grove', 'woods', 'spring',
            'quarry', 'cave', 'cavern', 'mountains', 'beach', 'desert',
            'island', 'village', 'town', 'forest', 'river', 'lake',
            'mountain', 'hill', 'valley', 'bridge', 'house', 'home',
            'room', 'cabin', 'shed', 'manor', 'shop', 'store', 'market',
            'clinic', 'hospital', 'library', 'museum', 'school', 'inn',
            'tavern', 'saloon', 'cafe', 'restaurant', 'guild', 'tower',
            'castle', 'ruins', 'temple', 'shrine', 'mine', 'mines',
            'beach', 'dock', 'pier', 'port', 'harbor', 'lighthouse',
            'farm', 'barn', 'coop', 'stable', 'greenhouse', 'garden',
            'orchard', 'meadow', 'field', 'pond', 'waterfall', 'creek'
        }

        # 组织/机构关键词
        self.organization_indicators = {
            'university', 'college', 'school', 'hospital', 'company',
            'corporation', 'inc', 'ltd', 'gmbh', 'llc', 'association',
            'foundation', 'institute', 'museum', 'library', 'hotel',
            'restaurant', 'cafe', 'bar', 'club'
        }

    def load_and_match_files(self, en_file: str, zh_file: str, source: str) -> List[Dict]:
        """加载并匹配翻译文件"""
        pairs = []

        try:
            en_data = file_tool.read_json_file(en_file)
            zh_data = file_tool.read_json_file(zh_file)

            # 如果是字典结构，直接匹配key-value
            if isinstance(en_data, dict) and isinstance(zh_data, dict):
                for key, en_value in en_data.items():
                    if key in zh_data and isinstance(en_value, str) and isinstance(zh_data[key], str):
                        zh_value = zh_data[key]

                        # 基础清洗
                        en_clean = en_value.strip()
                        zh_clean = zh_value.strip()

                        # 规则0：排除无效翻译对
                        if en_clean and zh_clean and en_clean != zh_clean:
                            # 检查英文内容是否包含中文字符
                            has_chinese_in_en = any('\u4e00' <= char <= '\u9fff' for char in en_clean)
                            # 检查中文内容是否包含英文字母
                            has_english_in_zh = any('a' <= char.lower() <= 'z' for char in zh_clean if char.isalpha())
                            # 检查中文内容是否包含符号
                            has_symbols_in_zh = any(char in '.,?!:;—()[]{}"\'`~@#$%^&*+=<>|\\/' for char in zh_clean)

                            # 如果英文包含中文或中文包含英文或符号，可能是错误的翻译对
                            if not has_chinese_in_en and not has_english_in_zh and not has_symbols_in_zh:
                                pairs.append({
                                    'key': key,
                                    'en': en_clean,
                                    'zh': zh_clean,
                                    'source': source,
                                    'file': os.path.basename(en_file),
                                    'confidence': self.calculate_confidence(en_clean, zh_clean)
                                })

            # 按置信度排序，高分在上
            pairs.sort(key=lambda x: x['confidence'], reverse=True)

        except Exception as e:
            signal_bus.log_message.emit("ERROR", f"处理文件 {en_file} 时出错: {e}", {})

        return pairs

    def calculate_confidence(self, en_text: str, zh_text: str) -> float:
        """计算为人名地名的置信度"""
        confidence = 0.0

        # 规则1：排除明显不是人名地名的情况
        en_lower = en_text.lower()

        # 排除UI相关词汇
        ui_words = {'button', 'menu', 'page', 'window', 'dialog', 'tab', 'option', 'setting', 'config', 'screen',
                    'panel', 'interface'}
        if any(word in en_lower for word in ui_words):
            return 0.0

        # 排除动作词汇
        action_words = {'click', 'press', 'select', 'choose', 'enter', 'exit', 'open', 'close', 'start', 'stop', 'save',
                        'load', 'cancel', 'confirm'}
        if any(word in en_lower for word in action_words):
            return 0.0

        # 排除描述性词汇
        desc_words = {'description', 'info', 'information', 'detail', 'details', 'help', 'tip', 'warning', 'error',
                      'message', 'text', 'content'}
        if any(word in en_lower for word in desc_words):
            return 0.0

        # 排除中文UI词汇
        chinese_ui = {'按钮', '菜单', '页面', '窗口', '对话框', '选项', '设置', '配置', '屏幕', '面板', '界面', '点击',
                      '选择', '进入', '退出', '打开', '关闭', '开始', '停止', '保存', '加载', '取消', '确认', '描述',
                      '信息', '详情', '帮助', '提示', '警告', '错误', '消息', '文本', '内容'}
        if any(word in zh_text for word in chinese_ui):
            return 0.0

        # 规则2：文本长度检查
        if len(en_text) > 30 or len(zh_text) > 20:  # 太长的文本不太可能是人名地名
            return 0.0

        if len(en_text) < 2 or len(zh_text) < 1:  # 太短的文本
            return 0.0

        # 规则3：检查是否为句子（包含标点符号）
        if any(punct in en_text for punct in {'.', '?', '!', ',', ';', ':', '-', '—'}):
            return 0.0

        # 规则4：检查单词数量
        words = en_text.split()
        if len(words) > 4:  # 超过4个单词不太可能是人名地名
            return 0.0

        # 规则5：首字母大写检查（人名地名特征）
        if len(words) <= 3 and all(w and w[0].isupper() for w in words):
            confidence += 0.4

        # 规则6：是否包含常见名字
        for word in words:
            if word in self.common_first_names:
                confidence += 0.5
            if word in self.common_last_names:
                confidence += 0.4

        # 规则7：是否包含地名关键词
        for indicator in self.location_indicators:
            if f" {indicator}" in en_lower or en_lower.endswith(indicator) or en_lower.startswith(indicator):
                confidence += 0.6

        # 规则8：中文特征检查
        # 人名特征：2-4个字，且不包含常见词汇
        if 2 <= len(zh_text) <= 4:
            # 检查是否包含常见的中文名字用字
            common_chars = {
                # 星露谷角色中文名常用字
                '阿', '比', '盖', '尔', '亚', '历', '山', '大', '萨', '姆', '斯', '巴', '蒂', '安', '马', '鲁', '艾',
                '利', '欧', '特', '莉', '潘', '妮', '海', '莉', '米', '肖', '恩', '玛', '贾', '斯', '文', '刘', '易',
                '皮', '埃', '卡', '洛', '琳', '肯', '特', '纳', '威', '冈', '瑟', '克', '罗', '布', '桑', '迪', '巫',
                '矮', '人', '莫', '里', '奥', '维', '克', '多', '索', '菲', '苏', '珊', '丁', '兰', '格', '努', '苹',
                '果', '嘉', '瑞', '伊', '莎', '白',
                # 阳莓村相关角色字
                '茱', '玛', '娜', '奥', '菲', '莉', '亚', '伊', '莱', '亚', '斯', '埃', '兹', '拉', '美', '永', '赛',
                '拉', '黛', '亚', '德', '莉', '娅', '莱', '茵', '布', '雷', '克', '雷', '哈', '纳', '艾', '米', '娜',
                '阿', '丽', '斯', '塔', '西', '亚', '科', '林', '基', '阿', '拉', '皮', '卡', '基', '维', '基', '猕',
                '猴', '桃'
            }
            if any(char in zh_text for char in common_chars):
                confidence += 0.3

            # 地名特征：包含山、水、城、镇等
            location_chars = {
                # 基础地名用字
                '山', '水', '河', '湖', '海', '城', '镇', '村', '庄', '街', '路', '桥', '门', '楼', '阁', '寺', '庙',
                '塔', '园', '林', '谷', '峡', '湾', '港', '洲', '岛',
                # 星露谷特有地点用字
                '农', '场', '田', '地', '野', '原', '丘', '陵', '坡', '岩', '石', '洞', '穴', '窟', '溪', '泉', '瀑',
                '布', '池', '塘', '泽', '沼', '滩', '岸', '边', '角', '嘴', '口', '关', '隘', '道', '径', '巷', '弄',
                '坊', '里', '区', '域', '界', '境', '方', '处', '所', '点', '站', '场', '院', '堂', '馆', '台', '榭',
                '亭', '轩', '斋', '室', '庐', '舍', '居', '宅', '府', '邸', '墅', '苑', '圃', '畦', '垄', '亩', '町',
                '畈', '州', '县', '郡', '市', '乡', '寨', '堡', '坞', '营', '屯', '集', '墟', '铺', '店', '作', '厂',
                '矿', '澳', '岬', '屿', '礁', '渚', '汀', '浦',
                # 官方地点中文名
                '鹈', '鹕', '星', '露', '谷', '枫', '叶', '沙', '漠', '姜', '岛', '祖', '城', '雾', '呜', '山', '峰',
                '矿', '山', '隧', '道', '废', '弃', '矿', '山', '矿', '洞', '头', '骨', '洞', '穴', '怪', '物', '巢',
                '穴', '海', '滩', '码', '头', '滴', '潮', '池', '人', '鱼', '池', '岛', '西', '码', '头', '岛', '南',
                '码', '头', '岛', '东', '码', '头', '岛', '北', '码', '头', '火', '山', '口', '龙', '穴', '巫', '师',
                '塔', '下', '水', '道', '铁', '匠', '铺', '渔', '夫', '小', '屋', '冒', '险', '家', '公', '会', '博',
                '物', '馆', '图', '书', '馆', '皮', '埃', '尔', '杂', '货', '店', '乔', '贾', '超', '市', '星', '之',
                '果', '滴', '酒', '馆', '医', '疗', '站', '社', '区', '中', '心',
                # SVE地点中文名
                '极', '光', '葡', '萄', '园', '魔', '法', '树', '林', '海', '鸥', '桥', '爷', '爷', '小', '屋', '农',
                '场', '入', '口', '温', '泉', '农', '场', '采', '石', '场', '硬', '木', '林', '地', '农', '场', '洞',
                '穴', '格', '兰', '普', '顿', '郊', '区', '旅', '行', '商', '人', '科', '罗', '布', '斯', '商', '店',
                '詹', '金', '斯', '庄', '园', '山', '姆', '的', '家', '冈', '瑟', '的', '房', '间', '艾', '米', '丽',
                '海', '莉', '的', '家', '庄', '园', '刘', '易', '斯', '的', '家', '潘', '妮', '的', '家', '花', '园',
                '玛', '妮', '的', '小', '屋', '莉', '亚', '的', '小', '屋', '安', '迪', '的', '农', '场', '苹', '果',
                '的', '房', '间', '熊', '的', '洞', '穴', '祝', '尼', '魔', '森', '林', '祝', '尼', '魔', '村', '精',
                '灵', '泉', '下', '水', '道', '格', '栅', '索', '菲', '娅', '的', '葡', '萄', '园', '索', '菲', '娅',
                '订', '单', '簿', '莱', '纳', '斯', '的', '帐', '篷', '公', '路', '隧', '道', '黄', '金', '镰', '刀',
                '苏', '珊', '的', '农', '场', '火', '车', '月', '台', '顶', '峰', '高', '地', '洞', '穴', '艾', '利',
                '欧', '特', '的', '小', '屋', '沙', '漠', '龙', '骨', '架', '城', '堡', '村', '前', '哨', '站', '绯',
                '红', '荒', '地', '铱', '矿', '场', '宝', '藏', '洞', '穴', '寓', '言', '礁', '矿', '车', '利', '刃',
                '之', '首', '公', '会', '斯', '嘉', '丽', '的', '房', '子', '高', '地', '前', '哨', '站', '法', '师',
                '地', '下', '室', '钻', '石', '洞', '穴', '格', '兰', '普', '顿', '郊', '区', '火', '车', '站',
                # 阳莓村地点中文名
                '阳', '莓', '村', '东', '斯', '卡', '普', '里', '奇', '赛', '德', '暮', '色', '节', '羽', '毛', '宁',
                '静', '旅', '馆', '猫', '咖', '啡', '晶', '洞', '秘', '密', '森', '林', '日', '晒', '林', '地', '古',
                '老', '树', '林', '喷', '泉', '区', '域', '停', '车', '场', '废', '弃', '房', '屋', '破', '损', '谷',
                '仓', '彩', '虹', '餐', '厅', '博', '物', '馆', '矿', '井', '底', '部', '山', '路', '捷', '径', '公',
                '寓', '铁', '匠', '铺', '花', '店', '服', '装', '店'
            }
            if any(char in zh_text for char in location_chars):
                confidence += 0.4

        # 规则9：检查是否为纯字母（专有名词特征）
        if en_text.replace(' ', '').replace("'", "").replace("-", "").isalpha():
            if not en_text.islower():  # 不是全小写
                confidence += 0.3

        # 规则10：特殊模式检查
        # 如 "Mr. Smith", "Dr. John" 等
        if en_text.startswith(('Mr ', 'Mrs ', 'Ms ', 'Dr ', 'Prof ')):
            confidence += 0.5

        # 规则11：中英文对应关系检查
        # 如果英文是单个单词，中文应该是2-4个字
        if len(words) == 1 and 2 <= len(zh_text) <= 4:
            confidence += 0.2

        # 规则12：星露谷特有的地名模式
        stardew_patterns = {
            # 原版地点
            'pelican', 'town', 'stardew', 'valley', 'farm', 'beach', 'mountain', 'forest',
            'river', 'lake', 'ocean', 'desert', 'calico', 'ginger', 'island', 'zuzu', 'city',
            'bus', 'stop', 'community', 'center', 'general', 'store',
            'clinic', 'hospital', 'joja', 'mart', 'saloon', 'blacksmith', 'fish', 'shop',
            'museum', 'library', 'adventurer', 'guild', 'wizard', 'tower', 'sewer',
            'quarry', 'secret', 'woods', 'mines', 'skull', 'cavern', 'mutant', 'bug', 'lair',
            'beach', 'bridge', 'tide', 'pool', 'mermaid', 'show', 'island', 'north',
            'south', 'west', 'east', 'duggie', 'cove', 'leah', 'cottage', 'pam', 'house',
            'marnie', 'ranch', 'cindersap', 'forest', 'robin', 'house', 'carpenter', 'shop',
            'river', 'road', 'mountain', 'lake', 'railroad',
            'hike', 'trail', 'old', 'town', 'marlon', 'room', 'wizard', 'basement',
            # SVE特有地点
            'aurora', 'vineyard', 'enchanted', 'grove', 'shearwater', 'bridge', 'grandpa', 'shed',
            'farm', 'entrance', 'hotspring', 'farm', 'quarry', 'hardwood', 'glade', 'farm',
            'cave', 'grampleton', 'suburbs', 'travelling', 'merchant', 'krobus', 'shop',
            'jenkins', 'manor', 'sam', 'home', 'gunther', 'room', 'emily', 'haley', 'home',
            'manor', 'muller', 'residence', 'alex', 'home', 'penny', 'home', 'garden',
            'marnie', 'shed', 'leah', 'cabin', 'andy', 'farm', 'apple', 'room', 'bear',
            'cave', 'junimo', 'woods', 'junimo', 'village', 'sprite', 'spring', 'sewer',
            'grate', 'sophia', 'vineyard', 'sophia', 'ledger', 'linus', 'tent', 'road',
            'tunnel', 'golden', 'scythe', 'susan', 'farm', 'train', 'platform', 'summit',
            'highlands', 'cavern', 'elliott', 'cabin', 'desert', 'dragon', 'skeleton',
            'castle', 'village', 'outpost', 'crimson', 'badlands', 'iridium', 'quarry',
            'treasure', 'cave', 'fable', 'reef', 'rail', 'cart', 'first', 'slash', 'guild',
            'scarlett', 'highlands', 'outpost', 'wizards', 'basement', 'diamond',
            'cavern', 'suburbs', 'train', 'station',
            # 阳莓村地点
            'sunberry', 'village', 'east', 'scarpe', 'richside', 'twilight', 'festival',
            'feather', 'warp', 'totem', 'serenity', 'inn', 'd&d', 'cat', 'cafe', 'crystal',
            'cave', 'secret', 'forest', 'glade', 'ancient', 'grove', 'fountain', 'area',
            'car', 'park', 'abandoned', 'house', 'broken', 'barn', 'diner', 'rainbow',
            'museum', 'mines', 'bottom', 'mountain', 'road', 'shortcut', 'sunkissed',
            'apartment', 'blacksmith', 'flower', 'shop', 'clothing',
            # 其他mod地点
            'ginger', 'island', 'west', 'pirate', 'cove', 'duggie', 'volcano', 'dungeon',
            'paradise', 'warp', 'totem', 'qi', 'walnut', 'room', 'frog', 'pond'
        }
        if any(pattern in en_lower for pattern in stardew_patterns):
            confidence += 0.3

        # 规则13：降低置信度的情况
        # 如果包含数字，很可能是编号而不是名称
        if any(char.isdigit() for char in en_text):
            confidence -= 0.3

        # 如果是全大写，可能是缩写
        if en_text.isupper() and len(en_text) > 2:
            confidence -= 0.2

        return max(0.0, min(confidence, 1.0))

    def smart_filter_names(self, pairs: List[Dict], min_confidence: float = 0.5) -> List[Dict]:
        """智能过滤人名地名"""
        filtered_pairs = []

        # 加载现有术语表
        existing_terms = self.load_existing_terminology()

        for pair in pairs:
            en = pair['en']
            zh = pair['zh']
            confidence = pair['confidence']

            # 应用置信度过滤
            if confidence < min_confidence:
                continue

            # 过滤已存在于术语表的条目
            if en in existing_terms:
                continue

            # 进一步智能过滤
            # 排除明显不是人名的
            if len(en) > 50 or len(zh) > 50:  # 太长的文本
                continue

            if any(x in en.lower() for x in ['button', 'menu', 'page', 'window', 'dialog']):
                continue

            if any(x in zh for x in ['按钮', '菜单', '页面', '窗口', '对话框']):
                continue

            # 检查是否可能为句子
            if en.count(' ') > 5 or '.' in en or '?' in en or '!' in en:
                continue

            filtered_pairs.append(pair)

        return filtered_pairs

    def load_existing_terminology(self) -> set:
        """加载现有术语表"""
        # 使用Python项目的resources目录
        python_project_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        terminology_path = os.path.join(python_project_path, "resources", "terminology.json")

        existing_terms = set()
        if os.path.exists(terminology_path):
            try:
                with open(terminology_path, 'r', encoding='utf-8') as f:
                    terminology = json.load(f)
                existing_terms = set(terminology.keys())
            except Exception as e:
                signal_bus.log_message.emit("ERROR", f"加载术语表失败: {e}", {})

        return existing_terms


class TabNameDetection(QWidget):
    """人名地名检测标签页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_manager = None
        self.mod_folders = []
        self.extraction_thread = None
        self.results_list = []  # 改用list存储结果
        self.init_ui()

    def set_project_manager(self, project_manager):
        """设置项目管理器"""
        self.project_manager = project_manager

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 添加使用说明
        help_text = QLabel(
            "使用说明：\n"
            "1. 拖放包含 i18n 文件夹的 mod 文件夹（可多选）\n"
            "2. 点击开始检测按钮提取人名地名\n"
            "3. 查看检测结果并可导出或追加到术语表\n"
            "4. 提取算法没有依赖成熟项目，所以不是太准，需要人工筛选\n"
            "5. 若有误添加的可打开全局设置-术语表 进行修改，也可导出到json，用记事本快速修改后导入覆盖"
        )
        help_text.setStyleSheet(get_settings_desc_style(config.theme))
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # 步骤1: 拖放mod文件夹
        step1_group = QGroupBox("步骤1: 拖放包含 i18n 文件夹的 mod 文件夹")
        step1_layout = QVBoxLayout(step1_group)

        self.name_mod_widget = DragDropWidget(
            "拖放包含 i18n 文件夹的 mod 文件夹到这里（可多选）",
            accept_folders=True,
            accept_files=False,
            multi_select=True
        )
        self.name_mod_widget.sender_id = 'name_detection_mod'
        signal_bus.foldersDropped.connect(self.on_mod_folders_dropped)
        step1_layout.addWidget(self.name_mod_widget)

        # 显示已选择的文件夹
        self.selected_folders_label = QLabel("已选择: 0 个mod文件夹")
        self.selected_folders_label.setStyleSheet(get_background_gray_style(config.theme))
        step1_layout.addWidget(self.selected_folders_label)

        layout.addWidget(step1_group)

        # 步骤2: 开始检测
        step2_group = QGroupBox("步骤2: 开始检测")
        step2_layout = QVBoxLayout(step2_group)

        self.detect_btn = QPushButton("🔍 开始检测人名地名")
        self.detect_btn.clicked.connect(self.start_detection)
        self.detect_btn.setStyleSheet(get_start_button_style(config.theme))
        step2_layout.addWidget(self.detect_btn)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        step2_layout.addWidget(self.progress_bar)

        layout.addWidget(step2_group)

        # 步骤3: 结果展示
        step3_group = QGroupBox("步骤3: 检测结果")
        step3_layout = QVBoxLayout(step3_group)

        # 结果统计
        self.results_label = QLabel("等待检测...")
        self.results_label.setStyleSheet(get_background_gray_style(config.theme))
        step3_layout.addWidget(self.results_label)

        # 查看结果按钮
        self.view_results_btn = QPushButton("📋 查看检测结果")
        self.view_results_btn.clicked.connect(self.view_results)
        self.view_results_btn.setStyleSheet(get_start_button_style(config.theme))
        self.view_results_btn.setEnabled(False)
        step3_layout.addWidget(self.view_results_btn)

        layout.addWidget(step3_group)

        layout.addStretch()
        self.setLayout(layout)

    def on_mod_folders_dropped(self, paths, sender_id=None):
        """处理mod文件夹拖放"""
        if sender_id != 'name_detection_mod':
            return

        if paths:
            self.mod_folders = paths
            self.selected_folders_label.setText(f"已选择: {len(paths)} 个mod文件夹")

            # 显示前几个文件夹路径
            preview_text = "已选择的mod文件夹:\n"
            for i, path in enumerate(paths[:3]):  # 显示前3个
                folder_name = os.path.basename(path)
                preview_text += f"  {i + 1}. {folder_name}\n"
            if len(paths) > 3:
                preview_text += f"  ... 还有 {len(paths) - 3} 个文件夹"

            self.selected_folders_label.setToolTip(preview_text)
            signal_bus.log_message.emit("INFO", f"已选择 {len(paths)} 个mod文件夹", {})

    def start_detection(self):
        """开始检测人名地名"""
        from ui.custom_message_box import CustomMessageBox

        # 检查1: 是否选择了文件夹
        if not self.mod_folders:
            CustomMessageBox.warning(self, "警告", "请先选择mod文件夹")
            return

        # 检查2: 是否有当前项目
        if not (self.project_manager and self.project_manager.current_project):
            CustomMessageBox.warning(self, "警告", "请先打开或创建一个项目")
            return

        # 禁用按钮并显示进度条
        self.detect_btn.setEnabled(False)
        self.view_results_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # 清空结果
        self.results_list = []
        self.results_label.setText("正在检测...")

        # 启动提取线程
        self.extraction_thread = NameExtractionThread(self.mod_folders)
        self.extraction_thread.progress_updated.connect(self.progress_bar.setValue)
        self.extraction_thread.finished.connect(self.on_extraction_finished)
        self.extraction_thread.error_occurred.connect(self.on_extraction_error)
        self.extraction_thread.start()

        signal_bus.log_message.emit("INFO", f"开始检测 {len(self.mod_folders)} 个mod文件夹的人名地名", {})

    def on_extraction_finished(self, results_list):
        """提取完成处理"""
        self.results_list = results_list
        self.progress_bar.setVisible(False)
        self.detect_btn.setEnabled(True)

        if results_list:
            # 更新统计信息
            self.results_label.setText(f"检测完成！共找到 {len(results_list)} 个人名地名")
            # 启用查看结果按钮
            self.view_results_btn.setEnabled(True)

            signal_bus.log_message.emit("INFO", f"检测完成，共找到 {len(results_list)} 个人名地名", {})
        else:
            self.results_label.setText("未检测到人名地名")
            CustomMessageBox.information(self, "提示", "未检测到人名地名")
            signal_bus.log_message.emit("INFO", "检测完成，未找到人名地名", {})

    def on_extraction_error(self, error_msg):
        """提取错误处理"""
        self.progress_bar.setVisible(False)
        self.detect_btn.setEnabled(True)
        self.results_label.setText("检测失败")
        CustomMessageBox.critical(self, "错误", f"检测过程中发生错误：{error_msg}")
        signal_bus.log_message.emit("ERROR", f"人名地名检测失败：{error_msg}", {})

    def view_results(self):
        """查看检测结果"""
        if not self.results_list:
            CustomMessageBox.warning(self, "警告", "没有可查看的结果")
            return

        # 打开结果对话框
        dialog = NameDetectionResultDialog(self.results_list, self.project_manager, self)
        dialog.exec()