// 文件名: ChatHistoryMapper.java
package org.demo.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.demo.entity.ChatHistory;

@Mapper
public interface ChatHistoryMapper extends BaseMapper<ChatHistory> {
}