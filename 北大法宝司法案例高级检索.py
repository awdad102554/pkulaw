#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北大法宝司法案例高级检索 - 交互式筛选版
流程：登录 → 跳转 → 进入高级检索 → 用户选择法院级别 & 输入案由 → 设置条件 → 保存HTML

使用方法:
    python 北大法宝司法案例高级检索.py
"""

import re
import time
import random
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from 北大法宝图书馆自动爬虫 import PkulawCrawler, print_info, print_success, print_error, print_step, print_warning


class CaseAdvancedSearchCrawler(PkulawCrawler):
    def wait(self, min_sec=1, max_sec=2):
        sec = random.uniform(min_sec, max_sec)
        print_info(f"等待 {sec:.1f} 秒...")
        time.sleep(sec)

    def ensure_dropdown_closed(self, timeout=5):
        """确保所有 el-select 下拉框已关闭，防止遮挡后续操作"""
        start = time.time()
        while time.time() - start < timeout:
            # 检查是否还有打开的下拉框（使用 getComputedStyle 更可靠）
            check = self.pkulaw_page.run_js('''
                (function(){
                    var dropdowns = document.querySelectorAll('.el-select-dropdown.el-popper');
                    var openCount = 0;
                    for (var i=0; i<dropdowns.length; i++){
                        var style = window.getComputedStyle(dropdowns[i]);
                        if (style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0'){
                            openCount++;
                        }
                    }
                    return openCount;
                })()
            ''', as_expr=True)
            if check == 0:
                return True

            # 方法1: 点击空白处
            self.pkulaw_page.run_js('''
                var blankArea = document.querySelector('.el-main') || document.querySelector('.main-content') || document.querySelector('.fb-content') || document.body;
                if (blankArea) blankArea.click();
            ''', as_expr=True)
            time.sleep(0.5)

            # 方法2: 按 Escape 键
            self.pkulaw_page.run_js('''
                document.dispatchEvent(new KeyboardEvent('keydown', {
                    key: 'Escape', code: 'Escape', keyCode: 27,
                    which: 27, bubbles: true, cancelable: true
                }));
            ''', as_expr=True)
            time.sleep(0.5)

            # 方法3: 找到当前打开着的 el-select 组件，通过 Vue 实例强制关闭
            self.pkulaw_page.run_js('''
                (function(){
                    var selects = document.querySelectorAll('.el-select');
                    for (var i=0; i<selects.length; i++){
                        var vue = selects[i].__vue__;
                        if (vue && vue.visible){
                            vue.visible = false;
                            if (typeof vue.handleClose === 'function') vue.handleClose();
                        }
                    }
                })()
            ''', as_expr=True)
            time.sleep(0.5)

        # 最终检查
        final = self.pkulaw_page.run_js('''
            (function(){
                var dropdowns = document.querySelectorAll('.el-select-dropdown.el-popper');
                for (var i=0; i<dropdowns.length; i++){
                    var style = window.getComputedStyle(dropdowns[i]);
                    if (style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0'){
                        return 'still_open';
                    }
                }
                return 'closed';
            })()
        ''', as_expr=True)
        if final == 'closed':
            return True
        print_warning("下拉框可能未完全关闭")
        return False

    def goto_advanced_case(self):
        """进入司法案例高级检索页面"""
        print_step(3, "进入司法案例高级检索")
        try:
            base = self._get_base_url()
            url = base + '/advanced/case/pfnl'
            print_info(f"访问: {url}")
            self.pkulaw_page.get(url)
            time.sleep(5)
            print_info(f"当前页面: {self.pkulaw_page.title}")

            # 轮询等待页面关键异步元素加载（最多30秒）
            print_info("等待页面异步元素加载...")
            for i in range(30):
                ready = self.pkulaw_page.run_js('''
                    (function(){
                        var inputs = document.querySelectorAll('input');
                        for (var i=0; i<inputs.length; i++) {
                            var ph = inputs[i].getAttribute('placeholder') || '';
                            if (ph.indexOf('最多5个词语') !== -1) return 'ready';
                        }
                        var spans = document.querySelectorAll('span');
                        for (var i=0; i<spans.length; i++) {
                            if (spans[i].textContent.trim() === '法院级别') return 'ready';
                        }
                        return '';
                    })()
                ''', as_expr=True)
                if ready:
                    print_info(f"页面元素已就绪 (等待了 {i+1} 秒)")
                    break
                time.sleep(1)
            else:
                print_warning("页面元素加载超时，继续执行...")
            return True
        except Exception as e:
            print_error(f"进入高级检索页面失败: {e}")
            return False

    def _get_base_url(self):
        current_url = self.pkulaw_page.url
        match = re.match(r'(https?://[^/]+)', current_url)
        return match.group(1) if match else current_url.rstrip('/')

    def click_add_filter(self, filter_name, max_retry=3):
        """点击左侧 '+筛选条件' 按钮，支持多个class容器，带重试"""
        print_info(f"点击'+{filter_name}'...")
        try:
            page = self.pkulaw_page

            for attempt in range(max_retry):
                clicked = False

                # 策略1: DP ele查找并点击
                for selector in [
                    f'css:.noShow-tree-content .content span:text({filter_name})',
                    f'css:.left-tree-content .content span:text({filter_name})',
                    f'css:.left-tree-content span:text({filter_name})',
                    f'text:{filter_name}',
                ]:
                    try:
                        btn = page.ele(selector, timeout=2)
                        if btn:
                            el = btn
                            for _ in range(3):
                                if not el:
                                    break
                                cls = el.attr('class') or ''
                                if 'content' in cls:
                                    el.run_js('this.click()')
                                    clicked = True
                                    break
                                el = el.parent()
                            if not clicked:
                                btn.run_js('this.click()')
                                clicked = True
                            break
                    except:
                        continue

                # 策略2: JS遍历多个容器查找
                if not clicked:
                    clicked = page.run_js(f'''
                        var containers = [
                            '.noShow-tree-content',
                            '.left-tree-content',
                            '.el-tree-node__children',
                            '.el-tree'
                        ];
                        for (var c=0; c<containers.length; c++){{
                            var contents = document.querySelectorAll(containers[c] + ' .content');
                            if (contents.length === 0){{
                                contents = document.querySelectorAll(containers[c] + ' .el-tree-node__content');
                            }}
                            if (contents.length === 0){{
                                contents = document.querySelectorAll(containers[c] + ' .custom-tree-node');
                            }}
                            for (var i=0; i<contents.length; i++){{
                                var spans = contents[i].querySelectorAll("span, .label");
                                var hasIcon = false, hasText = false;
                                for (var j=0; j<spans.length; j++){{
                                    var cls = spans[j].className || '';
                                    var txt = spans[j].textContent.trim();
                                    if (cls.indexOf("add_icon") !== -1 || cls.indexOf("el-icon-plus") !== -1) hasIcon = true;
                                    if (txt === "{filter_name}" || txt.indexOf("{filter_name}") !== -1) hasText = true;
                                }}
                                if (hasIcon && hasText){{
                                    contents[i].click();
                                    return true;
                                }}
                            }}
                        }}
                        var allSpans = document.querySelectorAll('span');
                        for (var i=0; i<allSpans.length; i++){{
                            if (allSpans[i].textContent.trim() === "{filter_name}"){{
                                var p = allSpans[i].parentElement;
                                for (var k=0; k<5 && p; k++){{
                                    var pc = p.className || '';
                                    if (pc.indexOf('content') !== -1 || pc.indexOf('el-tree-node__content') !== -1 || pc.indexOf('custom-tree-node') !== -1){{
                                        p.click();
                                        return true;
                                    }}
                                    p = p.parentElement;
                                }}
                            }}
                        }}
                        return false;
                    ''')

                if clicked:
                    print_info(f"'+{filter_name}' 点击完成")
                    time.sleep(0.5)
                    return True

                if attempt < max_retry - 1:
                    print_warning(f"未找到'+{filter_name}'，第{attempt+1}次重试...")
                    time.sleep(2)

            print_error(f"未找到'+{filter_name}'按钮")
            return False
        except Exception as e:
            print_error(f"点击'+{filter_name}'出错: {e}")
            return False

    def set_court_level(self, mode):
        """
        设置法院级别
        mode: 'mid' -> 最高+高级+中级
              'high' -> 最高+高级
        """
        values = {
            'mid': ['01', '02', '03'],
            'high': ['01', '02']
        }
        selected = values.get(mode, values['mid'])

        for attempt in range(3):
            try:
                result = self.pkulaw_page.run_js(f'''
                    (function(){{
                        var selected = {selected!r};
                        var cbs = document.querySelectorAll('.el-checkbox-group .el-checkbox__original');
                        if (cbs.length === 0) {{
                            cbs = document.querySelectorAll('input[type="checkbox"].el-checkbox__original');
                        }}
                        var matched = 0;
                        for (var i=0; i<cbs.length; i++){{
                            var cb = cbs[i];
                            if (selected.indexOf(cb.value) !== -1){{
                                cb.checked = true;
                                cb.dispatchEvent(new Event('change', {{bubbles: true}}));
                                var label = cb.closest ? cb.closest('label') : null;
                                if (!label) {{
                                    var p = cb.parentElement;
                                    while (p && p.tagName !== 'LABEL') p = p.parentElement;
                                    label = p;
                                }}
                                if (label){{
                                    var span = label.querySelector('.el-checkbox__input');
                                    if (span) span.classList.add('is-checked');
                                    label.classList.add('is-checked');
                                }}
                                matched++;
                            }}
                        }}
                        return matched;
                    }})()
                ''', as_expr=True)
                print_info(f"已勾选 {result} 个法院级别选项")
                if result == 0 and attempt < 2:
                    print_warning("法院级别复选框未加载，等待后重试...")
                    time.sleep(2)
                    continue
                time.sleep(0.5)
                return True
            except Exception as e:
                print_error(f"设置法院级别失败: {e}")
                return False
        return False

    def set_case_gist(self, text, max_retry=3):
        """设置案由：先选择下拉类型，再逐个填入关键词并选择匹配项"""
        dropdown_map = {
            '劳动争议、人事争议': '民事',
            '行政': '行政',
        }
        dropdown_type = dropdown_map.get(text, '全部')
        
        # 确定关键词列表
        if text == '行政':
            keywords = ['行政主体', '行政行为']
        else:
            keywords = [text]
        
        print_info(f"设置案由: {text} (下拉: {dropdown_type}, 关键词: {keywords})")

        try:
            for attempt in range(max_retry):
                # ========== 步骤1：展开下拉框 ==========
                r1 = self.pkulaw_page.run_js(f'''
                    (function(){{
                        var titles = document.querySelectorAll('.fb-title');
                        var gistItem = null;
                        for (var t=0; t<titles.length; t++){{
                            if (titles[t].textContent.trim() === '案由'){{
                                var p = titles[t].parentElement;
                                while (p && !p.classList.contains('item')) p = p.parentElement;
                                gistItem = p;
                                break;
                            }}
                        }}
                        if (!gistItem){{
                            var gistDiv = document.querySelector('[property="CaseGist"]');
                            if (gistDiv) gistItem = gistDiv.querySelector('.item');
                        }}
                        if (!gistItem) return 'NOT_FOUND_ITEM';

                        var chooseTypeSelect = gistItem.querySelector('.chooseType .el-select');
                        if (!chooseTypeSelect) chooseTypeSelect = gistItem.querySelector('.el-select.fb-mini');
                        if (!chooseTypeSelect) return 'NOT_FOUND_DROPDOWN';

                        var selectInput = chooseTypeSelect.querySelector('input.el-input__inner');
                        if (!selectInput) return 'NOT_FOUND_DROPDOWN_INPUT';

                        selectInput.click();
                        selectInput.focus();
                        return 'clicked';
                    }})()
                ''', as_expr=True)
                if not r1 or (isinstance(r1, str) and r1.startswith('NOT_FOUND')):
                    if attempt < max_retry - 1:
                        print_warning(f"展开下拉框失败，第{attempt+1}次重试...")
                        time.sleep(2)
                        continue
                    print_warning(f"展开下拉框失败: {r1}")
                    return False

                time.sleep(1.5)

                # ========== 步骤2：选择下拉类型（带加载检测+点击后验证）==========
                r2 = self.pkulaw_page.run_js(f'''
                    (function(){{
                        var dropdownType = "{dropdown_type}";
                        var titles = document.querySelectorAll('.fb-title');
                        var gistItem = null;
                        for (var t=0; t<titles.length; t++){{
                            if (titles[t].textContent.trim() === '案由'){{
                                var p = titles[t].parentElement;
                                while (p && !p.classList.contains('item')) p = p.parentElement;
                                gistItem = p;
                                break;
                            }}
                        }}
                        if (!gistItem){{
                            var gistDiv = document.querySelector('[property="CaseGist"]');
                            if (gistDiv) gistItem = gistDiv.querySelector('.item');
                        }}
                        if (!gistItem) return 'NOT_FOUND_ITEM';

                        var dropdown = document.querySelector('.el-select-dropdown.chooseType-select');
                        if (!dropdown || dropdown.style.display === 'none'){{
                            var allDropdowns = document.querySelectorAll('.el-select-dropdown.el-popper');
                            for (var d=0; d<allDropdowns.length; d++){{
                                if (allDropdowns[d].style.display !== 'none'){{
                                    dropdown = allDropdowns[d];
                                    break;
                                }}
                            }}
                        }}
                        if (!dropdown) return 'DROPDOWN_NOT_RENDERED:0';

                        var items = dropdown.querySelectorAll('.el-select-dropdown__item');
                        var optionTexts = [];
                        for (var i=0; i<items.length; i++){{
                            optionTexts.push(items[i].textContent.trim());
                        }}

                        // 优先精确匹配，其次包含匹配
                        var targetIdx = -1;
                        for (var i=0; i<items.length; i++){{
                            if (items[i].textContent.trim() === dropdownType){{
                                targetIdx = i;
                                break;
                            }}
                        }}
                        if (targetIdx === -1){{
                            for (var i=0; i<items.length; i++){{
                                if (items[i].textContent.trim().indexOf(dropdownType) !== -1){{
                                    targetIdx = i;
                                    break;
                                }}
                            }}
                        }}

                        if (targetIdx !== -1){{
                            items[targetIdx].click();
                            // 点击空白处关闭下拉框，避免遮挡后续操作
                            var blankArea = document.querySelector('.el-main') || document.querySelector('.main-content') || document.querySelector('.fb-content') || document.body;
                            if (blankArea) blankArea.click();
                            // 点击后验证 input 值是否正确
                            var chooseTypeSelect = gistItem.querySelector('.chooseType .el-select');
                            if (!chooseTypeSelect) chooseTypeSelect = gistItem.querySelector('.el-select.fb-mini');
                            var actualVal = '';
                            if (chooseTypeSelect){{
                                var inp = chooseTypeSelect.querySelector('input.el-input__inner');
                                if (inp) actualVal = inp.value || inp.placeholder || '';
                            }}
                            if (actualVal === dropdownType || actualVal.indexOf(dropdownType) !== -1){{
                                return 'dropdown-selected:' + JSON.stringify(optionTexts);
                            }}
                            return 'VERIFY_FAILED:' + actualVal + ':' + JSON.stringify(optionTexts);
                        }}
                        return 'OPTION_NOT_FOUND:' + JSON.stringify(optionTexts);
                    }})()
                ''', as_expr=True)
                if not r2 or (isinstance(r2, str) and r2.startswith('NOT_FOUND')):
                    if attempt < max_retry - 1:
                        print_warning(f"选择下拉类型失败，第{attempt+1}次重试...")
                        time.sleep(2)
                        continue
                    print_warning(f"选择下拉类型失败: {r2}")
                    return False
                if isinstance(r2, str) and r2.startswith('DROPDOWN_NOT_RENDERED'):
                    if attempt < max_retry - 1:
                        print_warning(f"下拉框未渲染（网络延迟），第{attempt+1}次重试...")
                        time.sleep(2)
                        continue
                    print_warning(f"下拉框未渲染: {r2}")
                    return False
                if isinstance(r2, str) and r2.startswith('OPTION_NOT_FOUND'):
                    if attempt < max_retry - 1:
                        parts = r2.split(':', 1)
                        options = parts[1] if len(parts) > 1 else '[]'
                        print_warning(f"未找到 '{dropdown_type}' 选项（当前选项: {options}），第{attempt+1}次重试...")
                        time.sleep(2)
                        continue
                    print_warning(f"未找到 '{dropdown_type}' 选项: {r2}")
                    return False
                if isinstance(r2, str) and r2.startswith('VERIFY_FAILED'):
                    parts = r2.split(':')
                    actual = parts[1] if len(parts) > 1 else 'unknown'
                    if attempt < max_retry - 1:
                        print_warning(f"点击后验证失败（实际值: {actual}，期望: {dropdown_type}），第{attempt+1}次重试...")
                        time.sleep(2)
                        continue
                    print_warning(f"点击后验证失败: 实际值={actual}，期望={dropdown_type}")
                    return False

                # 确保案由大类下拉框已关闭
                self.ensure_dropdown_closed()

                # ========== 步骤3：逐个填入关键词并选择 ==========
                for kw in keywords:
                    r3 = self.pkulaw_page.run_js(f'''
                        (function(){{
                            var kw = "{kw}";
                            var titles = document.querySelectorAll('.fb-title');
                            var gistItem = null;
                            for (var t=0; t<titles.length; t++){{
                                if (titles[t].textContent.trim() === '案由'){{
                                    var p = titles[t].parentElement;
                                    while (p && !p.classList.contains('item')) p = p.parentElement;
                                    gistItem = p;
                                    break;
                                }}
                            }}
                            if (!gistItem){{
                                var gistDiv = document.querySelector('[property="CaseGist"]');
                                if (gistDiv) gistItem = gistDiv.querySelector('.item');
                            }}
                            if (!gistItem) return 'NOT_FOUND_ITEM';

                            var searchInputs = gistItem.querySelectorAll('input');
                            var targetInput = null;
                            for (var i=0; i<searchInputs.length; i++){{
                                var ph = searchInputs[i].getAttribute('placeholder') || '';
                                if (ph.indexOf('最多5个词语') !== -1 || searchInputs[i].name === 'text'){{
                                    targetInput = searchInputs[i];
                                    break;
                                }}
                            }}
                            if (!targetInput) return 'NOT_FOUND_INPUT';

                            targetInput.focus();
                            targetInput.click();
                            targetInput.removeAttribute('readonly');
                            targetInput.value = kw;
                            targetInput.dispatchEvent(new InputEvent('input', {{
                                bubbles: true, inputType: 'insertText', data: kw
                            }}));
                            targetInput.dispatchEvent(new Event('change', {{bubbles: true}}));
                            var selectEl = targetInput.closest('.el-select');
                            if (selectEl){{
                                var vue = selectEl.__vue__;
                                if (vue && typeof vue.handleQueryChange === 'function'){{
                                    vue.handleQueryChange(kw);
                                }}
                            }}
                            return 'filled';
                        }})()
                    ''', as_expr=True)
                    if not r3 or (isinstance(r3, str) and r3.startswith('NOT_FOUND')):
                        print_warning(f"填入关键词失败: {kw} -> {r3}")
                        continue

                    if r3 == 'filled':
                        wait_sec = 1.5
                        print_info(f"等待 {wait_sec} 秒让下拉选项出现 [{kw}]...")
                        time.sleep(wait_sec)
                        # 获取下拉选项内容
                        options = self.pkulaw_page.run_js('''
                            (function(){
                                var allDropdowns = document.querySelectorAll('.el-select-dropdown.el-popper');
                                var dropdown = null;
                                for (var i=0; i<allDropdowns.length; i++){
                                    if (allDropdowns[i].style.display !== 'none'){
                                        dropdown = allDropdowns[i];
                                        break;
                                    }
                                }
                                if (!dropdown) return JSON.stringify({count: 0, items: []});
                                var items = dropdown.querySelectorAll('.el-select-dropdown__item');
                                var texts = [];
                                for (var i=0; i<items.length; i++){
                                    texts.push(items[i].textContent.trim());
                                }
                                return JSON.stringify({count: items.length, items: texts});
                            })()
                        ''', as_expr=True)
                        print_info(f"下拉选项内容 [{kw}]: {options}")
                        # 点击精确匹配项
                        self.pkulaw_page.run_js(f'''
                            (function(){{
                                var targetText = "{dropdown_type}/{kw}";
                                var allDropdowns = document.querySelectorAll('.el-select-dropdown.el-popper');
                                var dropdown = null;
                                for (var i=0; i<allDropdowns.length; i++){{
                                    if (allDropdowns[i].style.display !== 'none'){{
                                        dropdown = allDropdowns[i];
                                        break;
                                    }}
                                }}
                                if (dropdown){{
                                    var items = dropdown.querySelectorAll('.el-select-dropdown__item');
                                    var found = false;
                                    for (var i=0; i<items.length; i++){{
                                        if (items[i].textContent.trim() === targetText){{
                                            items[i].dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true, view: window}}));
                                            found = true;
                                            break;
                                        }}
                                    }}
                                    if (!found && items.length > 0){{
                                        items[0].dispatchEvent(new MouseEvent('click', {{bubbles: true, cancelable: true, view: window}}));
                                    }}
                                }}
                                // 等待Vue更新后再点击空白处关闭
                                var blankArea = document.querySelector('.el-main') || document.querySelector('.main-content') || document.querySelector('.fb-content') || document.body;
                                if (blankArea) blankArea.click();
                            }})()
                        ''', as_expr=True)
                        print_info(f"已选择: {dropdown_type}/{kw}")
                    # 确保关键词下拉框已关闭
                    self.ensure_dropdown_closed()
                    time.sleep(0.5)
                
                return True
        except Exception as e:
            print_error(f"设置案由失败: {e}")
            return False


    def click_no_group(self):
        """高级检索结果页：点击'不分组'dropdown选项"""
        print_info("点击'不分组'...")
        try:
            # 1. 点击 dropdown trigger 展开菜单
            self.pkulaw_page.run_js('''
                (function(){
                    var triggers = document.querySelectorAll('.dropdown .el-dropdown-link, .dropdown .el-dropdown-selfdefine');
                    for (var i=0; i<triggers.length; i++){
                        triggers[i].click();
                    }
                })()
            ''', as_expr=True)
            time.sleep(1)

            # 2. 点击'不分组'选项
            self.pkulaw_page.run_js('''
                (function(){
                    var items = document.querySelectorAll('.el-dropdown-menu__item');
                    for (var i=0; i<items.length; i++){
                        if (items[i].textContent.trim() === '不分组'){
                            items[i].click();
                            return 'clicked';
                        }
                    }
                    return 'not_found';
                })()
            ''', as_expr=True)
            time.sleep(3)
            print_info("已选择'不分组'")
            return True
        except Exception as e:
            print_warning(f"点击'不分组'失败: {e}")
            return False

    def download_page(self, page_num):
        """高级检索结果页：下载当前页（重写父类，适配el-table结构）"""
        try:
            page = self.pkulaw_page
            print_info(f"开始下载第 {page_num} 页...")

            # 1. 等待表格加载
            print_info("等待表格加载...")
            try:
                time.sleep(3)
                page.ele('.el-table__body tr', timeout=10)
                print_info("表格已加载")
            except:
                print_warning("等待表格加载超时，继续尝试...")
                time.sleep(5)

            # 2. 点击表头全选 checkbox
            print_info("点击表头全选...")
            try:
                page.run_js('''
                    (function(){
                        var headerCheckbox = document.querySelector('th.el-table-column--selection .el-checkbox__inner');
                        if (headerCheckbox){
                            headerCheckbox.click();
                            return 'clicked_header';
                        }
                        var headerInput = document.querySelector('th.el-table-column--selection input[type=checkbox]');
                        if (headerInput){
                            headerInput.click();
                            return 'clicked_input';
                        }
                        return 'not_found';
                    })()
                ''', as_expr=True)
                print_info("已点击表头全选")
                time.sleep(2)

                # 验证是否选中
                checked_count = 0
                try:
                    checked_boxes = page.eles('css:.el-table__body tr .el-checkbox.is-checked')
                    checked_count = len(checked_boxes)
                    print_info(f"已选中 {checked_count} 行")
                except:
                    pass

                if checked_count == 0:
                    print_warning("未选中任何行，可能当前页无数据")
                    return False
            except Exception as e:
                print_error(f"点击全选失败: {e}")
                return False

            # 3. 点击批量下载按钮
            print_info("点击批量下载按钮...")
            try:
                download_clicked = page.run_js('''
                    (function(){
                        var btn = document.querySelector('.batch-container .left-downLoad');
                        if (!btn) btn = document.querySelector('.batch-container .icon-qikan_xiazai');
                        if (btn){
                            btn.closest('p,div,span').click();
                            return 'clicked';
                        }
                        return 'not_found';
                    })()
                ''', as_expr=True)
                if download_clicked == 'not_found':
                    print_warning("未找到批量下载按钮，尝试备用选择器...")
                    for selector in ['.download-btn', 'text:下载', '[title*=下载]', '[class*=download]', '.icon-download']:
                        try:
                            btn = page.ele(selector, timeout=2)
                            if btn:
                                btn.run_js('this.click()')
                                print_info(f"使用备用选择器点击下载: {selector}")
                                break
                        except:
                            continue
                else:
                    print_info("已点击批量下载按钮")
                time.sleep(3)
            except Exception as e:
                print_error(f"点击下载按钮失败: {e}")
                return False

            # 4. 选择下载格式（复用父类方法）
            if not self.select_download_format(page):
                print_warning("下载格式选择可能未完全成功，继续尝试提交下载...")

            # 5. 点击确定，触发下载（复用父类逻辑）
            print_info("点击弹窗中的确定...")
            try:
                url_before = page.url
                download_dir = self.get_default_download_dir()
                before_files = set(os.listdir(download_dir)) if os.path.exists(download_dir) else set()
                time.sleep(2)

                confirm_btn = None
                # 方法1: .button_list 中的 primary 按钮（高级检索结果页下载弹窗）
                try:
                    confirm_btn = page.ele('css:.button_list .el-button--primary', timeout=3)
                    if confirm_btn and '确定' in (confirm_btn.text or ''):
                        print_info("在.button_list中找到确定按钮")
                except:
                    pass

                # 方法2: class="submit"
                if not confirm_btn:
                    try:
                        confirm_btn = page.ele('css:a.submit', timeout=3)
                        if confirm_btn and '确定' in (confirm_btn.text or ''):
                            print_info("找到class='submit'的确定按钮")
                    except:
                        pass

                # 方法3: 弹窗footer中找
                if not confirm_btn:
                    try:
                        dialog = page.ele('.el-dialog', timeout=3)
                        if dialog:
                            footer = dialog.ele('.el-dialog__footer', timeout=2)
                            confirm_btn = footer.ele('text:确定', timeout=2)
                            print_info("在弹窗footer中找到确定按钮")
                    except:
                        pass

                # 方法4: XPath
                if not confirm_btn:
                    try:
                        confirm_btn = page.ele('xpath://div[contains(@class,"el-dialog__footer")]//button[contains(.//span,"确定")]', timeout=3)
                        if confirm_btn:
                            print_info("使用XPath找到确定按钮")
                    except:
                        pass

                # 方法5: 最后一个确定按钮
                if not confirm_btn:
                    try:
                        buttons = page.eles('text:确定')
                        if buttons:
                            confirm_btn = buttons[-1]
                            print_info(f"使用最后一个确定按钮，共{len(buttons)}个")
                    except:
                        pass

                if not confirm_btn:
                    print_error("未找到确定按钮")
                    return False

                try:
                    confirm_btn.run_js('this.click()')
                    print_info("已点击确定")
                except Exception as e:
                    print_error(f"点击确定失败: {e}")
                    return False

                time.sleep(5)

                # 检测下载次数上限
                if self.check_download_limit_popup():
                    return False

                # 检查新标签页
                tabs = self.browser.get_tabs()
                new_tab = None
                for tab in tabs:
                    if tab != self.pkulaw_page and tab.url != url_before:
                        new_tab = tab
                        break

                if new_tab:
                    download_url = new_tab.url
                    print_info(f"新标签页URL: {download_url}")
                    if '.zip' in download_url.lower():
                        print_info("检测到ZIP下载链接")
                        self.pkulaw_page = new_tab
                        if self.download_and_extract_zip(download_url, page_num):
                            print_success(f"第 {page_num} 页下载并解压完成")
                            self.browser.get_tabs()[0].set.activate()
                            self.pkulaw_page = self.browser.get_tabs()[0]
                            self.close_download_dialog()
                            return True
                        return False
                    else:
                        print_success(f"第 {page_num} 页下载已触发")
                        for tab in self.browser.get_tabs():
                            if 'law' in tab.url or 'case' in tab.url:
                                tab.set.activate()
                                self.pkulaw_page = tab
                                break
                        self.close_download_dialog()
                else:
                    url_after = page.url
                    print_info(f"点击后URL: {url_after}")
                    if url_after != url_before:
                        if '.zip' in url_after.lower():
                            print_info("页面变为ZIP下载")
                            if self.download_and_extract_zip(url_after, page_num):
                                print_success(f"第 {page_num} 页下载完成")
                                return True
                            return False
                        else:
                            print_success(f"第 {page_num} 页下载已触发")
                            self.close_download_dialog()
                    else:
                        print_warning("URL未变化，下载可能通过浏览器自动处理")
                        print_success(f"第 {page_num} 页下载任务已提交")
                        self.close_download_dialog()

                # 兜底处理浏览器自动下载
                moved = self.wait_and_move_browser_download(page_num, before_files)
                if not moved:
                    print_warning("浏览器下载文件未能及时检测到，尝试扫描残留文件...")
                    self.scan_and_move_leftover_downloads(start_time=time.time() - 120, page_num=page_num)
                return True

            except Exception as e:
                print_error(f"点击确定失败: {e}")
                return False

        except Exception as e:
            print_error(f"下载第 {page_num} 页出错: {e}")
            return False

    def go_to_next_page(self):
        """高级检索结果页：翻到下一页"""
        try:
            page = self.pkulaw_page
            print_info("翻到下一页...")

            # 点击下一页按钮
            next_btn = None
            for selector in ['.el-pagination .btn-next:not([disabled])', '.el-pagination .btn-next']:
                try:
                    next_btn = page.ele(selector, timeout=3)
                    if next_btn:
                        btn_disabled = next_btn.attr('disabled')
                        if btn_disabled:
                            next_btn = None
                            continue
                        break
                except:
                    continue

            if next_btn:
                try:
                    next_btn.run_js('this.click()')
                    print_info("已点击下一页")
                except Exception as e:
                    print_info(f"点击下一页失败: {e}")
                    return False
            else:
                print_info("未找到下一页按钮，可能是最后一页")
                return False

            # 等待新页面加载
            time.sleep(3)
            try:
                page.ele('.el-table__body tr', timeout=10)
                print_info("新页面表格已加载")
                return True
            except:
                print_warning("新页面加载超时")
                return False

        except Exception as e:
            print_error(f"翻页失败: {e}")
            return False

    def click_search(self):
        """点击检索按钮"""
        print_info("点击检索按钮...")
        try:
            self.pkulaw_page.run_js('''
                (function(){
                    var btns = document.querySelectorAll('button');
                    for (var i=0; i<btns.length; i++){
                        if (btns[i].textContent.trim() === '检索'){
                            btns[i].click();
                            return true;
                        }
                    }
                    return false;
                })()
            ''', as_expr=True)
            time.sleep(3)
            return True
        except Exception as e:
            print_error(f"点击检索失败: {e}")
            return False

    def save_current_html(self, filename):
        try:
            html = self.pkulaw_page.html
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            print_success(f"页面HTML已保存: {filepath} ({len(html)} 字符)")
            return True
        except Exception as e:
            print_error(f"保存HTML失败: {e}")
            return False

    def set_filter_input(self, title_text, value):
        """通用：在指定标题的筛选区域（审理法院/审理程序等）填入文本并选择下拉选项"""
        if not value:
            return True
        print_info(f"设置 {title_text}: {value}")
        try:
            # 填入值并触发过滤
            r1 = self.pkulaw_page.run_js(f'''
                (function(){{
                    var titleText = "{title_text}";
                    var value = "{value}";
                    var titles = document.querySelectorAll('.fb-title');
                    var item = null;
                    for (var t=0; t<titles.length; t++){{
                        if (titles[t].textContent.trim() === titleText){{
                            var p = titles[t].parentElement;
                            while (p && !p.classList.contains('item')) p = p.parentElement;
                            item = p;
                            break;
                        }}
                    }}
                    if (!item) return 'NOT_FOUND_ITEM';
                    var searchInputs = item.querySelectorAll('input');
                    var targetInput = null;
                    for (var i=0; i<searchInputs.length; i++){{
                        var ph = searchInputs[i].getAttribute('placeholder') || '';
                        if (ph.indexOf('最多5个词语') !== -1 || searchInputs[i].name === 'text'){{
                            targetInput = searchInputs[i];
                            break;
                        }}
                    }}
                    if (!targetInput) return 'NOT_FOUND_INPUT';
                    targetInput.focus();
                    targetInput.click();
                    targetInput.removeAttribute('readonly');
                    targetInput.value = value;
                    targetInput.dispatchEvent(new InputEvent('input', {{
                        bubbles: true, inputType: 'insertText', data: value
                    }}));
                    targetInput.dispatchEvent(new Event('change', {{bubbles: true}}));
                    var selectEl = targetInput.closest('.el-select');
                    if (selectEl){{
                        var vue = selectEl.__vue__;
                        if (vue && typeof vue.handleQueryChange === 'function'){{
                            vue.handleQueryChange(value);
                        }}
                    }}
                    return 'filled';
                }})()
            ''', as_expr=True)
            if not r1 or (isinstance(r1, str) and r1.startswith('NOT_FOUND')):
                print_warning(f"{title_text} 填入失败: {r1}")
                return False

            # 等待下拉选项出现
            time.sleep(1.5)

            # 获取下拉选项内容
            options = self.pkulaw_page.run_js('''
                (function(){
                    var allDropdowns = document.querySelectorAll('.el-select-dropdown.el-popper');
                    var dropdown = null;
                    for (var i=0; i<allDropdowns.length; i++){
                        if (allDropdowns[i].style.display !== 'none'){
                            dropdown = allDropdowns[i];
                            break;
                        }
                    }
                    if (!dropdown) return JSON.stringify({count: 0, items: []});
                    var items = dropdown.querySelectorAll('.el-select-dropdown__item');
                    var texts = [];
                    for (var i=0; i<items.length; i++){
                        texts.push(items[i].textContent.trim());
                    }
                    return JSON.stringify({count: items.length, items: texts});
                })()
            ''', as_expr=True)
            print_info(f"下拉选项内容 [{title_text}]: {options}")

            # 点击第一个选项
            self.pkulaw_page.run_js('''
                (function(){
                    var allDropdowns = document.querySelectorAll('.el-select-dropdown.el-popper');
                    var dropdown = null;
                    for (var i=0; i<allDropdowns.length; i++){
                        if (allDropdowns[i].style.display !== 'none'){
                            dropdown = allDropdowns[i];
                            break;
                        }
                    }
                    if (dropdown){
                        var items = dropdown.querySelectorAll('.el-select-dropdown__item');
                        if (items.length > 0){
                            items[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                        }
                    }
                    // 等待Vue更新后再点击空白处关闭
                    var blankArea = document.querySelector('.el-main') || document.querySelector('.main-content') || document.querySelector('.fb-content') || document.body;
                    if (blankArea) blankArea.click();
                })()
            ''', as_expr=True)
            # 确保下拉框已关闭
            self.ensure_dropdown_closed()
            print_info(f"{title_text} 已设置")
            return True
        except Exception as e:
            print_error(f"设置 {title_text} 失败: {e}")
            return False

    def set_full_text(self, keywords_list):
        """设置全文检索关键词，前3个填入第一个框，后3个填入第二个框"""
        if not keywords_list:
            return True
        keywords1 = ' '.join(keywords_list[:3])
        keywords2 = ' '.join(keywords_list[3:6])
        print_info(f"设置全文关键词: {keywords_list}")
        try:
            max_wait = 10
            for attempt in range(max_wait):
                result = self.pkulaw_page.run_js(f'''
                    (function(){{
                        var keywords1 = "{keywords1}";
                        var keywords2 = "{keywords2}";
                        var fullTextDiv = document.querySelector('[property="FullText"]');
                        if (!fullTextDiv) return 'NOT_FOUND_FULLTEXT';
                        var inputs = fullTextDiv.querySelectorAll('input[name="FullText"]');
                        if (inputs.length < 1) return 'NOT_FOUND_INPUTS';
                        if (inputs[0] && keywords1){{
                            inputs[0].focus();
                            inputs[0].value = keywords1;
                            inputs[0].dispatchEvent(new Event('input', {{bubbles: true}}));
                            inputs[0].dispatchEvent(new Event('change', {{bubbles: true}}));
                        }}
                        if (inputs[1] && keywords2){{
                            inputs[1].focus();
                            inputs[1].value = keywords2;
                            inputs[1].dispatchEvent(new Event('input', {{bubbles: true}}));
                            inputs[1].dispatchEvent(new Event('change', {{bubbles: true}}));
                        }}
                        return 'filled';
                    }})()
                ''', as_expr=True)
                if result and result.startswith('filled'):
                    print_info(f"全文已设置 (框1: '{keywords1}' 框2: '{keywords2}')")
                    time.sleep(0.5)
                    return True
                if attempt < max_wait - 1:
                    print_warning(f"全文区域未加载，第{attempt+1}次重试...")
                    time.sleep(1.5)
                else:
                    print_warning(f"全文设置可能未成功: {result}")
            return False
        except Exception as e:
            print_error(f"设置全文失败: {{e}}")
            return False


def print_header(text):
    print(f"\n{'='*60}")
    print(f"{text.center(60)}")
    print(f"{'='*60}\n")


def main():
    print_header("北大法宝司法案例高级检索")

    # 清理旧HTML
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for f in os.listdir(base_dir):
        if f.startswith('advanced_case_') and f.endswith('.html'):
            try:
                os.remove(os.path.join(base_dir, f))
                print_info(f"已删除旧文件: {f}")
            except:
                pass

    # 用户交互：选择法院级别
    print("\n请选择法院级别模式:")
    print("  1. 中级（最高人民法院 + 高级人民法院 + 中级人民法院）")
    print("  2. 高级（最高人民法院 + 高级人民法院）")
    court_choice = input("请选择 (1/2，默认1): ").strip()
    court_mode = 'high' if court_choice == '2' else 'mid'

    # 用户交互：选择案由
    print("\n请选择案由:")
    print("  1. 劳动争议、人事争议")
    print("  2. 行政")
    case_choice = input("请选择 (1/2，默认1): ").strip()
    case_gist_text = "行政" if case_choice == "2" else "劳动争议、人事争议"

    # 用户交互：输入全文关键词
    print("\n请输入全文检索关键词（最多6个，空格分隔，直接回车表示不填）：")
    full_text_input = input("关键词: ").strip()
    full_text_keywords = full_text_input.split() if full_text_input else []

    # 用户交互：输入审理法院
    print("\n请输入审理法院（直接回车表示不填）：")
    trial_court = input("审理法院: ").strip()

    # 用户交互：输入审理程序
    print("\n请输入审理程序（直接回车表示不填）：")
    trial_step = input("审理程序: ").strip()

    # 用户交互：输入最大下载页数
    print("\n请输入最大下载页数（默认5页，直接回车）：")
    max_pages_input = input("下载页数: ").strip()
    max_pages = int(max_pages_input) if max_pages_input.isdigit() else 5

    print("\n" + "="*50)
    print(f"法院级别: {'中级' if court_mode == 'mid' else '高级'}")
    print(f"案由: {case_gist_text if case_gist_text else '无'}")
    print(f"全文关键词: {' '.join(full_text_keywords) if full_text_keywords else '无'}")
    print(f"审理法院: {trial_court if trial_court else '无'}")
    print(f"审理程序: {trial_step if trial_step else '无'}")
    print(f"最大下载页数: {max_pages}")
    print("="*50)
    confirm = input("\n确认开始？(Y/n): ").strip().lower()
    if confirm and confirm not in ['y', 'yes', '是']:
        print("已取消")
        return

    crawler = CaseAdvancedSearchCrawler()

    try:
        if not crawler.init_browser():
            return
        if not crawler.login_library():
            print_error("登录失败")
            return
        crawler.wait()
        if not crawler.goto_pkulaw():
            print_error("跳转失败")
            return
        crawler.wait()
        if not crawler.goto_advanced_case():
            return

        # 先设置全文关键词
        if full_text_keywords:
            if not crawler.set_full_text(full_text_keywords):
                print_warning("全文设置可能未成功，继续执行...")
            crawler.wait(0.5, 1)

        # 再设置案由
        if case_gist_text:
            if not crawler.set_case_gist(case_gist_text):
                print_warning("案由设置可能未成功，继续执行...")
            crawler.wait(0.5, 1)

        # 再点击左侧筛选条件展开面板
        filters_to_add = ['法院级别', '审理法院', '审理程序']
        for f in filters_to_add:
            crawler.click_add_filter(f)
            crawler.wait(0.5, 1)

        # 设置审理法院
        if trial_court:
            crawler.set_filter_input('审理法院', trial_court)
            crawler.wait(0.5, 1)

        # 设置审理程序
        if trial_step:
            crawler.set_filter_input('审理程序', trial_step)
            crawler.wait(0.5, 1)

        # 设置法院级别
        if not crawler.set_court_level(court_mode):
            return

        # 点击检索
        crawler.click_search()

        # 等待检索结果页面加载
        print_info("等待检索结果页面加载...")
        time.sleep(5)

        # 保存检索结果页面（首页）
        crawler.save_current_html('advanced_case_result.html')

        # 批量下载：不分组 → 全选 → 下载 → 翻页
        print_step(5, "开始批量下载")
        crawler.batch_download(max_pages=max_pages)

        print_success("任务完成！")

    except KeyboardInterrupt:
        print("\n已中止")
    except Exception as e:
        print_error(f"程序错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print()
        print_info("浏览器保持打开，请观察页面状态。")
        print_info("观察完毕后，在此终端按 Ctrl+C 或关闭窗口即可。")
        # 阻塞主线程，保持脚本运行，浏览器不关闭
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n已结束")


if __name__ == '__main__':
    main()
