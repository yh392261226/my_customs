            # 异步查找重复书籍（【回退到稳定的Ultra检测器】）
            def find_duplicates_async():
                """异步查找重复书籍（使用经过优化的Ultra检测器）"""
                try:
                    # 【重要说明】2026-05-29 回退到Ultra检测器
                    # 
                    # 回退原因：V2引擎在大数据集(16000+本TXT)上存在严重问题：
                    # 1. SimHash阈值太宽松(=4)，导致候选对数量爆炸
                    # 2. O(n²)复杂度，16833本书需1.4亿次SimHash比较
                    # 3. 评分过于乐观，不相关的书对也容易超过阈值(50分)
                    # 结果：大量误报，几乎所有书都被判定为"100%重复"
                    #
                    # Ultra检测器已做的优化（保留）：
                    # ✅ 包含关系参数放宽：SUBSET_MIN_RATIO 65%→55%
                    # ✅ 内容采样增加：15000字符→30000字符，5位置→8位置
                    # ✅ 规则B/C/D阈值优化：针对1-5章 vs 1-8章等场景
                    # ✅ 推荐删除功能正常（_recommend_deletion方法）
                    
                    from src.utils.book_duplicate_detector_ultra import UltraBookDuplicateDetector
                    
                    result = UltraBookDuplicateDetector.find_duplicates(
                        all_books,
                        progress_callback=progress_callback,
                        batch_callback=batch_callback
                    )
                    
                    # 所有批次完成后，通知UI
                    self.app.call_from_thread(self._on_all_batches_completed, result)
                    return result
                    
                except Exception as e:
                    # 处理错误
                    self.app.call_from_thread(self._on_duplicate_search_error, e)
                    return None
            
            # 【暂时禁用】V2版本的批次回调函数
            # （回退到Ultra检测器后不再需要）
            
            # 标准格式的批次回调函数
            def batch_callback(batch_groups, batch_index, total_batches, processing_remaining=True):
                """处理批次完成"""
                logger.info(f"批回调被调用: 批次 {batch_index+1 if batch_index >= 0 else '初始'}, 找到 {len(batch_groups)} 组重复")
                
                # 使用 app.call_from_thread 确保线程安全
                logger.info(f"准备显示重复结果: 批次 {batch_index+1 if batch_index >= 0 else '初始'}, 组数 {len(batch_groups)}")
                self.app.call_from_thread(
                    self._show_duplicate_results,
                    batch_groups,
                    batch_index,
                    total_batches,
                    processing_remaining
                )
