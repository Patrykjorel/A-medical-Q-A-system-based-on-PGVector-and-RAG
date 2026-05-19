// 文件路径: org/demo/mapper/UserMapper.java
package org.demo.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.demo.entity.User;

@Mapper
public interface UserMapper extends BaseMapper<User> {
}